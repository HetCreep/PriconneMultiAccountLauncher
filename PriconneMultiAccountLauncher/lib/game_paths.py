r"""Resolve game manifest + registry paths via auto-detect.

Scans `LocalLow\Cygames\*` and `HKCU\Software\Cygames\*` for a child whose
contents look like Priconne (has manifest.db / has any value). Falls back to
the hardcoded `PrincessConnectReDive` default when detection fails.

Override fields were removed (per user request 2026-05-27); auto-detect covers
~99% of installs. If a future Cygames product rename happens, edit
DEFAULT_PRODUCT_NAME below or hand-patch `data/config.json`.
"""

import logging
import winreg
from pathlib import Path
from typing import Optional

from static.env import Env

logger = logging.getLogger(__name__)

CYGAMES_LOCALLOW = Env.HOMEPATH.joinpath("AppData", "LocalLow", "Cygames")
CYGAMES_REGISTRY_BASE = r"Software\Cygames"

DEFAULT_PRODUCT_NAME = "PrincessConnectReDive"


def _detect_manifest_path() -> Optional[Path]:
    if not CYGAMES_LOCALLOW.exists():
        return None
    try:
        candidates = [d for d in CYGAMES_LOCALLOW.iterdir() if d.is_dir() and d.joinpath("manifest.db").exists()]
    except OSError as exc:
        logger.warning("Failed to scan %s: %s", CYGAMES_LOCALLOW, exc)
        return None

    if len(candidates) == 1:
        return candidates[0].joinpath("manifest.db")
    if len(candidates) > 1:
        for c in candidates:
            if c.name == DEFAULT_PRODUCT_NAME:
                return c.joinpath("manifest.db")
        logger.warning("Multiple Cygames products under %s; none match default: %s",
                       CYGAMES_LOCALLOW, [c.name for c in candidates])
    return None


def _detect_registry_subkey() -> Optional[str]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CYGAMES_REGISTRY_BASE, 0, winreg.KEY_READ) as key:
            names: list[str] = []
            i = 0
            while True:
                try:
                    names.append(winreg.EnumKey(key, i))
                except OSError:
                    break
                i += 1
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.warning("Failed to enumerate %s: %s", CYGAMES_REGISTRY_BASE, exc)
        return None

    candidates = [n for n in names if _subkey_has_values(CYGAMES_REGISTRY_BASE + "\\" + n)]
    if len(candidates) == 1:
        return CYGAMES_REGISTRY_BASE + "\\" + candidates[0]
    if len(candidates) > 1:
        for c in candidates:
            if c == DEFAULT_PRODUCT_NAME:
                return CYGAMES_REGISTRY_BASE + "\\" + c
        logger.warning("Multiple Cygames registry subkeys: %s", candidates)
    return None


def _subkey_has_values(subkey: str) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_READ) as key:
            try:
                winreg.EnumValue(key, 0)
                return True
            except OSError:
                return False
    except OSError:
        return False


def get_manifest_path() -> Path:
    """Resolve manifest.db path. Detected > default."""
    detected = _detect_manifest_path()
    if detected is not None:
        return detected
    return CYGAMES_LOCALLOW.joinpath(DEFAULT_PRODUCT_NAME, "manifest.db")


def get_registry_subkey() -> str:
    """Resolve registry subkey. Detected > default."""
    detected = _detect_registry_subkey()
    if detected is not None:
        return detected
    return CYGAMES_REGISTRY_BASE + "\\" + DEFAULT_PRODUCT_NAME


def verify_game_data_present() -> bool:
    """True if either manifest or registry subkey exists."""
    if get_manifest_path().exists():
        return True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, get_registry_subkey(), 0, winreg.KEY_READ):
            return True
    except OSError:
        return False
