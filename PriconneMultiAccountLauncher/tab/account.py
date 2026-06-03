import logging
from pathlib import Path
from tkinter import BooleanVar, StringVar
from typing import Callable, Optional, TypeVar

import customtkinter as ctk
import i18n

logger = logging.getLogger(__name__)
from component.component import CheckBoxComponent, EntryComponent, OptionMenuComponent, OptionMenuTupleComponent, PaddingComponent
from component.tab_menu import TabMenuComponent
from customtkinter import CTkBaseClass, CTkButton, CTkFrame, CTkLabel
from component.auto_scroll_frame import CTkAutoScrollFrame
from lib.DGPSessionV2 import DgpSessionV2
from lib.toast import ToastController, error_toast
from models.shortcut_data import BrowserConfigData
from static.config import DataPathConfig
from static.constant import Constant
from utils.utils import children_destroy, file_create, get_driver, login_driver

T = TypeVar("T")


# ===== Account Sub Menu =====


class AccountTab(CTkFrame):
    tab: TabMenuComponent

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.tab = TabMenuComponent(self)

    def create(self):
        self.tab.create()
        self.tab.add(text=i18n.t("app.tab.account_import"), callback=self.import_callback)
        self.tab.add(text=i18n.t("app.tab.import_browser"), callback=self.import_browser_callback)
        self.tab.add(text=i18n.t("app.tab.account_edit"), callback=self.edit_callback)
        self.tab.add(text=i18n.t("app.tab.device"), callback=self.device_callback)
        self.tab.add(text=i18n.t("app.tab.device_list"), callback=self.device_list_callback)
        return self

    def import_callback(self, master: CTkBaseClass):
        AccountImport(master).create().pack(expand=True, fill=ctk.BOTH)

    def import_browser_callback(self, master: CTkBaseClass):
        AccountBrowserImport(master).create().pack(expand=True, fill=ctk.BOTH)

    def edit_callback(self, master: CTkBaseClass):
        AccountEdit(master).create().pack(expand=True, fill=ctk.BOTH)

    def device_callback(self, master: CTkBaseClass):
        SettingDeviceTab(master).create().pack(expand=True, fill=ctk.BOTH)

    def device_list_callback(self, master: CTkBaseClass):
        DeviceListTab(master).create().pack(expand=True, fill=ctk.BOTH)


# ===== Account Body =====


