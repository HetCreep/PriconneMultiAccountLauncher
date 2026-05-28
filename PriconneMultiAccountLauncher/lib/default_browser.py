"""Detect Windows default browser via registry UserChoice.

Reads `HKCU\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\https\\UserChoice`
ProgId and maps to one of {"Chrome", "Edge", "Firefox"}. Falls back to "Chrome".
"""

import logging
import winreg
from typing import Literal

logger = logging.getLogger(__name__)

BrowserName = Literal["Chrome", "Edge", "Firefox"]

_USER_CHOICE_KEY = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"

_PROGID_MAP: dict[str, BrowserName] = {
    "ChromeHTML": "Chrome",
    "MSEdgeHTML": "Edge",
    "MSEdgeBHTML": "Edge",
    "AppXq0fevzme2pys62n3e0fbqa7peapykr8v": "Edge",
    "FirefoxURL": "Firefox",
}


def detect_default_browser() -> BrowserName:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _USER_CHOICE_KEY, 0, winreg.KEY_READ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
    except OSError as exc:
        logger.warning("UserChoice ProgId unreadable, defaulting to Edge (always-present on Win10+): %s", exc)
        return "Edge"

    if not isinstance(prog_id, str):
        return "Edge"

    if prog_id in _PROGID_MAP:
        return _PROGID_MAP[prog_id]

    lower = prog_id.lower()
    if "firefox" in lower:
        return "Firefox"
    if "edge" in lower:
        return "Edge"
    if "chrome" in lower:
        return "Chrome"

    logger.info("Unknown default browser ProgId '%s'; defaulting to Edge", prog_id)
    return "Edge"
