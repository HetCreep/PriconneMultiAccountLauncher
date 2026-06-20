"""Shortcut tab — DIRECT game-launch shortcuts.

Top-level "Shortcut" tab with two sub-tabs (Create + Edit). Each shortcut
launches the game executable directly via `GameLauncher` (argparse default
`--type game`). Bypasses the DMM client UI — faster, slightly higher
detection risk vs the DMM-relay pathway (which lives in the separate
`Fast Launch GamePlayer` tab — see `tab/launcher_shortcut.py`).

Shortcuts live under `DataPathConfig.SHORTCUT/`.
"""

import logging
import webbrowser
from pathlib import Path
from tkinter import Frame, StringVar
from typing import Callable

import customtkinter as ctk
import i18n

logger = logging.getLogger(__name__)
from component.auto_scroll_frame import CTkAutoScrollFrame
from component.component import (
    ButtonComponent,
    CheckBoxComponent,
    EntryComponent,
    FilePathComponent,
    LabelComponent,
    OptionMenuTupleComponent,
    PaddingComponent,
)
from component.tab_menu import TabMenuComponent
from customtkinter import CTkBaseClass, CTkButton, CTkFrame, CTkLabel, CTkOptionMenu
from lib.DGPSessionV2 import DgpSessionV2
from lib.process_manager import Shortcut
from lib.toast import ToastController, error_toast
from models.shortcut_data import ShortcutData
from static.config import DataPathConfig
from static.constant import Constant
from static.env import Env
from utils.utils import children_destroy, file_create


class ShortcutTab(CTkFrame):
    tab: TabMenuComponent

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.tab = TabMenuComponent(self)

    def create(self):
        self.tab.create()
        self.tab.add(text=i18n.t("app.tab.create"), callback=self.create_callback)
        self.tab.add(text=i18n.t("app.tab.edit"), callback=self.edit_callback)
        return self

    def create_callback(self, master: CTkBaseClass):
        ShortcutCreate(master).create().pack(expand=True, fill=ctk.BOTH)

    def edit_callback(self, master: CTkBaseClass):
        ShortcutEdit(master).create().pack(expand=True, fill=ctk.BOTH)


