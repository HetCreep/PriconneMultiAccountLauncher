"""Cross-machine backup / restore via passphrase-derived AES-GCM.

Why this exists: DPAPI-encrypted `.bytes` files are bound to a specific Windows
user + machine and cannot be copied verbatim across PCs. This module decrypts
each account locally (via DPAPI), bundles all accounts + shortcuts + browser
configs into a single JSON, then re-encrypts the JSON with an AES-256-GCM key
derived from a user-chosen passphrase (PBKDF2-HMAC-SHA256, 310 000 iterations
per OWASP 2024 minimum). The resulting `.pmal` file is portable.

On import, the reverse: decrypt with passphrase, then re-encrypt each account
under the NEW machine's DPAPI key before writing to disk.

File format (`.pmal`):

    offset  len  field
    -----  ----  -----
    0      4     magic "PMAL"
    4      1     format version (1)
    5      16    PBKDF2 salt
    21     12    AES-GCM nonce
    33     16    AES-GCM tag
    49     N     ciphertext (AES-GCM(json plaintext))

Plaintext JSON shape:

    {
      "format_version": 1,
      "exported_at": "<ISO-8601 UTC>",
      "source_version": "<launcher version>",
      "accounts": { "<name>": {"accessToken": "...", "_device_params": {...}}, ... },
      "shortcuts": { "<name>": {...}, ... },
      "account_shortcuts": { "<name>": {...}, ... },
      "browser_config": { "<name>": {...}, ... }
    }
"""

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2

logger = logging.getLogger(__name__)

MAGIC = b"PMAL"
FORMAT_VERSION = 1
PBKDF2_ITERATIONS = 310_000  # OWASP 2024 minimum for PBKDF2-HMAC-SHA256
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32  # AES-256
HEADER_LEN = len(MAGIC) + 1 + SALT_LEN + NONCE_LEN + TAG_LEN
MIN_PASSPHRASE_LEN = 8


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return PBKDF2(
        passphrase.encode("utf-8"),
        salt,
        dkLen=KEY_LEN,
        count=PBKDF2_ITERATIONS,
        hmac_hash_module=SHA256,
    )


def _load_account_blob(path: Path) -> dict:
    """DPAPI-decrypt an account `.bytes` file and return plaintext dict."""
    from lib.DGPSessionV2 import DgpSessionV2

    session = DgpSessionV2()
    session.read_bytes(str(path))
    data = dict(session.actauth)
    data["_device_params"] = session.device_params
    return data


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json_atomic(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def export_backup(passphrase: str, output_path: Path) -> dict:
    """Bundle every account + shortcut + browser config, encrypt, write .pmal.

    Returns a summary dict counting items per category.
    Raises ValueError on passphrase too short or write failure.
    """
    if len(passphrase) < MIN_PASSPHRASE_LEN:
        raise ValueError(f"Passphrase must be at least {MIN_PASSPHRASE_LEN} characters")

    from static.config import DataPathConfig
    from static.env import Env

    bundle: dict = {
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_version": Env.VERSION,
        "accounts": {},
        "shortcuts": {},
        "account_shortcuts": {},
        "browser_config": {},
    }

    if DataPathConfig.ACCOUNT.exists():
        for f in DataPathConfig.ACCOUNT.glob("*.bytes"):
            if any(f.name.endswith(s) for s in (".bak.0", ".bak.1")):
                continue
            try:
                bundle["accounts"][f.stem] = _load_account_blob(f)
            except Exception as exc:
                logger.warning("Skipping account %s during export: %s", f.stem, exc)

    if DataPathConfig.SHORTCUT.exists():
        for f in DataPathConfig.SHORTCUT.glob("*.json"):
            try:
                bundle["shortcuts"][f.stem] = _load_json(f)
            except Exception as exc:
                logger.warning("Skipping shortcut %s: %s", f.stem, exc)

    if DataPathConfig.ACCOUNT_SHORTCUT.exists():
        for f in DataPathConfig.ACCOUNT_SHORTCUT.glob("*.json"):
            try:
                bundle["account_shortcuts"][f.stem] = _load_json(f)
            except Exception as exc:
                logger.warning("Skipping account_shortcut %s: %s", f.stem, exc)

    if DataPathConfig.BROWSER_CONFIG.exists():
        for f in DataPathConfig.BROWSER_CONFIG.glob("*.json"):
            try:
                bundle["browser_config"][f.stem] = _load_json(f)
            except Exception as exc:
                logger.warning("Skipping browser_config %s: %s", f.stem, exc)

    plaintext = json.dumps(bundle, ensure_ascii=False).encode("utf-8")

    salt = secrets.token_bytes(SALT_LEN)
    nonce = secrets.token_bytes(NONCE_LEN)
    key = _derive_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)

    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as f:
        f.write(MAGIC)
        f.write(bytes([FORMAT_VERSION]))
        f.write(salt)
        f.write(nonce)
        f.write(tag)
        f.write(ciphertext)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, output_path)

    summary = {
        "accounts": len(bundle["accounts"]),
        "shortcuts": len(bundle["shortcuts"]),
        "account_shortcuts": len(bundle["account_shortcuts"]),
        "browser_config": len(bundle["browser_config"]),
        "bytes_written": output_path.stat().st_size,
    }
    logger.info("Exported backup to %s: %s", output_path, summary)
    return summary


