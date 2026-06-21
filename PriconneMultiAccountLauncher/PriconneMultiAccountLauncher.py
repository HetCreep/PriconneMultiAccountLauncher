import argparse
import logging
import os
import sys
import time
from tkinter import font, messagebox

import customtkinter as ctk
import i18n
from app import App
from coloredlogs import ColoredFormatter
from component.logger import LoggingHandlerMask, StyleScheme, TkinkerLogger
from customtkinter import ThemeManager
from launch import GameLauncher, GameLauncherUac, LanchLauncher
from lib.DGPSessionV2 import DgpSessionV2
from lib.log_sanitizer import install_redaction_filter
from lib.single_instance import SingleInstanceLock
from models.setting_data import AppConfig
from static.config import AssetsPathConfig, DataPathConfig, UrlConfig
from static.env import Env
from static.loder import config_loder, config_migrate
from tkinter_colored_logging_handlers.main import LoggingHandler


def loder(master: LanchLauncher):
    DataPathConfig.ACCOUNT.mkdir(exist_ok=True, parents=True)
    DataPathConfig.ACCOUNT_SHORTCUT.mkdir(exist_ok=True, parents=True)
    DataPathConfig.SHORTCUT.mkdir(exist_ok=True, parents=True)
    DataPathConfig.BROWSER_PROFILE.mkdir(exist_ok=True, parents=True)
    DataPathConfig.BROWSER_CONFIG.mkdir(exist_ok=True, parents=True)

    config_loder()
    i18n.load_path.append(str(AssetsPathConfig.I18N))
    i18n.set("locale", AppConfig.DATA.lang.get())

    handlers: list[logging.Handler] = []

    if AppConfig.DATA.output_logfile.get() and not any([isinstance(x, logging.FileHandler) for x in logging.getLogger().handlers]):
        DataPathConfig.LOG.mkdir(exist_ok=True, parents=True)
        handler = logging.FileHandler(DataPathConfig.LOG.joinpath(f"{time.strftime('%Y%m%d%H%M%S')}.log"), encoding="utf-8")
        handlers.append(handler)

    if AppConfig.DATA.debug_window.get() and not any([isinstance(x, LoggingHandler) for x in logging.getLogger().handlers]):
        handle = LoggingHandlerMask if AppConfig.DATA.mask_token.get() else LoggingHandler
        tk_handler = handle(TkinkerLogger(master).create().box, scheme=StyleScheme)
        tk_handler.setFormatter(ColoredFormatter("[%(levelname)s] [%(asctime)s] %(message)s"))
        handlers.append(tk_handler)

    if not any([isinstance(x, logging.StreamHandler) for x in logging.getLogger().handlers]):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(ColoredFormatter("[%(levelname)s] [%(asctime)s] %(message)s"))
        handlers.append(stream_handler)

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)
    install_redaction_filter()

    logging.debug("==================================================")
    logging.debug("===== PriconneMultiAccountLauncher Environment =====")
    logging.debug("==================================================")
    logging.debug(Env.dump())
    logging.debug(AppConfig.DATA.to_dict())
    logging.debug(AppConfig.DEVICE.to_dict())
    logging.debug(DataPathConfig.dump())
    logging.debug(AssetsPathConfig.dump())
    logging.debug(UrlConfig.dump())
    logging.debug(sys.argv)
    logging.debug("==================================================")
    logging.debug("==================================================")
    logging.debug("==================================================")

    config_migrate()

    if AppConfig.DATA.proxy_all.get() != "":
        os.environ["ALL_PROXY"] = AppConfig.DATA.proxy_all.get()
    if AppConfig.DATA.dmm_proxy_all.get() != "":
        DgpSessionV2.PROXY["http"] = AppConfig.DATA.dmm_proxy_all.get()
        DgpSessionV2.PROXY["https"] = AppConfig.DATA.dmm_proxy_all.get()

    ctk.set_default_color_theme(str(AssetsPathConfig.THEMES.joinpath(AppConfig.DATA.theme.get()).with_suffix(".json")))

    additional_theme = {
        "MenuComponent": {"text_color": ["#000000", "#ffffff"]},
        "LabelComponent": {"fg_color": ["#F9F9FA", "#343638"], "required_color": ["red", "red"]},
        "CheckBoxComponent": {"checkbox_width": 16, "checkbox_height": 16, "border_width": 2},
    }
    for key, value in additional_theme.items():
        ThemeManager.theme[key] = value

    # Font modes:
    #   auto   = per-locale font from app.font.main (Segoe UI / Microsoft YaHei UI / Leelawadee UI / ...)
    #   system = Windows TkDefaultFont (usually Segoe UI; fewer script-fallback guarantees)
    # Legacy values ("i18n", "theme") collapse to "auto"; "os" collapses to "system".
    font_mode = AppConfig.DATA.theme_font.get()
    if font_mode in ("system", "os"):
        os_default_font = font.nametofont("TkDefaultFont").config()
        if os_default_font is None:
            logging.warning("Default Tk font not available; falling back to locale font")
            font_mode = "auto"
        else:
            ThemeManager.theme["CTkFont"]["family"] = os_default_font["family"]

    if font_mode not in ("system", "os"):  # auto (default) + any legacy i18n/theme
        i18n_font = i18n.t("app.font.main")
        if i18n_font not in font.families():
            logging.warning("Font %s not found; CTk default will apply", i18n_font)
        ThemeManager.theme["CTkFont"]["family"] = i18n_font

    ctk.set_appearance_mode(AppConfig.DATA.appearance_mode.get())

    import tkinter as _tk
    try:
        ctk.set_widget_scaling(AppConfig.DATA.window_scaling.get())
    except (ValueError, TypeError, _tk.TclError) as exc:
        # TclError fires when CTk's ScalingTracker tries to update widgets that
        # were destroyed between scaling calls (CTk known limitation). Safe to swallow.
        logging.warning("Widget scaling not applied: %s", exc)


