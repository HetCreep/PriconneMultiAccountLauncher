import logging
import webbrowser

import customtkinter as ctk
import i18n
from customtkinter import CTkBaseClass, CTkButton, CTkTextbox
from component.auto_scroll_frame import CTkAutoScrollFrame
from lib.toast import ToastController
from static.config import AssetsPathConfig, UrlConfig

logger = logging.getLogger(__name__)


class HelpTab(CTkAutoScrollFrame):
    toast: ToastController

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)

    def create(self):
        try:
            with open(AssetsPathConfig.LICENSE, "r", encoding="utf-8") as f:
                license = f.read()
        except OSError as exc:
            logger.warning("LICENSE asset unavailable at %s: %s", AssetsPathConfig.LICENSE, exc)
            license = f"License file unavailable: {exc}\n\nSee LICENSE in the install directory."

        box = CTkTextbox(self, width=590, height=400)
        box.pack(padx=10, pady=10)
        box.insert("0.0", license)

        CTkButton(self, text=i18n.t("app.help.coop_in_develop"), command=self.contribution_callback).pack(fill=ctk.X, pady=(10, 0))
        CTkButton(self, text=i18n.t("app.help.donations_to_developer"), command=self.donation_callback).pack(fill=ctk.X, pady=10)
        CTkButton(self, text=i18n.t("app.help.bug_report"), command=self.report_callback).pack(fill=ctk.X, pady=(0, 10))

        return self

    def contribution_callback(self):
        webbrowser.open(UrlConfig.CONTRIBUTION)

    def donation_callback(self):
        webbrowser.open(UrlConfig.DONATE)

    def report_callback(self):
        webbrowser.open(UrlConfig.ISSUE)
