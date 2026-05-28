import logging
import webbrowser
from tkinter import Misc
from typing import Optional

import i18n
from customtkinter import CTkFont, CTkFrame, CTkImage, CTkLabel
from lib.toast import ToastController
from lib.version import Version
from lib.version_check import get_latest_version
from models.setting_data import AppConfig
from PIL import Image
from static.config import AssetsPathConfig, UrlConfig
from static.env import Env

logger = logging.getLogger(__name__)


class HomeTab(CTkFrame):
    toast: ToastController
    update_flag: bool = False
    _image_cache: Optional[CTkImage] = None

    def __init__(self, master: Misc):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)

    @classmethod
    def _get_logo_image(cls) -> CTkImage:
        if cls._image_cache is None:
            cls._image_cache = CTkImage(
                light_image=Image.open(AssetsPathConfig.ICONS.joinpath("PriconneMultiAccountLauncher.png")),
                size=(240, 240),
            )
        return cls._image_cache

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        """True only when `latest` is a strictly newer, parseable version than `current`.

        Guards against a stale update-check cache (data/ is preserved across
        upgrades) still naming an older/equal tag — never nag when already current.
        """
        try:
            return Version(latest) > Version(current)
        except ValueError:
            logger.debug("Update-check: unparseable version (latest=%r current=%r)", latest, current)
            return False

    def create(self):
        frame = CTkFrame(self, fg_color="transparent")
        frame.pack(anchor="center", expand=1)

        CTkLabel(frame, image=self._get_logo_image(), text="").pack()
        CTkLabel(frame, text=i18n.t("app.title"), font=CTkFont(size=28)).pack(pady=20)

        CTkLabel(frame, text=Env.VERSION, font=CTkFont(size=18)).pack()

        if HomeTab.update_flag is False:
            disabled = AppConfig.DATA.disable_update_check.get()
            latest = get_latest_version(Env.VERSION, disabled=disabled)
            if self._is_newer(latest, Env.VERSION):
                logger.info("Update available: current=%s latest=%s", Env.VERSION, latest)
                HomeTab.update_flag = True
                # Toast text reminds user to verify SHA-256 on the release page
                # before running the installer — per release-verification.md.
                message = i18n.t("app.home.new_version") + " (Verify SHA-256 on release page before running.)"
                self.toast.command_info(message, lambda: webbrowser.open(UrlConfig.RELEASE))

        return self