argpar = argparse.ArgumentParser(
    prog="PriconneMultiAccountLauncher",
    usage="https://github.com/HetCreep/PriconneMultiAccountLauncher",
    description="Priconne Multi Account Launcher",
)
argpar.add_argument("id", default=None, nargs="?")
argpar.add_argument("--type", default="game")


try:
    arg = argpar.parse_args()
    id = arg.id
    type = arg.type
except SystemExit:
    raise

# Single-instance guard. Each role uses a distinct mutex name so the main GUI,
# game launches, kill mode, and force-user-game can coexist (they manipulate
# different state). The main GUI guard prevents two GUI instances racing on
# data/ files. Game-launch subprocesses are deliberately allowed to be
# concurrent across different shortcuts (one per game instance).
_instance_lock = SingleInstanceLock("gui" if id is None else f"launch.{type}.{id}")
if not _instance_lock.acquire():
    messagebox.showwarning(
        "PriconneMultiAccountLauncher",
        "Another instance is already running. Switch to the existing window."
    )
    sys.exit(0)

if id is None:
    _app = App(loder).create()
    # Crash-recovery probe: if a previous launch was killed before its
    # post-game-exit restore could run, baseline state on disk is now whichever
    # B/C slot was last swapped in. Detect via stale last_active marker and
    # roll back to baseline so the user's primary DMM account is usable again.
    try:
        from lib.account_swapper import restore_baseline_if_stale
        restore_baseline_if_stale()
    except Exception:
        logging.exception("Startup baseline-recovery check failed (non-fatal — continuing)")
    _app.mainloop()

elif type == "launcher":
    lanch = LanchLauncher(loder).create()
    lanch.thread(id)
    lanch.mainloop()

elif type == "game":
    lanch = GameLauncher(loder).create()
    lanch.thread(id)
    lanch.mainloop()

elif type == "force-user-game":
    GameLauncherUac.wait([id, "--type", "kill-game"])
    lanch = GameLauncher(loder).create()
    lanch.thread(id, force_non_uac=True)
    lanch.mainloop()

elif type == "kill-game":
    lanch = GameLauncher(loder).create()
    lanch.thread(id, kill=True)
    lanch.mainloop()

else:
    raise Exception("type error")
