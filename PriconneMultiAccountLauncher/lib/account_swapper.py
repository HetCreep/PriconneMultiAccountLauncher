"""Per-account state isolation: snapshot/restore the Cygames game registry
subtree between account switches.

Registry-only by design. The account binding lives entirely in the obfuscated
`HKCU\\Software\\Cygames\\PrincessConnectReDive` values. `manifest.db` and the
LocalLow asset caches (`a/ b/ m/ s/ v/`) are SHARED, account-agnostic game
assets — swapping them per account caused multi-GB re-downloads and black
textures, so they are never touched here.
"""

import json
import logging
import winreg
from pathlib import Path
from typing import Any, Optional

from lib.game_paths import get_registry_subkey, verify_game_data_present
from static.config import DataPathConfig

logger = logging.getLogger(__name__)

BACKUP_BASE_DIR: Path = DataPathConfig.DATA.joinpath("account_backups")
LAST_ACTIVE_FILE: Path = DataPathConfig.DATA.joinpath("last_active_account.json")

_ALWAYS_EXTRACT = "always_extract_from_dmm"

# Sentinel slot representing the user's pre-launcher game state — the DMM account
# they were already logged into via DMM Game Player before installing this fork.
# Snapshotted once on the first managed swap so post-game-exit can restore the
# machine to that state (per user's design: B/C are temporary slots layered over
# the persistent A baseline).
BASELINE_NAME = "_baseline_"

_REG_TYPE_MAP: dict[int, str] = {
    winreg.REG_SZ: "REG_SZ",
    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
    winreg.REG_DWORD: "REG_DWORD",
    winreg.REG_QWORD: "REG_QWORD",
    winreg.REG_BINARY: "REG_BINARY",
    winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
    winreg.REG_NONE: "REG_NONE",
}
_REG_TYPE_REV: dict[str, int] = {v: k for k, v in _REG_TYPE_MAP.items()}


def _encode_value(data: Any, vtype: int) -> Any:
    if vtype == winreg.REG_BINARY and isinstance(data, (bytes, bytearray)):
        return data.hex()
    if vtype == winreg.REG_MULTI_SZ:
        return list(data)
    return data


def _decode_value(data: Any, vtype: int) -> Any:
    if vtype == winreg.REG_BINARY and isinstance(data, str):
        return bytes.fromhex(data)
    if vtype == winreg.REG_MULTI_SZ:
        return list(data)
    return data


def _export_subtree(root: int, subkey: str) -> Optional[dict]:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
            return _walk_key(key)
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.error("Registry read failed for %s: %s", subkey, exc)
        return None


def _walk_key(key) -> dict:
    values: dict[str, dict[str, Any]] = {}
    i = 0
    while True:
        try:
            name, data, vtype = winreg.EnumValue(key, i)
        except OSError:
            break
        values[name] = {
            "type": _REG_TYPE_MAP.get(vtype, str(vtype)),
            "data": _encode_value(data, vtype),
        }
        i += 1

    subkeys: dict[str, dict] = {}
    i = 0
    while True:
        try:
            sub_name = winreg.EnumKey(key, i)
        except OSError:
            break
        with winreg.OpenKey(key, sub_name, 0, winreg.KEY_READ) as sub:
            subkeys[sub_name] = _walk_key(sub)
        i += 1

    return {"values": values, "subkeys": subkeys}


def _delete_subtree(root: int, subkey: str) -> None:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            i = 0
            children: list[str] = []
            while True:
                try:
                    children.append(winreg.EnumKey(key, i))
                except OSError:
                    break
                i += 1
        for child in children:
            _delete_subtree(root, f"{subkey}\\{child}")
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        return
    except OSError as exc:
        logger.warning("Registry delete failed for %s: %s", subkey, exc)


def _import_subtree(root: int, subkey: str, tree: dict) -> None:
    with winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
        for name, entry in tree.get("values", {}).items():
            vtype = _REG_TYPE_REV.get(entry["type"], winreg.REG_SZ)
            winreg.SetValueEx(key, name, 0, vtype, _decode_value(entry["data"], vtype))
    for sub_name, sub_tree in tree.get("subkeys", {}).items():
        _import_subtree(root, f"{subkey}\\{sub_name}", sub_tree)


def _is_real_account(account_name: str) -> bool:
    return bool(account_name) and account_name != _ALWAYS_EXTRACT


def _is_storable_slot(slot_name: str) -> bool:
    """True for any slot we can back up to disk — real accounts OR the baseline.

    Used in place of _is_real_account inside the low-level backup/restore
    functions so the baseline slot bypasses the ALWAYS_EXTRACT-exclusion that
    applies to user-facing account names.
    """
    return bool(slot_name) and slot_name != _ALWAYS_EXTRACT


def get_last_active_account() -> Optional[str]:
    if not LAST_ACTIVE_FILE.exists():
        return None
    try:
        with open(LAST_ACTIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("account_name")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read last active account file: %s", exc)
        return None


def set_last_active_account(account_name: str) -> None:
    LAST_ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(LAST_ACTIVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"account_name": account_name}, f, indent=4, ensure_ascii=False)
    except OSError as exc:
        logger.error("Failed to write last active account file: %s", exc)


