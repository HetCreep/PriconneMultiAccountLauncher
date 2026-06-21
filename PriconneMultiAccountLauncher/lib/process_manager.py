import ctypes
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import psutil
from static.config import AssetsPathConfig
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
