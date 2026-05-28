from lib.app_paths import ASSETS_DIR, DATA_DIR
from static.dump import Dump


class DataPathConfig(Dump):
    DATA = DATA_DIR
    ACCOUNT = DATA.joinpath("account")
    ACCOUNT_SHORTCUT = DATA.joinpath("account_shortcut")
    SHORTCUT = DATA.joinpath("shortcut")
    BROWSER_PROFILE = DATA.joinpath("browser_profile")
    BROWSER_CONFIG = DATA.joinpath("browser_config")
    LOG = DATA.joinpath("log")
    APP_CONFIG = DATA.joinpath("config.json")
    SCHTASKS = DATA.joinpath("schtasks")
    DEVICE = DATA.joinpath("device.json")


class AssetsPathConfig(Dump):
    PATH = ASSETS_DIR
    I18N = PATH.joinpath("i18n")
    ICONS = PATH.joinpath("icons")
    LICENSE = PATH.joinpath("license").joinpath("LICENSE")
    TEMPLATE = PATH.joinpath("template")
    THEMES = PATH.joinpath("themes")

    ICON_MAIN = ICONS.joinpath("PriconneMultiAccountLauncher.ico")

    SCHTASKS = TEMPLATE.joinpath("schtasks.xml")
    SHORTCUT = TEMPLATE.joinpath("shortcut.ps1")


class UrlConfig(Dump):
    CONTRIBUTION = "https://github.com/HetCreep/PriconneMultiAccountLauncher"
    RELEASE_API = "https://api.github.com/repos/HetCreep/PriconneMultiAccountLauncher/releases/latest"
    RELEASE = "https://github.com/HetCreep/PriconneMultiAccountLauncher/releases/latest"
    DONATE = "https://github.com/HetCreep/PriconneMultiAccountLauncher"
    ISSUE = "https://github.com/HetCreep/PriconneMultiAccountLauncher/issues/new/choose"


class SchtasksConfig(Dump):
    FILE = "schtasks_v1_{0}_{1}"
    NAME = "\\Microsoft\\Windows\\PriconneMultiAccountLauncher\\{0}"
