import json
import logging
import os
import time
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk
import i18n

logger = logging.getLogger(__name__)
from component.component import CheckBoxComponent, ConfirmWindow, DirectoryPathComponent, EntryComponent, OptionMenuComponent, OptionMenuTupleComponent, PaddingComponent
from component.tab_menu import TabMenuComponent
from customtkinter import CTkBaseClass, CTkButton, CTkFrame, CTkInputDialog, CTkLabel, CTkSlider
from component.auto_scroll_frame import CTkAutoScrollFrame
from lib.backup import export_backup, import_backup
from lib.toast import ToastController, error_toast
from models.setting_data import AppConfig, DeviceData, SettingData
from static.config import AssetsPathConfig, DataPathConfig
from utils.utils import get_supported_lang


class SettingTab(CTkFrame):
    tab: TabMenuComponent

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.tab = TabMenuComponent(self)

    def create(self):
        self.tab.create()
        self.tab.add(text=i18n.t("app.tab.general"), callback=self.general_callback)
        self.tab.add(text=i18n.t("app.tab.appearance"), callback=self.appearance_callback)
        self.tab.add(text=i18n.t("app.tab.advanced"), callback=self.advanced_callback)
        self.tab.add(text=i18n.t("app.tab.device"), callback=self.device_callback)
        self.tab.add(text=i18n.t("app.tab.backup"), callback=self.backup_callback)
        self.tab.add(text=i18n.t("app.tab.other"), callback=self.other_callback)
        return self

    def general_callback(self, master: CTkBaseClass):
        SettingGeneralTab(master).create().pack(expand=True, fill=ctk.BOTH)

    def appearance_callback(self, master: CTkBaseClass):
        SettingAppearanceTab(master).create().pack(expand=True, fill=ctk.BOTH)

    def advanced_callback(self, master: CTkBaseClass):
        SettingAdvancedTab(master).create().pack(expand=True, fill=ctk.BOTH)

    def device_callback(self, master: CTkBaseClass):
        SettingDeviceTab(master).create().pack(expand=True, fill=ctk.BOTH)

    def backup_callback(self, master: CTkBaseClass):
        SettingBackupTab(master).create().pack(expand=True, fill=ctk.BOTH)

    def other_callback(self, master: CTkBaseClass):
        SettingOtherTab(master).create().pack(expand=True, fill=ctk.BOTH)


class _SettingSaveMixin:
    """Shared save / reload callbacks for split setting sub-tabs."""

    toast: ToastController

    @error_toast
    def save_callback(self):
        logger.info("Setting save: persisting config to %s", DataPathConfig.APP_CONFIG)
        with open(DataPathConfig.APP_CONFIG, "w+", encoding="utf-8") as f:
            json.dump(AppConfig.DATA.to_dict(), f)
        self.reload_callback()

    @error_toast
    def reload_callback(self):
        from app import App

        logger.info("Setting reload: re-running loder + create")
        app = self.winfo_toplevel()
        assert isinstance(app, App)
        app.loder(app)
        app.create()
        self.toast.info(i18n.t("app.setting.save_success"))


class SettingGeneralTab(CTkAutoScrollFrame, _SettingSaveMixin):
    """DMM paths + locale + update check."""

    toast: ToastController
    data: SettingData
    lang: list[tuple[str, str]]

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.data = AppConfig.DATA
        self.lang = get_supported_lang()

    def create(self):
        DirectoryPathComponent(self, text=i18n.t("app.setting.dmm_game_player_program_folder"),
                               variable=self.data.dmm_game_player_program_folder, required=True).create()
        DirectoryPathComponent(self, text=i18n.t("app.setting.dmm_game_player_data_folder"),
                               variable=self.data.dmm_game_player_data_folder, required=True).create()
        OptionMenuTupleComponent(self, text=i18n.t("app.setting.lang"),
                                 values=self.lang, variable=self.data.lang).create()

        PaddingComponent(self, height=10).create()
        CheckBoxComponent(self, text=i18n.t("app.setting.disable_update_check"),
                          variable=self.data.disable_update_check).create()

        PaddingComponent(self, height=10).create()
        CTkButton(self, text=i18n.t("app.setting.save"), command=self.save_callback).pack(fill=ctk.X, pady=10)
        return self


