"""Update-check with 24h disk cache.

Per [domain/telemetry-policy.md] and [domain/release-verification.md]:
- Connects only to api.github.com
- User can disable in Settings (AppConfig.DATA.disable_update_check)
- Cached on disk to avoid spamming the API on every app launch
- Notify-only; never auto-downloads
"""

import json
import logging
import time
from typing import Optional

import requests
from static.config import DataPathConfig, UrlConfig

logger = logging.getLogger(__name__)

# 7 days: this is a stable desktop tool, not a browser — releases are
# infrequent (mostly bug fixes when a user reports one), so a weekly
# notify-only check is plenty and keeps GitHub API traffic minimal.
CACHE_TTL_SEC = 7 * 24 * 60 * 60


def _cache_path():
    return DataPathConfig.DATA.joinpath("update_check_cache.json")


def _read_cache() -> Optional[dict]:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Update cache unreadable: %s", exc)
        return None


def _write_cache(tag_name: str) -> None:
    """Atomic cache write — tmp + os.replace so a partial JSON never poisons the cache."""
    import os as _os
    path = _cache_path()
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"tag_name": tag_name, "ts": int(time.time())}, f)
            f.flush()
            _os.fsync(f.fileno())
        _os.replace(tmp, path)
    except OSError as exc:
        logger.warning("Failed to write update cache: %s", exc)
        try:
            tmp.unlink()
        except OSError:
            pass


def get_latest_version(current_version: str, *, disabled: bool = False) -> str:
    """Return the latest release tag, or current_version if check disabled / fails / cached."""
    if disabled:
        return current_version

    cached = _read_cache()
    if cached and (time.time() - cached.get("ts", 0)) < CACHE_TTL_SEC:
        return cached.get("tag_name", current_version)

    try:
        res = requests.get(UrlConfig.RELEASE_API, timeout=(3.0, 5.0))
        res.raise_for_status()
        tag = res.json().get("tag_name", current_version)
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Release API check failed: %s", exc)
        return current_version

    _write_cache(tag)
    return tag
