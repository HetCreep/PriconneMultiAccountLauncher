import logging
import os
from pathlib import Path
from typing import Optional

import requests
from static.config import UrlConfig
from static.dump import Dump
from windows_pathlib import WindowsPathlib

logger = logging.getLogger(__name__)


def _fetch_release_version(default: str) -> str:
    try:
        res = requests.get(UrlConfig.RELEASE_API, timeout=(3.0, 5.0))
        res.raise_for_status()
        return res.json().get("tag_name", default)
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Release API check skipped: %s", exc)
        return default


class _EnvMeta(type):
    _release_version_cache: Optional[str] = None

    @property
    def RELEASE_VERSION(cls) -> str:
        if cls._release_version_cache is None:
            cls._release_version_cache = _fetch_release_version(cls.VERSION)
        return cls._release_version_cache


class Env(Dump, metaclass=_EnvMeta):
    VERSION = "v6.3.40"

    DEVELOP: bool = os.environ.get("ENV") == "DEVELOP"
    APPDATA: Path = Path(os.getenv("APPDATA", default=""))
    HOMEPATH: Path = Path(os.getenv("USERPROFILE", default=""))
    PROGURAM_FILES: Path = Path(os.getenv("PROGRAMFILES", default=""))
    DESKTOP: Path = WindowsPathlib.desktop()

    DEFAULT_DMM_GAME_PLAYER_PROGURAM_FOLDER: Path = PROGURAM_FILES.joinpath("DMMGamePlayer")
    DEFAULT_DMM_GAME_PLAYER_DATA_FOLDER: Path = APPDATA.joinpath("dmmgameplayer5")

    DMM_GAME_PLAYER_HIDDEN_FOLDER: Path = HOMEPATH.joinpath(".DMMGamePlayer")

    SYSTEM_ROOT = Path(os.getenv("SYSTEMROOT", default=""))
    SYSTEM32 = SYSTEM_ROOT.joinpath("System32")
    SCHTASKS = SYSTEM32.joinpath("schtasks.exe")