class SettingAppearanceTab(CTkAutoScrollFrame, _SettingSaveMixin):
    """Theme + appearance mode + font preset + window scaling."""

    toast: ToastController
    data: SettingData
    theme: list[str]

    _theme_cache: Optional[list[str]] = None

    @classmethod
    def _get_themes(cls) -> list[str]:
        if cls._theme_cache is None:
            cls._theme_cache = sorted(x.stem for x in AssetsPathConfig.THEMES.iterdir())
        return cls._theme_cache

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.data = AppConfig.DATA
        self.theme = self._get_themes()

    def create(self):
        OptionMenuComponent(self, text=i18n.t("app.setting.theme"),
                            values=self.theme, variable=self.data.theme).create()
        OptionMenuComponent(self, text=i18n.t("app.setting.appearance"),
                            values=["light", "dark", "system"], variable=self.data.appearance_mode).create()

        text = i18n.t("app.setting.font_preset")
        OptionMenuComponent(self, text=text, tooltip=i18n.t("app.setting.font_preset_tooltip"),
                            values=["auto", "system"], variable=self.data.theme_font).create()

        PaddingComponent(self, height=5).create()
        CTkLabel(self, text=i18n.t("app.setting.window_scaling")).pack(anchor=ctk.W)
        scaling_row = CTkFrame(self, fg_color="transparent")
        scaling_row.pack(fill=ctk.X, expand=True)
        CTkSlider(scaling_row, from_=0.75, to=1.25, variable=self.data.window_scaling).pack(
            side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 5))
        CTkButton(scaling_row, text=i18n.t("app.setting.reset_to_auto"), width=120,
                  command=lambda: self.data.window_scaling.set(1.0)).pack(side=ctk.LEFT)

        PaddingComponent(self, height=10).create()
        CTkButton(self, text=i18n.t("app.setting.save"), command=self.save_callback).pack(fill=ctk.X, pady=10)
        return self


class SettingAdvancedTab(CTkAutoScrollFrame, _SettingSaveMixin):
    """Proxies + diagnostics (debug window, log to file, mask token)."""

    toast: ToastController
    data: SettingData

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.data = AppConfig.DATA

    def create(self):
        text = i18n.t("app.setting.proxy_all")
        EntryComponent(self, text=text, tooltip=i18n.t("app.setting.proxy_all_tooltip"),
                       variable=self.data.proxy_all).create()
        text = i18n.t("app.setting.dmm_proxy_all")
        EntryComponent(self, text=text, tooltip=i18n.t("app.setting.dmm_proxy_all_tooltip"),
                       variable=self.data.dmm_proxy_all).create()

        PaddingComponent(self, height=10).create()
        CheckBoxComponent(self, text=i18n.t("app.setting.debug_window"), variable=self.data.debug_window).create()
        CheckBoxComponent(self, text=i18n.t("app.setting.output_logfile"), variable=self.data.output_logfile).create()
        CheckBoxComponent(self, text=i18n.t("app.setting.mask_token"), variable=self.data.mask_token).create()

        PaddingComponent(self, height=10).create()
        CTkButton(self, text=i18n.t("app.setting.save"), command=self.save_callback).pack(fill=ctk.X, pady=10)
        return self