def backup_account(account_name: str) -> None:
    """Snapshot an account's binding into its backup slot.

    Account identity lives ENTIRELY in the obfuscated Cygames registry subtree
    (`HKCU\\Software\\Cygames\\PrincessConnectReDive`). `manifest.db` and the
    `a/ b/ m/ s/ v/` caches under LocalLow are SHARED asset data (a single
    table of 79k asset hash→version rows, account-agnostic) — swapping them
    per account caused multi-GB re-downloads and black-texture renders.
    So this only snapshots the registry.
    """
    if not _is_real_account(account_name):
        return

    registry_subkey = get_registry_subkey()
    logger.info("Backing up session data (registry) for account: %s", account_name)
    backup_dir = BACKUP_BASE_DIR.joinpath(account_name)
    backup_dir.mkdir(parents=True, exist_ok=True)

    snapshot = _export_subtree(winreg.HKEY_CURRENT_USER, registry_subkey)
    if snapshot is None:
        logger.info("Registry subtree absent (%s); skipping registry backup for %s", registry_subkey, account_name)
        return

    try:
        with open(backup_dir.joinpath("registry.json"), "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        logger.info("Backed up registry for %s", account_name)
    except OSError as exc:
        logger.error("Failed to write registry backup: %s", exc)


def _clear_account_binding_for_fresh_start(account_name: str) -> None:
    """Wipe Cygames account-binding artifacts so the game treats the next
    launch as a fresh account login.

    Called when swapping IN an account that has no prior snapshot. Without
    this, the live registry state still belongs to whichever account was last
    on disk, and Cygames' server rejects the launch with
    "ข้อมูลเกมนี้เชื่อมโยงกับบัญชี PC อื่น..." (PC account already linked).

    Wiped:
      - `HKCU\\Software\\Cygames\\PrincessConnectReDive` subtree (account ID
        + device-binding values). The Cygames server's per-PC-account check
        is gated by values in this subkey — clearing it is sufficient to
        force a fresh-account login flow.

    Preserved (do NOT touch):
      - Everything under `LocalLow\\Cygames\\PrincessConnectReDive\\`.
        Earlier iterations swept "non-asset" top-level files here on the
        assumption that they held binding state. In practice they hold
        asset-index metadata, shader caches, and Unity runtime files that
        the `a/` hashed cache depends on — deleting them produced black
        textures and partial UI even when the registry binding was fine.
        The asset manifest + `a/` cache + every adjacent metadata file
        stays in place; Cygames re-syncs anything stale on next launch.
    """
    registry_subkey = get_registry_subkey()
    logger.info("Clearing Cygames account-binding state (registry only) for fresh start of '%s'", account_name)
    _delete_subtree(winreg.HKEY_CURRENT_USER, registry_subkey)


def restore_account(account_name: str) -> None:
    """Apply an account's saved registry binding to the live registry.

    Registry-only — see `backup_account` docstring. `manifest.db` and the
    LocalLow asset caches are shared and never touched here.
    """
    if not _is_real_account(account_name):
        return

    registry_subkey = get_registry_subkey()

    logger.info("Restoring session data (registry) for account: %s", account_name)
    backup_dir = BACKUP_BASE_DIR.joinpath(account_name)
    backup_reg = backup_dir.joinpath("registry.json")
    if not backup_reg.exists():
        # New account that has never been launched through the swap path:
        # leaving the current registry in place would make the game inherit
        # the previous account's binding (Cygames "1 game data per PC account"
        # error). Force a fresh-start clear so the game does a clean login.
        logger.info("No registry backup for %s — clearing live registry for fresh first launch", account_name)
        _clear_account_binding_for_fresh_start(account_name)
        return

    try:
        with open(backup_reg, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read registry backup: %s", exc)
        return

    _delete_subtree(winreg.HKEY_CURRENT_USER, registry_subkey)
    try:
        _import_subtree(winreg.HKEY_CURRENT_USER, registry_subkey, snapshot)
        logger.info("Restored registry for %s", account_name)
    except OSError as exc:
        logger.error("Failed to import registry: %s", exc)


def _baseline_exists() -> bool:
    """True only if the baseline slot has at least one real backup artifact.

    Earlier impl checked dir existence alone, which mis-treated a half-failed
    snapshot (dir created but `backup_account` bailed before writing manifest
    or registry — e.g. when the game's manifest.db had been deleted for a
    fresh re-download) as "baseline already captured". That left the slot
    empty forever, so post-game-exit restore couldn't return the machine to
    A's state. Now we require at least one of the two artifacts to be on
    disk; an empty dir triggers a fresh snapshot attempt on the next swap.
    """
    bdir = BACKUP_BASE_DIR.joinpath(BASELINE_NAME)
    if not bdir.exists():
        return False
    # Registry-only swap: the baseline is captured iff its registry snapshot
    # exists. (manifest.db is no longer copied per-slot.)
    return bdir.joinpath("registry.json").exists()


def snapshot_baseline_if_missing() -> None:
    """Capture the current on-disk game state as the baseline if not already saved.

    Called from `swap_account_data` on the FIRST managed swap. The baseline
    represents the user's primary DMM account state — whatever was already in
    `manifest.db` + the Cygames registry subkey before any per-account swap
    occurred. `restore_to_baseline` (post-game-exit) returns the machine to
    this state so the user's primary account remains usable outside the launcher.
    """
    if _baseline_exists():
        return
    if not verify_game_data_present():
        logger.info("Skip baseline snapshot — no game data on disk yet.")
        return
    logger.info("Snapshotting baseline game state before first account swap.")
    backup_account(BASELINE_NAME)


def _count_active_launch_processes() -> int:
    """Count PMAL processes currently running a SHORTCUT launch (have an id arg
    in cmdline), excluding self.

    The main GUI is excluded — it owns no live game-launch state, so leaving it
    running while we restore the baseline is harmless. Only another in-flight
    `--type game` / `--type launcher` process is the case where recovery must
    defer to avoid corrupting its session.
    """
    import os

    import psutil

    my_pid = os.getpid()
    target = "PriconneMultiAccountLauncher.exe".lower()
    count = 0
    for p in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            info = p.info
            pid = info.get("pid")
            name = (info.get("name") or "").lower()
            if pid is None or pid == my_pid:
                continue
            if name != target:
                continue
            cmdline = info.get("cmdline") or []
            # Shortcut launch always has at least one positional arg (the
            # shortcut filename) after the exe path. Main GUI has the exe
            # path only. `--type ...` extras are also fine — any non-exe arg
            # signals a launch process.
            non_exe_args = [a for a in cmdline[1:] if a and not a.lower().endswith(".exe")]
            if non_exe_args:
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return count


def restore_baseline_if_stale() -> None:
    """Crash-recovery probe. Call from main-GUI startup.

    Workflow:
      - `last_active_account.json` present at startup = previous launch did NOT
        run its post-game-exit `restore_to_baseline` (Task Manager kill, power
        loss, force-close, etc.). Baseline state on disk is whichever account
        was last swapped in, not the user's primary A account.
      - Restore baseline NOW so the user can run DMM client directly without
        hitting the "data linked to another PC account" Cygames error.

    Skipped if another PMAL process is currently running a shortcut launch —
    we'd otherwise corrupt that in-flight session's state.
    """
    if not get_last_active_account():
        return
    active_count = _count_active_launch_processes()
    if active_count > 0:
        logger.info(
            "Stale last_active marker found but %d other PMAL launch process(es) active — deferring recovery.",
            active_count,
        )
        return
    logger.warning("Stale last_active marker — previous launch did not clean up. Restoring baseline now.")
    restore_to_baseline()


def restore_to_baseline() -> None:
    """Post-game-exit handler. Saves current per-account state, then restores baseline.

    Workflow on game close:
      1. Identify the slot the game was just played as (last_active).
      2. Snapshot the current registry binding back into that slot — progress
         made during this session is preserved.
      3. Restore the baseline so any subsequent DMM-client direct launch sees
         the user's primary account, not the temporary B/C state.
      4. Clear last_active so the next launcher click starts from baseline again.

    Safe no-op if the baseline was never captured (e.g. game uninstalled).
    """
    if not verify_game_data_present():
        logger.info("Skip baseline restore — no game data on disk.")
        return

    last_active = get_last_active_account()
    if last_active and _is_real_account(last_active):
        logger.info("Game closed — capturing post-session state for '%s'", last_active)
        backup_account(last_active)

    if not _baseline_exists():
        logger.warning("Cannot restore baseline — no baseline snapshot exists. Leaving current state in place.")
        return

    logger.info("Restoring baseline game state.")
    restore_account(BASELINE_NAME)

    # Baseline = "no per-account slot is live". Clear the marker so the next
    # swap_account_data call enters the cold-start path cleanly.
    try:
        LAST_ACTIVE_FILE.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to clear last_active marker after baseline restore: %s", exc)


def swap_account_data(new_account_name: str) -> None:
    if not _is_real_account(new_account_name):
        return

    if not verify_game_data_present():
        logger.warning(
            "Game data not found at expected locations. Skipping account isolation — install the game first.",
        )
        set_last_active_account(new_account_name)
        return

    # First managed swap ever: capture the user's pre-launcher state so
    # restore_to_baseline (post-game-exit) has somewhere to return to.
    snapshot_baseline_if_missing()

    last_active = get_last_active_account()

    if last_active and last_active != new_account_name:
        logger.info("Swapping account: backing up '%s' first", last_active)
        backup_account(last_active)

    logger.info("Restoring account data for '%s'", new_account_name)
    restore_account(new_account_name)
    set_last_active_account(new_account_name)