class AccountImport(CTkAutoScrollFrame):
    """Import flow that reads the already-logged-in DMM Game Player token.

    Use case: user is already signed in via the official DMM Game Player UI.
    This snapshots that session into a per-account .bytes blob so the launcher
    can swap it back later without re-logging through DMM.

    Pair with AccountBrowserImport (browser-driven OAuth) for accounts where
    the user is NOT currently signed in to the DMM client.
    """

    toast: ToastController
    name: StringVar

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.name = StringVar()

    def create(self):
        CTkLabel(self, text=i18n.t("app.account.import_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
        text = i18n.t("app.account.filename")
        tooltip = i18n.t("app.account.filename_tooltip")
        EntryComponent(self, text=text, tooltip=tooltip, required=True, variable=self.name, alnum_only=True).create()
        CTkButton(self, text=i18n.t("app.account.import"), command=self.callback).pack(fill=ctk.X, pady=10)
        return self

    @error_toast
    def callback(self):
        logger.info("AccountImport.callback start: name=%s", self.name.get())
        path = DataPathConfig.ACCOUNT.joinpath(self.name.get()).with_suffix(".bytes")
        if self.name.get() == "":
            raise Exception(i18n.t("app.account.filename_not_entered"))
        if path.exists():
            raise Exception(i18n.t("app.account.filename_already_exists"))
        if self.name.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            raise Exception(i18n.t("app.account.filename_reserved"))

        session = DgpSessionV2.read_dgp()
        if session.get_access_token() is None:
            logger.warning("AccountImport: DMM Game Player has no active session; import aborted")
            raise Exception(i18n.t("app.account.import_error"))
        session.write_bytes(str(path))
        logger.info("AccountImport.callback success: name=%s", self.name.get())
        self.toast.info(i18n.t("app.account.import_success"))
        # Refresh form so user can import another account without manually
        # clearing the filename. Delay lets the success toast render first.
        self.after(120, self._refresh_after_save)

    def _refresh_after_save(self) -> None:
        try:
            self.name.set("")
            children_destroy(self)
            self.create()
        except Exception:
            logger.exception("AccountImport post-save refresh failed (non-fatal)")


class AccountBrowserImport(CTkAutoScrollFrame):
    toast: ToastController
    name: StringVar
    data: BrowserConfigData

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.name = StringVar()
        self.auto_refresh = BooleanVar(value=True)
        self.data = BrowserConfigData()

    def create(self):
        CTkLabel(self, text=i18n.t("app.account.import_browser_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
        text = i18n.t("app.account.filename")
        tooltip = i18n.t("app.account.filename_tooltip")
        EntryComponent(self, text=text, tooltip=tooltip, required=True, variable=self.name, alnum_only=True).create()
        CheckBoxComponent(self, text=i18n.t("app.account.auto_refresh"), variable=self.auto_refresh).create()
        CTkButton(self, text=i18n.t("app.account.import_browser"), command=self.callback).pack(fill=ctk.X, pady=10)
        return self

    @error_toast
    def callback(self):
        logger.info("AccountBrowserImport.callback start: name=%s", self.name.get())
        path = DataPathConfig.ACCOUNT.joinpath(self.name.get()).with_suffix(".bytes")
        if self.name.get() == "":
            raise Exception(i18n.t("app.account.filename_not_entered"))
        if path.exists():
            raise Exception(i18n.t("app.account.filename_already_exists"))
        if self.name.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            raise Exception(i18n.t("app.account.filename_reserved"))

        session = DgpSessionV2()
        res = session.post_dgp(DgpSessionV2.LOGIN_URL, json={"prompt": ""}).json()
        if res["result_code"] != 100:
            logger.warning("LOGIN_URL request failed result_code=%s", res.get("result_code"))
            raise Exception(res["error"])

        profile_path = DataPathConfig.BROWSER_PROFILE.joinpath(self.data.profile_name.get()).absolute()
        driver = get_driver(profile_path)
        code = login_driver(res["data"]["url"], driver)
        driver.quit()
        res = session.post_dgp(DgpSessionV2.ACCESS_TOKEN, json={"code": code}).json()
        if res["result_code"] != 100:
            logger.warning("ACCESS_TOKEN request failed result_code=%s", res.get("result_code"))
            raise Exception(res["error"])
        session.actauth = {"accessToken": res["data"]["access_token"]}
        session.write_bytes(str(path))
        if self.auto_refresh.get():
            config_path = DataPathConfig.BROWSER_CONFIG.joinpath(self.name.get()).with_suffix(".json")
            file_create(config_path, name=i18n.t("app.account.filename"))
            self.data.write_path(config_path)
        logger.info("AccountBrowserImport success: name=%s", self.name.get())
        self.toast.info(i18n.t("app.account.import_browser_success"))
        self.after(120, self._refresh_after_save)

    def _refresh_after_save(self) -> None:
        try:
            self.name.set("")
            # Fresh BrowserConfigData = new uuid profile_name for the next import,
            # so the next account's cookies don't share the just-used profile dir.
            self.data = BrowserConfigData()
            children_destroy(self)
            self.create()
        except Exception:
            logger.exception("AccountBrowserImport post-save refresh failed (non-fatal)")


class AccountEdit(CTkAutoScrollFrame):
    toast: ToastController
    values: list[str]
    filename: StringVar
    body: CTkFrame
    body_var: dict[str, StringVar]
    browser_config: Optional[BrowserConfigData]
    body_filename: StringVar

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.values = [x.stem for x in DataPathConfig.ACCOUNT.iterdir() if x.suffix == ".bytes"]
        self.filename = StringVar()
        self.body_var = {}
        self.browser_config = None
        self.body_filename = StringVar()

    def create(self):
        CTkLabel(self, text=i18n.t("app.account.edit_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
        OptionMenuComponent(self, text=i18n.t("app.account.file_select"), values=self.values, variable=self.filename, command=self.select_callback).create()
        self._parent_canvas.yview_moveto(0)
        self.body = CTkFrame(self, fg_color="transparent", height=0)
        self.body.pack(expand=True, fill=ctk.BOTH)
        return self

    @error_toast
    def select_callback(self, value: str):
        children_destroy(self.body)
        path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
        self.body_filename.set(self.filename.get())
        text = i18n.t("app.account.filename")
        tooltip = i18n.t("app.account.filename_tooltip")
        EntryComponent(self.body, text=text, tooltip=tooltip, required=True, variable=self.body_filename, alnum_only=True).create()

        session = DgpSessionV2.read_cookies(Path(path))
        for key in session.actauth.keys():
            self.body_var[key] = StringVar(value=session.actauth[key] or "")
            EntryComponent(self.body, text=key, variable=self.body_var[key]).create()
        config_path = DataPathConfig.BROWSER_CONFIG.joinpath(self.filename.get()).with_suffix(".json")
        if config_path.exists():
            self.browser_config = BrowserConfigData.from_path(config_path)
            PaddingComponent(self.body, height=20).create()
            EntryComponent(self.body, text="profile_name", variable=self.browser_config.profile_name).create()

        CTkButton(self.body, text=i18n.t("app.account.save"), command=self.save_callback).pack(fill=ctk.X, pady=10)
        CTkButton(self.body, text=i18n.t("app.account.delete"), command=self.delete_callback).pack(fill=ctk.X)

    @error_toast
    def save_callback(self):
        if self.body_filename.get() == "":
            raise Exception(i18n.t("app.account.filename_not_entered"))
        if self.body_filename.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            raise Exception(i18n.t("app.account.filename_reserved"))

        path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
        body_path = DataPathConfig.ACCOUNT.joinpath(self.body_filename.get()).with_suffix(".bytes")
        config_path = DataPathConfig.BROWSER_CONFIG.joinpath(self.filename.get()).with_suffix(".json")
        config_body_path = DataPathConfig.BROWSER_CONFIG.joinpath(self.body_filename.get()).with_suffix(".json")

        def check_file(callback: Callable[[], None]):
            if self.browser_config:
                callback()

        def write():
            session = DgpSessionV2.read_cookies((Path(path)))
            for key in session.actauth.keys():
                session.actauth[key] = self.body_var[key].get()
            session.write_bytes(str(body_path))
            if self.browser_config:
                self.browser_config.write_path(config_body_path)

        if path == body_path:
            write()
        else:
            try:
                file_create(body_path, name=i18n.t("app.account.filename"))
                check_file(lambda: file_create(config_body_path, name=i18n.t("app.account.filename")))
                write()
            except Exception as e:
                logger.exception("AccountEdit.save_callback rename-write failed; cleaning new files")
                body_path.unlink(missing_ok=True)
                if self.browser_config:
                    config_body_path.unlink(missing_ok=True)
                raise e
            path.unlink()
            check_file(lambda: config_path.unlink())
            self.values.remove(self.filename.get())
            self.values.append(self.body_filename.get())
            self.filename.set(self.body_filename.get())
            children_destroy(self)
            self.create()
            self.select_callback("_")

        self.toast.info(i18n.t("app.account.save_success"))

    @error_toast
    def delete_callback(self):
        path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
        path.unlink()
        self.values.remove(self.filename.get())
        self.filename.set("")
        children_destroy(self)
        self.create()


class SettingDeviceTab(CTkAutoScrollFrame):
    toast: ToastController
    mode: bool
    hardware_name: StringVar
    auth_code: StringVar

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.mode = False
        self.hardware_name = StringVar(value="PriconneMultiAccountLauncher")
        self.auth_code = StringVar()
        self.account_name_list = [(x.stem, x.stem) for x in DataPathConfig.ACCOUNT.iterdir() if x.suffix == ".bytes"]
        self.account_name_list.insert(0, (Constant.ALWAYS_EXTRACT_FROM_DMM, i18n.t("app.shortcut.always_extract_from_dmm")))
        self.filename = StringVar()

    def create(self):
        if self.mode:
            CTkLabel(self, text=i18n.t("app.account.device_detail"), justify=ctk.LEFT).pack(anchor=ctk.W)
            EntryComponent(self, text=i18n.t("app.account.hardware_name"), variable=self.hardware_name, required=True).create()
            EntryComponent(self, text=i18n.t("app.account.auth_code"), tooltip=i18n.t("app.account.auth_code_tooltip"), variable=self.auth_code, required=True).create()
            CTkButton(self, text=i18n.t("app.account.auth"), command=self.auth_callback).pack(fill=ctk.X, pady=10)

        else:
            OptionMenuTupleComponent(self, text=i18n.t("app.account.file_select"), values=self.account_name_list, variable=self.filename).create()
            CTkButton(self, text=i18n.t("app.account.send_auth_code"), command=self.send_auth_code_callback).pack(fill=ctk.X, pady=10)

        return self

    @error_toast
    def send_auth_code_callback(self):
        if self.filename.get() == "":
            raise Exception(i18n.t("app.account.filename_not_entered"))

        if self.filename.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            session = DgpSessionV2.read_dgp()
        else:
            path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
            session = DgpSessionV2.read_cookies(path)
        logger.info("send_auth_code_callback: requesting HARDWARE_CODE for %s", self.filename.get())
        res = session.post_device_dgp(DgpSessionV2.HARDWARE_CODE).json()
        if res["result_code"] != 100:
            logger.warning("HARDWARE_CODE failed result_code=%s", res.get("result_code"))
            raise Exception(res["error"])

        self.mode = True
        children_destroy(self)
        self.create()
        self.toast.info(i18n.t("app.account.send_auth_code_success"))

    @error_toast
    def auth_callback(self):
        if self.filename.get() == "":
            raise Exception(i18n.t("app.account.filename_not_entered"))

        if self.filename.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            session = DgpSessionV2.read_dgp()
        else:
            path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
            session = DgpSessionV2.read_cookies(path)
        json = {
            "hardware_name": self.hardware_name.get(),
            "auth_code": self.auth_code.get(),
        }
        logger.info("auth_callback: registering hardware for %s", self.filename.get())
        res = session.post_device_dgp(DgpSessionV2.HARDWARE_CONF, json=json).json()
        if res["result_code"] != 100:
            logger.warning("HARDWARE_CONF failed result_code=%s", res.get("result_code"))
            raise Exception(res["error"])

        self.mode = False
        self.filename.set("")
        children_destroy(self)
        self.create()
        self.toast.info(i18n.t("app.account.auth_success"))


class DeviceListTab(CTkAutoScrollFrame):
    toast: ToastController

    def __init__(self, master: CTkBaseClass):
        super().__init__(master, fg_color="transparent")
        self.toast = ToastController(self)
        self.account_name_list = [(x.stem, x.stem) for x in DataPathConfig.ACCOUNT.iterdir() if x.suffix == ".bytes"]
        self.account_name_list.insert(0, (Constant.ALWAYS_EXTRACT_FROM_DMM, i18n.t("app.shortcut.always_extract_from_dmm")))
        self.filename = StringVar()
        self.data = None

    def create(self):
        OptionMenuTupleComponent(self, text=i18n.t("app.account.file_select"), values=self.account_name_list, variable=self.filename, command=self.select_callback).create()
        if self.data:
            count = len(self.data["hardwares"] or [])
            limit = self.data["device_auth_limit_num"]
            CTkLabel(self, text=i18n.t("app.account.device_registrations", count=count, limit=limit), justify=ctk.LEFT).pack(anchor=ctk.W)

            for hardware in self.data["hardwares"] or []:
                for key, value in hardware.items():
                    EntryComponent(self, text=key, variable=StringVar(value=value), state=ctk.DISABLED).create()

                def command(id=hardware["hardware_manage_id"]):
                    return self.delete_callback(id)

                CTkButton(self, text=i18n.t("app.account.delete"), command=command).pack(fill=ctk.X, pady=10)
                PaddingComponent(self, height=20).create()

        return self

    @error_toast
    def select_callback(self, value: str):
        if self.filename.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            session = DgpSessionV2.read_dgp()
        else:
            path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
            session = DgpSessionV2.read_cookies(path)
        logger.info("DeviceListTab.select_callback: HARDWARE_LIST for %s", self.filename.get())
        res = session.post_device_dgp(DgpSessionV2.HARDWARE_LIST, json={}).json()
        if res["result_code"] != 100:
            logger.warning("HARDWARE_LIST failed result_code=%s", res.get("result_code"))
            raise Exception(res["error"])
        self.data = res["data"]

        children_destroy(self)
        self.create()
        self.toast.info(i18n.t("app.account.device_list_success"))

    @error_toast
    def delete_callback(self, id: str):
        if self.filename.get() == Constant.ALWAYS_EXTRACT_FROM_DMM:
            session = DgpSessionV2.read_dgp()
        else:
            path = DataPathConfig.ACCOUNT.joinpath(self.filename.get()).with_suffix(".bytes")
            session = DgpSessionV2.read_cookies(path)
        json = {"hardware_manage_id": [id]}
        logger.info("DeviceListTab.delete_callback: HARDWARE_REJECT id=%s for %s", id, self.filename.get())
        res = session.post_device_dgp(DgpSessionV2.HARDWARE_REJECT, json=json).json()
        if res["result_code"] != 100:
            logger.warning("HARDWARE_REJECT failed result_code=%s", res.get("result_code"))
            raise Exception(res["error"])
        assert isinstance(self.data, dict)
        self.data["hardwares"] = [x for x in self.data["hardwares"] if x["hardware_manage_id"] != id]

        children_destroy(self)
        self.create()
        self.toast.info(i18n.t("app.account.delete_success"))
