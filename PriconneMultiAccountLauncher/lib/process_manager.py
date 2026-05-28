import ctypes
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import psutil
import win32security
from static.config import AssetsPathConfig, DataPathConfig, SchtasksConfig
from static.env import Env

logger = logging.getLogger(__name__)


class ProcessManager:
    @staticmethod
    def admin_run(args: list[str], cwd: Optional[str] = None) -> int:
        """Elevate via ShellExecuteW 'runas'. Returns >32 on success, <=32 on failure.

        Does not mutate the caller's list.
        """
        if not args:
            raise ValueError("admin_run requires at least one arg (the executable)")
        file = args[0]
        rest = args[1:]
        logger.info({"cwd": cwd, "file": file, "argc": len(rest)})
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", str(file), " ".join([f"{arg}" for arg in rest]), cwd, 1
        )
        if rc <= 32:
            logger.warning("ShellExecuteW 'runas' returned %d (failure)", rc)
        return rc

    @staticmethod
    def admin_check() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except OSError as exc:
            logger.warning("IsUserAnAdmin failed: %s", exc)
            return False

    @staticmethod
    def run(args: list[str], cwd: Optional[str] = None) -> subprocess.Popen:
        logger.info({"cwd": cwd, "argc": len(args), "head": args[0] if args else None})
        return subprocess.Popen(args, cwd=cwd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    @staticmethod
    def run_ps_file(script_path: Path) -> int:
        logger.info("ps script: %s", script_path)
        return subprocess.call(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path.absolute())],
            shell=False,
        )


class ProcessIdManager:
    process: list[tuple[int, Optional[str]]]

    def __init__(self, _process: Optional[list[tuple[int, Optional[str]]]] = None) -> None:
        if _process is None:
            # Batch query: psutil populates `.info` in one pass, avoiding a per-process syscall
            # on `.exe()`. On a typical Win11 desktop this is ~10-50× faster than per-attr access.
            snapshot: list[tuple[int, Optional[str]]] = []
            for p in psutil.process_iter(attrs=["pid", "exe"]):
                info = p.info
                snapshot.append((info["pid"], info.get("exe")))
            self.process = snapshot
        else:
            self.process = _process

    def __sub__(self, other: "ProcessIdManager") -> "ProcessIdManager":
        process = [x for x in self.process if x not in other.process]
        return ProcessIdManager(process)

    def __add__(self, other: "ProcessIdManager") -> "ProcessIdManager":
        process = list(set(self.process + other.process))
        return ProcessIdManager(process)

    def __repr__(self) -> str:
        return "\n".join([f"{x[0]}: {x[1]}" for x in self.process]) + "\n"

    def new_process(self) -> "ProcessIdManager":
        return ProcessIdManager() - self

    def search(self, name: str) -> int:
        process = [x[0] for x in self.process if x[1] == name]
        if len(process) == 0:
            raise Exception(f"Process not found: {name}")
        return process[0]

    def search_or_none(self, name: str) -> Optional[int]:
        process = [x[0] for x in self.process if x[1] == name]
        if len(process) != 1:
            return None
        return process[0]


import functools


@functools.lru_cache(maxsize=1)
def get_sid() -> str:
    username = os.getlogin()
    sid, _, _ = win32security.LookupAccountName("", username)
    sidstr = win32security.ConvertSidToStringSid(sid)
    return sidstr


class Schtasks:
    file: str
    name: str

    def __init__(self, args: str) -> None:
        self.file = SchtasksConfig.FILE.format(os.getlogin(), args)
        self.name = SchtasksConfig.NAME.format(self.file)
        self.args = args

    def check(self) -> bool:
        xml_path = DataPathConfig.SCHTASKS.joinpath(self.file).with_suffix(".xml")
        return not xml_path.exists()

    def _xml_path(self) -> Path:
        return DataPathConfig.SCHTASKS.joinpath(self.file).with_suffix(".xml")

    def set(self) -> None:
        """Write XML + register the scheduled task. Raises on UAC denial."""
        with open(AssetsPathConfig.SCHTASKS, "r", encoding="utf-8") as f:
            template = f.read()

        if Env.DEVELOP:
            command = Path(sys.executable)
            args = [str(Path(sys.argv[0]).absolute()), self.args, "--type", "game"]
        else:
            command = Path(sys.argv[0])
            args = [self.args, "--type", "game"]

        from xml.sax.saxutils import escape

        template = template.replace(r"{{UID}}", escape(self.file))
        template = template.replace(r"{{SID}}", escape(get_sid()))
        template = template.replace(r"{{COMMAND}}", escape(str(command.absolute())))
        template = template.replace(r"{{ARGUMENTS}}", escape(" ".join(f"{x}" for x in args)))
        template = template.replace(r"{{WORKING_DIRECTORY}}", escape(os.getcwd()))

        xml_path = self._xml_path()
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(template)
        create_args = [str(Env.SCHTASKS), "/create", "/xml", str(xml_path.absolute()), "/tn", self.name]

        rc = ProcessManager.admin_run(create_args)
        if rc <= 32:
            # Roll back the XML side-effect so check() reflects reality.
            try:
                xml_path.unlink()
            except OSError:
                pass
            raise RuntimeError(f"Scheduled task registration failed (ShellExecute rc={rc}, likely UAC denied)")

    def delete(self) -> None:
        delete_args = [str(Env.SCHTASKS), "/delete", "/tn", self.name, "/f"]
        ProcessManager.admin_run(delete_args)
        try:
            self._xml_path().unlink()
        except OSError:
            pass


class Shortcut:
    def create(self, source: Path, target: Optional[Path] = None, args: Optional[list[str]] = None, icon: Optional[Path] = None):
        with open(AssetsPathConfig.SHORTCUT, "r", encoding="utf-8") as f:
            template = f.read()
        if icon is None:
            icon = Path(sys.argv[0])
        if args is None:
            args = []

        if target is None:
            if Env.DEVELOP:
                target = Path(sys.executable)
                args.insert(0, str(Path(sys.argv[0]).absolute()))
            else:
                target = Path(sys.argv[0])

        template = template.replace(r"{{SOURCE}}", str(source.absolute()))
        template = template.replace(r"{{TARGET}}", str(target))
        template = template.replace(r"{{WORKING_DIRECTORY}}", os.getcwd())
        template = template.replace(r"{{ICON_LOCATION}}", str(icon.absolute()))
        template = template.replace(r"{{ARGUMENTS}}", " ".join(f"{x}" for x in args))

        # Write the substituted script to a temp .ps1 and run with -File (no -Command interpolation).
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", encoding="utf-8", delete=False) as tf:
            tf.write(template)
            script_path = Path(tf.name)
        try:
            ProcessManager.run_ps_file(script_path)
        finally:
            try:
                script_path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove temp ps1 %s: %s", script_path, exc)