class ShortcutBase(CTkAutoScrollFrame):
    toast: ToastController
    data: ShortcutData
    filename: StringVar
    product_ids: list[str]
    dgp_config: dict
    account_name_list: list[tuple[str, str]]

    def __init__(self, master: Frame):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.data = ShortcutData()
        self.data.product_id.set("priconner")  # Lock product ID to priconner
        self.filename = StringVar()
        self.dgp_config = DgpSessionV2().get_config()
        self.product_ids = ["priconner"]
        self.account_name_list = [(x.stem, x.stem) for x in DataPathConfig.ACCOUNT.iterdir() if x.suffix == ".bytes"]
        self.account_name_list.insert(0, (Constant.ALWAYS_EXTRACT_FROM_DMM, i18n.t("app.shortcut.always_extract_from_dmm")))

        # Locked-display value for the Registry row on the form — the per-account
        # swap target (registry-only isolation; manifest.db is shared, not shown).
        self.registry_path_var = StringVar(value=r"HKEY_CURRENT_USER\Software\Cygames\PrincessConnectReDive")

    def create(self):
        text = i18n.t("app.shortcut.filename")
        EntryComponent(self, text=text, tooltip=i18n.t("app.shortcut.filename_tooltip"), required=True, variable=self.filename, alnum_only=True).create()

        text = i18n.t("app.shortcut.product_id")
        EntryComponent(self, text=text, tooltip=i18n.t("app.shortcut.product_id_tooltip"), variable=self.data.product_id, state="disabled").create()
        text = i18n.t("app.shortcut.account_path")
        OptionMenuTupleComponent(self, text=text, tooltip=i18n.t("app.shortcut.account_path_tooltip"), values=self.account_name_list, variable=self.data.account_path).create()

        text = i18n.t("app.shortcut.game_args")
        EntryComponent(self, text=text, tooltip=i18n.t("app.shortcut.game_args_tooltip"), variable=self.data.game_args).create()

        text = i18n.t("app.shortcut.external_tool_path")
        FilePathComponent(self, text=text, tooltip=i18n.t("app.shortcut.external_tool_path_tooltip"), variable=self.data.external_tool_path).create()

        # Account isolation is registry-only (see lib/account_swapper). manifest.db
        # is shared asset data and is never swapped, so it's no longer surfaced
        # here. Registry path stays — that IS the per-account swap target.
        registry_text = i18n.t("app.shortcut.registry_path")
        EntryComponent(self, text=registry_text, tooltip=i18n.t("app.shortcut.registry_path_tooltip"), variable=self.registry_path_var, state="disabled").create()

        CheckBoxComponent(self, text=i18n.t("app.shortcut.auto_update"), variable=self.data.auto_update).create()

        PaddingComponent(self, height=5).create()

        text = i18n.t("app.shortcut.create_shortcut_and_save")
        ButtonComponent(self, text=text, tooltip=i18n.t("app.shortcut.create_shortcut_and_save_tooltip"), command=self.save_callback).create()
        text = i18n.t("app.shortcut.save_only")
        ButtonComponent(self, text=text, tooltip=i18n.t("app.shortcut.save_only_tooltip"), command=self.save_only_callback).create()
        return self

    def save(self):
        if self.data.product_id.get() == "":
            raise Exception(i18n.t("app.shortcut.product_id_not_entered"))
        if self.filename.get() == "":
            raise Exception(i18n.t("app.shortcut.filename_not_entered"))
        if self.data.account_path.get() == "":
            raise Exception(i18n.t("app.shortcut.account_path_not_entered"))

        path = DataPathConfig.SHORTCUT.joinpath(self.filename.get()).with_suffix(".json")
        file_create(path, name=i18n.t("app.shortcut.filename"))
        self.data.write_path(path)
        logger.info("Saved direct shortcut: %s", path)

    def save_handler(self, fn: Callable[[], None]):
        pass

    @error_toast
    def save_callback(self):
        def fn():
            filename = self.filename.get()
            logger.info("save_callback start: file=%s", filename)
            name: str = filename
            icon: Path | None = None
            try:
                name, icon, _admin = self.get_game_info()
            except Exception:
                logger.exception("get_game_info failed in save for %s", filename)
                try:
                    self.toast.error(i18n.t("app.shortcut.game_info_error"))
                except Exception:
                    logger.warning("toast.error failed; continuing with filename fallback")
                # Fail-soft: locate the game exec locally so the .lnk still gets
                # the proper game icon instead of falling back to the launcher's
                # own generic icon. Matches the visual outcome upstream produces
                # when its session is valid.
                icon = self._resolve_local_game_icon()

            source = Env.DESKTOP.joinpath(name).with_suffix(".lnk")
            Shortcut().create(source=source, args=[filename], icon=icon)
            logger.info("save shortcut created: %s (icon=%s)", source, icon)
            self.toast.info(i18n.t("app.shortcut.save_success"))

        self.save_handler(fn)

    def _resolve_local_game_icon(self) -> Path | None:
        """Find the game's executable on disk via dgp_config — does not call DMM API.

        Used as an icon fallback for the .lnk when the live API call fails
        (token expired, network down, etc.). Returns the .exe Path if found
        and existing on disk, else None (caller falls back to launcher icon)."""
        try:
            product_id = self.data.product_id.get()
            game = next(x for x in self.dgp_config["contents"] if x["productId"] == product_id)
            game_path = Path(game["detail"]["path"])
            # Priconne's exec is PrincessConnectReDive.exe. For other product_ids,
            # walk the install dir for a single .exe — but the project locks
            # product_id to priconner so the direct lookup is sufficient.
            candidates = [
                game_path.joinpath("PrincessConnectReDive.exe"),
            ]
            for exe in candidates:
                if exe.exists():
                    return exe
            # Fallback: scan install dir for any .exe (skip Unity crash handlers / installers).
            try:
                for child in game_path.iterdir():
                    if child.suffix.lower() == ".exe" and "UnityCrashHandler" not in child.stem and "unins" not in child.stem.lower():
                        return child
            except OSError as exc:
                logger.debug("Game dir scan failed: %s", exc)
        except Exception as exc:
            logger.debug("Local game icon resolution failed: %s", exc)
        return None

    @error_toast
    def save_only_callback(self):
        def fn():
            self.toast.info(i18n.t("app.shortcut.save_success"))

        self.save_handler(fn)

    def unity_command_line_args_callback(self):
        webbrowser.open(i18n.t("app.shortcut.unity_command_line_args_link"))

    def get_game_info(self) -> tuple[str, Path | None, bool]:
        """Resolve the shortcut's display name + game icon for "Create Shortcut".

        Intentionally does NOT call the live DMM ``lunch()`` API. ``lunch()`` is a
        stateful game-LAUNCH RPC (it writes a DRM token + play record server-side)
        and requires a *fresh* access token, so invoking it just to fetch a title
        made shortcut creation fail with ``result_code=203``
        ("E210012: refresh token is invalid") whenever the per-account stored token
        had expired. The token is only refreshed on the real launch path
        (``launch.py._launch_after_swap``), never here — so creating a shortcut must
        not depend on it. The game title is not present in the local ``dmmgame.cnf``
        and is discarded anyway for non-cp932 locales, so the display name comes from
        the user's chosen filename and the icon from the on-disk game executable
        (``_resolve_local_game_icon`` already does that lookup safely). Dropping the
        RPC also avoids firing a launch request outside an actual user-driven launch.

        The third tuple element (formerly ``is_administrator`` from the API) is kept
        only for the caller's unpacking shape; the caller discards it and elevation
        is decided from the live response at launch time, not from the shortcut.
        """
        icon = self._resolve_local_game_icon()
        return (self.filename.get(), icon, False)