class SettingDeviceTab(CTkAutoScrollFrame):
    toast: ToastController
    data: DeviceData

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.data = AppConfig.DEVICE

    def create(self):
        CTkLabel(self, text=i18n.t("app.setting.device_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
        EntryComponent(self, text=i18n.t("app.setting.mac_address"), variable=self.data.mac_address, required=True).create()
        EntryComponent(self, text=i18n.t("app.setting.hdd_serial"), variable=self.data.hdd_serial, required=True).create()
        EntryComponent(self, text=i18n.t("app.setting.motherboard"), variable=self.data.motherboard, required=True).create()
        EntryComponent(self, text=i18n.t("app.setting.user_os"), variable=self.data.user_os, required=True).create()
        CTkButton(self, text=i18n.t("app.setting.save"), command=self.save_callback).pack(fill=ctk.X, pady=10)
        return self

    def save_callback(self):
        logger.info("SettingDeviceTab.save_callback: persisting device config")
        with open(DataPathConfig.DEVICE, "w+", encoding="utf-8") as f:
            json.dump(AppConfig.DEVICE.to_dict(), f)
        AppConfig.DEVICE.update()
        self.toast.info(i18n.t("app.setting.save_success"))


class SettingBackupTab(CTkAutoScrollFrame):
    """Cross-machine backup / restore (passphrase-protected .pmal)."""

    toast: ToastController

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)

    def create(self):
        CTkLabel(self, text=i18n.t("app.setting.backup_detail"),
                 justify=ctk.LEFT, wraplength=560).pack(anchor=ctk.W, pady=(0, 10))
        CTkButton(self, text=i18n.t("app.setting.export_backup"), command=self.export_callback).pack(fill=ctk.X, pady=5)
        CTkButton(self, text=i18n.t("app.setting.import_backup"), command=self.import_callback).pack(fill=ctk.X, pady=5)
        return self

    def _ask_passphrase(self, title_key: str) -> Optional[str]:
        dlg = CTkInputDialog(
            text=i18n.t("app.setting.passphrase_prompt"),
            title=i18n.t(title_key),
        )
        pw = dlg.get_input()
        if pw is None:
            return None
        pw = pw.strip()
        if len(pw) < 8:
            raise Exception(i18n.t("app.setting.passphrase_too_short"))
        return pw

    @error_toast
    def export_callback(self):
        default_name = f"priconne-backup-{time.strftime('%Y%m%d-%H%M%S')}.pmal"
        path = filedialog.asksaveasfilename(
            title=i18n.t("app.setting.export_backup"),
            defaultextension=".pmal",
            initialfile=default_name,
            filetypes=[("Priconne backup", "*.pmal"), ("All files", "*.*")],
        )
        if not path:
            return
        passphrase = self._ask_passphrase("app.setting.export_backup")
        if passphrase is None:
            return
        logger.info("Exporting backup to %s", path)
        summary = export_backup(passphrase, Path(path))
        self.toast.info(i18n.t("app.setting.export_success", count=summary["accounts"]))

    @error_toast
    def import_callback(self):
        path = filedialog.askopenfilename(
            title=i18n.t("app.setting.import_backup"),
            filetypes=[("Priconne backup", "*.pmal"), ("All files", "*.*")],
        )
        if not path:
            return
        passphrase = self._ask_passphrase("app.setting.import_backup")
        if passphrase is None:
            return
        logger.info("Importing backup from %s", path)
        summary = import_backup(passphrase, Path(path))
        self.toast.info(i18n.t("app.setting.import_success", count=summary["accounts"]))
        # Imported accounts land in data/account/ but other tabs (Shortcut →
        # Create dropdown, Account → Edit list) snapshot the dir at their own
        # __init__. Reload the app so the next tab the user visits picks up
        # the freshly-imported entries without requiring a manual restart.
        self.after(150, self._reload_app)

    def _reload_app(self) -> None:
        try:
            from app import App
            app = self.winfo_toplevel()
            if isinstance(app, App):
                app.loder(app)
                app.create()
            else:
                logger.warning("Backup import reload skipped — toplevel is not App (%s)", type(app).__name__)
        except Exception:
            logger.exception("Backup import post-success reload failed (non-fatal)")


class SettingOtherTab(CTkAutoScrollFrame, _SettingSaveMixin):
    """Reset all + open save folder."""

    toast: ToastController

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)

    def create(self):
        CTkLabel(self, text=i18n.t("app.setting.other_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
        CTkButton(self, text=i18n.t("app.setting.open_save_folder"), command=self.open_folder_callback).pack(fill=ctk.X, pady=10)

        def reset_command():
            return ConfirmWindow(self, command=self.delete_callback, text=i18n.t("app.setting.confirm_reset")).create()

        CTkButton(self, text=i18n.t("app.setting.reset_all_settings"), command=reset_command).pack(fill=ctk.X, pady=10)
        return self

    @error_toast
    def open_folder_callback(self):
        os.startfile(DataPathConfig.DATA)

    @error_toast
    def delete_callback(self):
        logger.warning("SettingOtherTab.delete_callback: removing %s and reloading", DataPathConfig.APP_CONFIG)
        DataPathConfig.APP_CONFIG.unlink()
        self.reload_callback()