def import_backup(passphrase: str, input_path: Path) -> dict:
    """Decrypt .pmal, restore accounts/shortcuts to local data dir.

    Each account is re-encrypted via THIS machine's DPAPI (so the on-disk
    .bytes is bound to the current Windows user + machine, same as natively
    imported accounts).
    Returns a summary dict counting items restored per category.
    """
    if len(passphrase) < MIN_PASSPHRASE_LEN:
        raise ValueError(f"Passphrase must be at least {MIN_PASSPHRASE_LEN} characters")

    from lib.DGPSessionV2 import DgpSessionV2
    from static.config import DataPathConfig

    with open(input_path, "rb") as f:
        raw = f.read()

    if len(raw) < HEADER_LEN:
        raise ValueError("File is truncated or not a PMAL backup")
    if raw[:4] != MAGIC:
        raise ValueError("Not a valid .pmal file (magic bytes mismatch)")
    version = raw[4]
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported backup format version: {version}")

    salt = raw[5 : 5 + SALT_LEN]
    nonce = raw[5 + SALT_LEN : 5 + SALT_LEN + NONCE_LEN]
    tag = raw[5 + SALT_LEN + NONCE_LEN : HEADER_LEN]
    ciphertext = raw[HEADER_LEN:]

    key = _derive_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    except (ValueError, KeyError) as exc:
        raise ValueError("Wrong passphrase or corrupted backup file") from exc

    bundle = json.loads(plaintext.decode("utf-8"))

    DataPathConfig.ACCOUNT.mkdir(parents=True, exist_ok=True)
    DataPathConfig.SHORTCUT.mkdir(parents=True, exist_ok=True)
    DataPathConfig.ACCOUNT_SHORTCUT.mkdir(parents=True, exist_ok=True)
    DataPathConfig.BROWSER_CONFIG.mkdir(parents=True, exist_ok=True)

    summary = {"accounts": 0, "shortcuts": 0, "account_shortcuts": 0, "browser_config": 0}

    for name, data in bundle.get("accounts", {}).items():
        session = DgpSessionV2()
        device_params = data.pop("_device_params", None)
        if device_params:
            session.device_params = device_params
        session.actauth = data
        path = DataPathConfig.ACCOUNT.joinpath(name).with_suffix(".bytes")
        session.write_bytes(str(path))  # re-encrypts under THIS machine's DPAPI
        summary["accounts"] += 1

    for name, data in bundle.get("shortcuts", {}).items():
        _save_json_atomic(DataPathConfig.SHORTCUT.joinpath(name).with_suffix(".json"), data)
        summary["shortcuts"] += 1

    for name, data in bundle.get("account_shortcuts", {}).items():
        _save_json_atomic(DataPathConfig.ACCOUNT_SHORTCUT.joinpath(name).with_suffix(".json"), data)
        summary["account_shortcuts"] += 1

    for name, data in bundle.get("browser_config", {}).items():
        _save_json_atomic(DataPathConfig.BROWSER_CONFIG.joinpath(name).with_suffix(".json"), data)
        summary["browser_config"] += 1

    logger.info("Imported backup from %s: %s", input_path, summary)
    return summary