class ShortcutCreate(ShortcutBase):
    def create(self):
        if not self.winfo_children():
            CTkLabel(self, text=i18n.t("app.shortcut.add_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
        super().create()

        PaddingComponent(self, height=15).create()
        text = i18n.t("app.shortcut.unity_command_line_args")
        ButtonComponent(self, text=text, tooltip=i18n.t("app.shortcut.unity_command_line_args_tooltip"), command=self.unity_command_line_args_callback).create()

        return self

    def save_handler(self, fn: Callable[[], None]):
        self.save()
        fn()
        # Auto-refresh after save: re-scan account dir (picks up newly imported
        # accounts), clear the filename input, rebuild the form. Equivalent to
        # an F5 reload — saved-success toast still shows because it was queued
        # before this fires.
        self.after(120, self._refresh_after_save)

    def _refresh_after_save(self) -> None:
        try:
            self.account_name_list = [(x.stem, x.stem) for x in DataPathConfig.ACCOUNT.iterdir() if x.suffix == ".bytes"]
            self.account_name_list.insert(0, (Constant.ALWAYS_EXTRACT_FROM_DMM, i18n.t("app.shortcut.always_extract_from_dmm")))
            self.filename.set("")
            children_destroy(self)
            self.create()
        except Exception:
            logger.exception("Post-save form refresh failed (non-fatal)")


class ShortcutEdit(ShortcutBase):
    selected: StringVar
    values: list[str]

    def __init__(self, master: Frame):
        super().__init__(master)
        self.values = [x.stem for x in DataPathConfig.SHORTCUT.iterdir() if x.suffix == ".json"]
        self.selected = StringVar()

    def create(self):
        CTkLabel(self, text=i18n.t("app.shortcut.edit_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)

        LabelComponent(self, text=i18n.t("app.shortcut.file_select")).create()
        CTkOptionMenu(self, values=self.values, variable=self.selected, command=self.option_callback).pack(fill=ctk.X)

        if self.selected.get() in self.values:
            self.data = self.read()
            self.data.product_id.set("priconner")
            super().create()
            self.filename.set(self.selected.get())
            CTkButton(self, text=i18n.t("app.shortcut.delete"), command=self.delete_callback).pack(fill=ctk.X, pady=5)

        PaddingComponent(self, height=15).create()
        text = i18n.t("app.shortcut.unity_command_line_args")
        ButtonComponent(self, text=text, tooltip=i18n.t("app.shortcut.unity_command_line_args_tooltip"), command=self.unity_command_line_args_callback).create()

        return self

    def save_handler(self, fn: Callable[[], None]):
        selected = DataPathConfig.SHORTCUT.joinpath(self.selected.get())
        logger.info("ShortcutEdit.save_handler: editing %s", self.selected.get())
        selected.with_suffix(".json").rename(selected.with_suffix(".json.bak"))
        try:
            self.save()
            try:
                fn()
            except Exception as e:
                logger.exception("ShortcutEdit inner fn failed; cleaning new file")
                try:
                    DataPathConfig.SHORTCUT.joinpath(self.filename.get()).with_suffix(".json").unlink()
                except Exception as inner_exc:
                    logger.warning("Cleanup of new json failed: %s", inner_exc)
                raise e
        except Exception:
            logger.exception("ShortcutEdit save_handler failed; restoring backup")
            selected.with_suffix(".json.bak").rename(selected.with_suffix(".json"))
            raise
        selected.with_suffix(".json.bak").unlink()
        self.values.remove(self.selected.get())
        self.values.append(self.filename.get())
        self.selected.set(self.filename.get())
        self.option_callback("_")

    @error_toast
    def delete_callback(self):
        path = DataPathConfig.SHORTCUT.joinpath(self.selected.get()).with_suffix(".json")
        path.unlink()
        self.values.remove(self.selected.get())
        self.selected.set("")
        self.option_callback("_")
        self.toast.info(i18n.t("app.shortcut.save_success"))

    @error_toast
    def option_callback(self, _: str):
        children_destroy(self)
        self.create()

    def read(self) -> ShortcutData:
        path = DataPathConfig.SHORTCUT.joinpath(self.selected.get()).with_suffix(".json")
        return ShortcutData.from_path(path)
