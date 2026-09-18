import logging
import subprocess
import sys
import time
import traceback
from base64 import b64encode
from pathlib import Path
from typing import Callable

import customtkinter as ctk
import i18n
import psutil
from component.component import CTkProgressWindow
from customtkinter import CTk
from lib.DGPSessionV2 import DgpSessionV2
from lib.process_manager import ProcessIdManager, ProcessManager
from lib.thread import threading_wrapper
from lib.toast import ErrorWindow
from models.setting_data import AppConfig
from models.shortcut_data import BrowserConfigData, LauncherShortcutData, ShortcutData
from static.config import DataPathConfig
from static.constant import Constant
from static.env import Env
from tab.home import HomeTab
from utils.utils import get_driver, login_driver

logger = logging.getLogger(__name__)


class GameLauncher(CTk):
    loder: Callable

    def __init__(self, loder):
        super().__init__()

        self.title("Priconne Multi Account Launcher")
        self.geometry("900x600")
        self.withdraw()
        loder(self)

    def create(self):
        HomeTab(self).create().pack(expand=True, fill=ctk.BOTH)
        return self

    @threading_wrapper
    def thread(self, id: str, kill: bool = False, force_non_uac: bool = False):
        try:
            self.launch(id, kill, force_non_uac)
            self.quit()
        except Exception as e:
            if Env.DEVELOP:
                self.iconify()
                raise
            else:
                self.iconify()
                ErrorWindow(self, str(e), traceback.format_exc(), quit=True).create()

    def launch(self, id: str, kill: bool = False, force_non_uac: bool = False):
        logger.info("GameLauncher.launch start: id=%s kill=%s force_non_uac=%s", id, kill, force_non_uac)
        path = DataPathConfig.SHORTCUT.joinpath(id).with_suffix(".json")
        data = ShortcutData.from_path(path)

        account_name = data.account_path.get()
        from lib.account_swapper import swap_account_data, restore_to_baseline, restore_baseline_if_stale
        # Crash recovery: if the previous launcher process was force-killed
        # (Task Manager, power loss, etc.), the on-disk state is whichever
        # account was last swapped in, not the user's primary DMM-client
        # account. Roll back baseline FIRST so the snapshot chain stays
        # consistent — user mostly launches via shortcuts, never opens main
        # GUI, so the main-GUI startup recovery probe wouldn't catch this.
        try:
            restore_baseline_if_stale()
        except Exception:
            logger.exception("Pre-launch stale-baseline recovery failed (non-fatal — continuing)")
        swap_account_data(account_name)
        # Per user design: swap-in before launch, swap-out (restore baseline) on
        # close. The finally guarantees the baseline restore even on crash/error
        # so the user's primary DMM account state is never left clobbered by a
        # temporary B/C session.
        try:
            self._launch_after_swap(data, kill, force_non_uac)
        finally:
            try:
                restore_to_baseline()
            except Exception:
                logger.exception("restore_to_baseline failed (baseline state may be left as last_active)")

    def _launch_after_swap(self, data, kill: bool, force_non_uac: bool):
        if data.account_path.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            session = DgpSessionV2.read_dgp()
        else:
            account_path = DataPathConfig.ACCOUNT.joinpath(data.account_path.get()).with_suffix(".bytes")
            browser_config_path = DataPathConfig.BROWSER_CONFIG.joinpath(data.account_path.get()).with_suffix(".json")
            session = DgpSessionV2.read_cookies(account_path)
            if browser_config_path.exists():
                browser_config = BrowserConfigData.from_path(browser_config_path)
                profile_path = DataPathConfig.BROWSER_PROFILE.joinpath(browser_config.profile_name.get()).absolute()
                userdata = session.post_dgp(DgpSessionV2.USER_INFO).json()
                if userdata["result_code"] != 100:
                    logger.info("USER_INFO result_code=%s; refreshing via browser", userdata.get("result_code"))
                    res = session.post_dgp(DgpSessionV2.LOGIN_URL, json={"prompt": ""}).json()
                    if res["result_code"] != 100:
                        logger.warning("LOGIN_URL refresh failed result_code=%s", res.get("result_code"))
                        raise Exception(res["error"])
                    driver = get_driver(profile_path)
                    code = login_driver(res["data"]["url"], driver)
                    driver.quit()
                    res = session.post_dgp(DgpSessionV2.ACCESS_TOKEN, json={"code": code}).json()
                    if res["result_code"] != 100:
                        logger.warning("ACCESS_TOKEN refresh failed result_code=%s", res.get("result_code"))
                        raise Exception(res["error"])
                    session.actauth = {"accessToken": res["data"]["access_token"]}
                    session.write_bytes(str(account_path))

        dgp_config = session.get_config()
        game = [x for x in dgp_config["contents"] if x["productId"] == data.product_id.get()][0]

        response = session.lunch(data.product_id.get(), game["gameType"]).json()

        if response["result_code"] != 100:
            logger.warning("launch lunch result_code=%s for product_id=%s", response.get("result_code"), data.product_id.get())
            raise Exception(response["error"])

        if response["data"].get("drm_auth_token") is not None:
            filename = b64encode(data.product_id.get().encode("utf-8")).decode("utf-8")
            drm_path = Env.DMM_GAME_PLAYER_HIDDEN_FOLDER.joinpath(filename)
            drm_path.parent.mkdir(parents=True, exist_ok=True)
            with open(drm_path.absolute(), "w+", encoding="utf-8") as f:
                f.write(response["data"]["drm_auth_token"])

        game_file = Path(game["detail"]["path"])
        game_path = game_file.joinpath(response["data"]["exec_file_name"])

        if response["data"]["latest_version"] != game["detail"]["version"]:
            if data.auto_update.get():
                download = session.download(response["data"]["sign"], response["data"]["file_list_url"], game_file)
                box = CTkProgressWindow(self).create()
                for progress, file in download:
                    box.set(progress)
                box.destroy()
                game["detail"]["version"] = response["data"]["latest_version"]
                session.set_config(dgp_config)

        dmm_args = response["data"]["execute_args"].split(" ") + data.game_args.get().split(" ")
        game_path = str(game_path.relative_to(game_file))
        game_full_path = str(game_file.joinpath(game_path))
        is_admin = ProcessManager.admin_check()
        external_tool_pid = None
        if kill:
            process = ProcessManager.run([game_path] + dmm_args, cwd=str(game_file))
            try:
                process.wait(2)
            except subprocess.TimeoutExpired:
                try:
                    for child in psutil.Process(process.pid).children(recursive=True):
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    logger.debug("Parent process already gone during kill: %s", exc)
        else:
            pid_manager = ProcessIdManager()
            timer = time.time()
            if response["data"]["is_administrator"] and (not is_admin) and (not force_non_uac):
                ProcessManager.admin_run([game_path] + dmm_args, cwd=str(game_file))
                game_pid = pid_manager.new_process().search(game_full_path)
                if data.external_tool_path.get() != "":
                    external_tool_pid_manager = ProcessIdManager()
                    ProcessManager.admin_run([data.external_tool_path.get()], cwd=str(game_file))
                    external_tool_pid = external_tool_pid_manager.new_process().search_or_none(data.external_tool_path.get())
                while psutil.pid_exists(game_pid):
                    time.sleep(1)
            else:
                process = ProcessManager.run([game_path] + dmm_args, cwd=str(game_file))
                if data.external_tool_path.get() != "":
                    external_tool_process = ProcessManager.run([data.external_tool_path.get()], cwd=str(game_file))
                    external_tool_pid = external_tool_process.pid
                if process.stdout is not None:
                    for line in process.stdout:
                        logger.debug(decode(line))
            if time.time() - timer < 10:
                logger.warning("Unexpected process termination")
                time.sleep(10 - (time.time() - timer))
                logger.warning("Restarting the process")
                game_pid = pid_manager.new_process().search_or_none(game_full_path)
                if game_pid is not None:
                    while psutil.pid_exists(game_pid):
                        time.sleep(1)
            if data.external_tool_path.get() != "" and external_tool_pid is not None:
                try:
                    for child in psutil.Process(external_tool_pid).children(recursive=True):
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    logger.debug("External tool process already gone: %s", exc)


