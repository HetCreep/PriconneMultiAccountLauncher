import functools
import locale
import logging
import time
import urllib.parse
from pathlib import Path
from tkinter import Misc
from typing import Optional, Tuple, TypeVar

import i18n
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from static.config import AssetsPathConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


def isinstance_filter(obj, cls: type[T]) -> list[T]:
    return list(filter(lambda x: isinstance(x, cls), obj))


def get_isinstance(obj, cls: type[T]) -> Optional[T]:
    ins = isinstance_filter(obj, cls)
    if len(ins) > 0:
        return ins[0]
    return None


def children_destroy(master: Misc):
    for child in master.winfo_children():
        child.destroy()


def file_create(path: Path, name: str):
    if path.exists():
        raise FileExistsError(i18n.t("app.utils.file_exists", name=name))
    else:
        path.touch()


@functools.lru_cache(maxsize=1)
def _supported_lang_codes() -> tuple[str, ...]:
    """Filesystem-derived list of locale codes. Cached for app lifetime."""
    return tuple(sorted({x.suffixes[0][1:] for x in AssetsPathConfig.I18N.iterdir()}))


def get_supported_lang() -> list[tuple[str, str]]:
    # i18n.t is locale-dependent; cannot @lru_cache the full list.
    return [(code, i18n.t("app.language", locale=code)) for code in _supported_lang_codes()]


@functools.lru_cache(maxsize=1)
def get_default_locale() -> Tuple[str, str]:
    lang, encoding = locale.getdefaultlocale()
    if lang not in _supported_lang_codes():
        lang = "en"
    if encoding is None:
        encoding = "utf-8"
    return lang, encoding


def get_driver(path: Optional[Path]) -> webdriver.Chrome | webdriver.Edge | webdriver.Firefox:
    """Launch the user's default Windows browser as a selenium webdriver."""
    from lib.default_browser import detect_default_browser

    browser = detect_default_browser()
    logger.info("Launching webdriver: browser=%s profile=%s", browser, path)
    absolute_path = path.absolute() if path is not None else None
    try:
        if browser == "Chrome":
            options = ChromeOptions()
            if absolute_path is not None:
                options.add_argument(f"--user-data-dir={absolute_path}")
            return webdriver.Chrome(options=options)
        if browser == "Edge":
            options = EdgeOptions()
            if absolute_path is not None:
                options.add_argument(f"--user-data-dir={absolute_path}")
            return webdriver.Edge(options=options)
        if browser == "Firefox":
            options = FirefoxOptions()
            if absolute_path is not None:
                options.add_argument("-profile")
                options.add_argument(str(absolute_path))
            return webdriver.Firefox(options=options)
    except Exception:
        logger.exception("Failed to start webdriver for %s", browser)
        raise
    logger.error("Unknown browser identifier: %s", browser)
    raise Exception(i18n.t("app.account.browser_not_selected"))


LOGIN_DRIVER_TIMEOUT_SEC = 300.0


def login_driver(url: str, driver: webdriver.Chrome | webdriver.Edge | webdriver.Firefox):
    from selenium.common.exceptions import WebDriverException

    logger.info("Navigating webdriver to login URL")
    driver.get(url)
    deadline = time.monotonic() + LOGIN_DRIVER_TIMEOUT_SEC
    while True:
        try:
            current = driver.current_url
        except WebDriverException as exc:
            logger.warning("Webdriver detached during login: %s", exc)
            raise TimeoutError(i18n.t("app.account.browser_not_selected")) from exc

        parsed_url = urllib.parse.urlparse(current)
        if parsed_url.netloc == "webdgp-gameplayer.games.dmm.com" and parsed_url.path == "/login/success":
            logger.info("Webdriver login success URL reached")
            code = urllib.parse.parse_qs(parsed_url.query)["code"][0]
            # Halt page JS BEFORE it can navigate to dmmgameplayer://. Without
            # this, Edge shows the "open DMMGamePlayer?" external-app prompt
            # mid-import — naive users click Open, DMM client launches, and
            # they think the import failed. We already have the OAuth code
            # from the URL; the success page itself is throwaway.
            try:
                driver.execute_script("window.stop(); window.location.replace('about:blank');")
            except WebDriverException as exc:
                logger.debug("Could not suppress success-page protocol nav: %s", exc)
            return code

        if time.monotonic() > deadline:
            logger.warning("Webdriver login timeout after %.0fs", LOGIN_DRIVER_TIMEOUT_SEC)
            raise TimeoutError(f"Browser login did not complete within {LOGIN_DRIVER_TIMEOUT_SEC:.0f}s")

        time.sleep(0.2)
