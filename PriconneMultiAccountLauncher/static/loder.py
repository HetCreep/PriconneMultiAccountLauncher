import json
import logging
from pathlib import Path

from lib.version import Version
from models.setting_data import AppConfig, DeviceData, SettingData
from static.config import AssetsPathConfig, DataPathConfig
from static.env import Env
from utils.utils import get_supported_lang

logger = logging.getLogger(__name__)


def config_loder():
    DataPathConfig.DATA.mkdir(parents=True, exist_ok=True)
    if not AssetsPathConfig.PATH.exists():
        raise FileNotFoundError(f"{AssetsPathConfig.PATH} not found")

    if DataPathConfig.APP_CONFIG.exists():
        try:
            with open(DataPathConfig.APP_CONFIG, "r", encoding="utf-8") as f:
                AppConfig.DATA = SettingData.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Config file corrupt (%s) — re-creating defaults", exc)
            AppConfig.DATA = SettingData()
            with open(DataPathConfig.APP_CONFIG, "w+", encoding="utf-8") as f:
                json.dump(AppConfig.DATA.to_dict(), f)
    else:
        AppConfig.DATA = SettingData()
        with open(DataPathConfig.APP_CONFIG, "w+", encoding="utf-8") as f:
            json.dump(AppConfig.DATA.to_dict(), f)

    if DataPathConfig.DEVICE.exists():
        try:
            with open(DataPathConfig.DEVICE, "r", encoding="utf-8") as f:
                AppConfig.DEVICE = DeviceData.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Device file corrupt (%s) — re-creating defaults", exc)
            AppConfig.DEVICE = DeviceData()
            with open(DataPathConfig.DEVICE, "w+", encoding="utf-8") as f:
                json.dump(AppConfig.DEVICE.to_dict(), f)
    else:
        AppConfig.DEVICE = DeviceData()
        with open(DataPathConfig.DEVICE, "w+", encoding="utf-8") as f:
            json.dump(AppConfig.DEVICE.to_dict(), f)

    AppConfig.DATA.update()
    AppConfig.DEVICE.update()


def config_migrate():
    last = AppConfig.DATA.last_version.get()
    try:
        version = Version(last)
    except ValueError:
        logger.warning("last_version %r is not parseable — treating as fresh install", last)
        version = Version("v0.0.0")

    if version == Version(Env.VERSION):
        return

    logger.info("Migration from %s to %s", version, Env.VERSION)

    if version < Version("v5.5.2"):
        logger.info("Migration step <v5.5.2: drop legacy i18n files, normalize lang")
        Path(AssetsPathConfig.I18N).joinpath("app.ja.yml").unlink(missing_ok=True)
        Path(AssetsPathConfig.I18N).joinpath("app.en.yml").unlink(missing_ok=True)

        if AppConfig.DATA.lang.get() not in [x[0] for x in get_supported_lang()]:
            AppConfig.DATA.lang.set("en_US")

    if version < Version("v6.3.35"):
        # theme_font collapsed from 3 modes (i18n/os/theme) to 2 (auto/system).
        legacy = AppConfig.DATA.theme_font.get()
        if legacy in ("i18n", "theme"):
            AppConfig.DATA.theme_font.set("auto")
            logger.info("theme_font migrated '%s' -> 'auto'", legacy)
        elif legacy == "os":
            AppConfig.DATA.theme_font.set("system")
            logger.info("theme_font migrated 'os' -> 'system'")

        # Theme set trimmed: kept blue, dark-blue, purple, magenta.
        # Dropped green, red, torquoise -> migrate to closest match.
        theme = AppConfig.DATA.theme.get()
        theme_map = {"green": "blue", "red": "magenta", "torquoise": "blue"}
        if theme in theme_map:
            new_theme = theme_map[theme]
            AppConfig.DATA.theme.set(new_theme)
            logger.info("theme migrated '%s' -> '%s' (dropped in v6.3.35)", theme, new_theme)

    AppConfig.DATA.last_version.set(Env.VERSION)
    try:
        with open(DataPathConfig.APP_CONFIG, "w+", encoding="utf-8") as f:
            json.dump(AppConfig.DATA.to_dict(), f)
    except OSError as exc:
        logger.error("Failed to persist migrated config: %s", exc)