# NOTE: "Lanch" keeps the upstream (fa0311) spelling — a typo for "Launch".
# Kept intentionally so this class still lines up when diffing against upstream.
# Do NOT "fix" the spelling: renaming silently breaks that parity.
class LanchLauncher(CTk):
    loder: Callable

    def __init__(self, loder):
        super().__init__()

        self.title("Priconne Multi Account Launcher")
        self.geometry("900x600")
        self.withdraw()
        loder(self)

    def create(self):
        HomeTab(self).create().pack(expand=True, fill=ctk.BOTH)
        return self

    @threading_wrapper
    def thread(self, id: str):
        try:
            self.launch(id)
            self.quit()
        except Exception as e:
            if not Env.DEVELOP:
                self.iconify()
                ErrorWindow(self, str(e), traceback.format_exc(), quit=True).create()
            raise

    def launch(self, id: str):
        logger.info("LanchLauncher.launch start: id=%s", id)
        if DgpSessionV2.is_running_dmm():
            logger.warning("LanchLauncher.launch aborted: DMM Game Player already running")
            raise Exception(i18n.t("app.lib.dmm_already_running"))

        path = DataPathConfig.ACCOUNT_SHORTCUT.joinpath(id).with_suffix(".json")
        data = LauncherShortcutData.from_path(path)

        account_name = data.account_path.get()
        from lib.account_swapper import swap_account_data, restore_to_baseline, restore_baseline_if_stale
        try:
            restore_baseline_if_stale()
        except Exception:
            logger.exception("Pre-launch stale-baseline recovery failed in LanchLauncher (non-fatal)")
        swap_account_data(account_name)
        try:
            self._launch_dmm_after_swap(data)
        finally:
            try:
                restore_to_baseline()
            except Exception:
                logger.exception("restore_to_baseline failed in LanchLauncher")

    def _launch_dmm_after_swap(self, data: LauncherShortcutData):
        account_path = DataPathConfig.ACCOUNT.joinpath(data.account_path.get()).with_suffix(".bytes")

        before_session = DgpSessionV2.read_dgp()

        session = DgpSessionV2.read_cookies(Path(account_path))
        if session.get_access_token() is None:
            logger.warning("LanchLauncher.launch: account %s missing access token", data.account_path.get())
            raise Exception(i18n.t("app.launch.export_error"))
        session.write()

        dgp = AppConfig.DATA.dmm_game_player_program_folder.get_path()

        dmm_args = data.dgp_args.get().split(" ")
        process = ProcessManager.run(["DMMGamePlayer.exe"] + dmm_args, cwd=str(dgp.absolute()))

        if process.stdout is not None:
            for line in process.stdout:
                logger.debug(decode(line))

        session = DgpSessionV2.read_dgp()
        if session.get_access_token() is None:
            logger.warning("LanchLauncher.launch: post-launch session missing token; import failed")
            raise Exception(i18n.t("app.launch.import_error"))
        session.write_bytes(str(account_path))
        before_session.write()
        logger.info("LanchLauncher.launch complete: id=%s", id)


class GameLauncherUac(CTk):
    @staticmethod
    def wait(args: list[str]):
        if not ProcessManager.admin_check():
            pid_manager = ProcessIdManager()
            ProcessManager.admin_run([sys.executable, *args])
            logger.debug("Spawned admin process: %s", sys.executable)
            game_pid = pid_manager.new_process().search(sys.executable)
            while psutil.pid_exists(game_pid):
                time.sleep(1)


def decode(s: bytes) -> str:
    for encoding in ("utf-8", "cp932"):
        try:
            return s.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return s.decode("utf-8", errors="replace").strip()
