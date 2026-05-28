import logging
import traceback
from typing import Callable

import customtkinter as ctk
import i18n
from component.tab_menu import TabMenuComponent
from customtkinter import CTk, CTkFrame, CTkLabel
from static.config import AssetsPathConfig

logger = logging.getLogger(__name__)

# Tab imports wrapped — a single broken tab (e.g. missing optional dep) shouldn't
# kill the entire app. Failed tabs are replaced by an inline error label so the
# user still sees the GUI and can read the failure.
# Static `from ... import ...` (NOT __import__) so PyInstaller's static analysis
# bundles each tab module into the frozen exe.
_tab_failures: dict[str, str] = {}

try:
    from tab.account import AccountTab
except Exception:
    AccountTab = None  # type: ignore[misc,assignment]
    _tab_failures["Account"] = traceback.format_exc()
    logger.error("Failed to import tab.account.AccountTab\n%s", _tab_failures["Account"])

try:
    from tab.help import HelpTab
except Exception:
    HelpTab = None  # type: ignore[misc,assignment]
    _tab_failures["Help"] = traceback.format_exc()
    logger.error("Failed to import tab.help.HelpTab\n%s", _tab_failures["Help"])

try:
    from tab.home import HomeTab
except Exception:
    HomeTab = None  # type: ignore[misc,assignment]
    _tab_failures["Home"] = traceback.format_exc()
    logger.error("Failed to import tab.home.HomeTab\n%s", _tab_failures["Home"])

try:
    from tab.setting import SettingTab
except Exception:
    SettingTab = None  # type: ignore[misc,assignment]
    _tab_failures["Setting"] = traceback.format_exc()
    logger.error("Failed to import tab.setting.SettingTab\n%s", _tab_failures["Setting"])

try:
    from tab.shortcut import ShortcutTab
except Exception:
    ShortcutTab = None  # type: ignore[misc,assignment]
    _tab_failures["Shortcut"] = traceback.format_exc()
    logger.error("Failed to import tab.shortcut.ShortcutTab\n%s", _tab_failures["Shortcut"])


class App(CTk):
    loder: Callable
    tab: TabMenuComponent

    def __init__(self, loder):
        super().__init__()

        self.title("Priconne Multi Account Launcher")
        self.geometry("900x600")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.iconbitmap(default=str(AssetsPathConfig.ICON_MAIN))
        self.loder = loder
        self.tab = TabMenuComponent(self)
        loder(self)

    def _on_close(self) -> None:
        try:
            self.quit()
        finally:
            self.destroy()

    def create(self):
        self.tab.create()
        self.tab.add(text=i18n.t("app.tab.home"), callback=self.home_callback)
        self.tab.add(text=i18n.t("app.tab.shortcut"), callback=self.shortcut_callback)
        self.tab.add(text=i18n.t("app.tab.account"), callback=self.account_callback)
        self.tab.add(text=i18n.t("app.tab.setting"), callback=self.setting_callback)
        self.tab.add(text=i18n.t("app.tab.help"), callback=self.help_callback)
        return self

    def _render_tab(self, master, tab_cls, tab_label: str):
        if tab_cls is None:
            self._show_tab_error(master, tab_label, _tab_failures.get(tab_label, "(no traceback captured)"), "failed to load")
            return
        try:
            tab_cls(master).create().pack(expand=True, fill=ctk.BOTH)
        except Exception:
            tb = traceback.format_exc()
            logger.exception("Runtime error rendering tab '%s'", tab_label)
            self._show_tab_error(master, tab_label, tb, "crashed at runtime")

    def _show_tab_error(self, master, tab_label: str, tb: str, phase: str) -> None:
        from customtkinter import CTkScrollableFrame, CTkTextbox
        scroll = CTkScrollableFrame(master, fg_color="transparent")
        scroll.pack(expand=True, fill=ctk.BOTH, padx=10, pady=10)
        CTkLabel(
            scroll,
            text=f"Tab '{tab_label}' {phase} — traceback:",
            justify=ctk.LEFT,
        ).pack(anchor=ctk.W, pady=(0, 5))
        box = CTkTextbox(scroll, height=400, wrap="word")
        box.pack(fill=ctk.BOTH, expand=True)
        box.insert("0.0", tb)

    def home_callback(self, master: CTkFrame):
        self._render_tab(master, HomeTab, "Home")

    def shortcut_callback(self, master: CTkFrame):
        self._render_tab(master, ShortcutTab, "Shortcut")

    def account_callback(self, master: CTkFrame):
        self._render_tab(master, AccountTab, "Account")

    def setting_callback(self, master):
        self._render_tab(master, SettingTab, "Setting")

    def help_callback(self, master):
        self._render_tab(master, HelpTab, "Help")
