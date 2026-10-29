"""Validators for names and values that cross a trust boundary. Standard library only.

Kept free of project imports so the test job can run them without installing anything.
Used by: backup import (an untrusted .pmal), the account swapper (account_path read from a
shortcut file that may itself have come from an import), and shortcut script generation.
"""

from typing import Any

BASELINE_NAME = "_baseline_"
_RESERVED = frozenset({BASELINE_NAME, "always_extract_from_dmm"})

_BACKSLASH = chr(92)
_PATH_CHARS = frozenset("/" + _BACKSLASH + ':*?"<>|')
# Meaningful to a shell or to PowerShell string expansion. Rejected only in strict mode:
# a name from an untrusted bundle has no legitimate use for them.
_SHELL_CHARS = frozenset("$`;")
_MAX_NAME = 128

# PowerShell treats the typographic single quotes as string delimiters too.
_PS_QUOTES = ("'", "‘", "’", "‚", "‛")


def is_reserved_account_name(name: str) -> bool:
    """True for names the launcher uses internally. Windows paths are case-insensitive."""
    return isinstance(name, str) and name.casefold() in _RESERVED


def check_name(name: object, *, strict: bool) -> str:
    """Return `name` if it is safe to join onto a data directory, else raise ValueError.

    Rejected in every mode: non-text or empty, path separators and Windows-reserved
    characters, control characters, a dot-segment ("." or ".."), and leading or trailing
    spaces/dots (Windows silently drops them, so two names can alias one file).

    `strict` (untrusted input) additionally rejects any dot, because the app derives file
    names with `with_suffix`, which replaces everything after the last dot: an imported
    "a.b" would be listed as "a.b" but read from "a.json", i.e. a different record.
    Also rejects `$`, backtick and `;`.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("name must be non-empty text")
    if len(name) > _MAX_NAME:
        raise ValueError(f"name longer than {_MAX_NAME} characters")
    if name in (".", "..") or name != name.strip() or name.endswith("."):
        raise ValueError(f"unsafe name: {name!r}")
    if any(ch in _PATH_CHARS for ch in name) or any(ord(ch) < 32 for ch in name):
        raise ValueError(f"unsafe name: {name!r}")
    if strict and ("." in name or any(ch in _SHELL_CHARS for ch in name)):
        raise ValueError(f"unsafe name: {name!r}")
    return name


def ps_quote(value: str) -> str:
    """Escape `value` for the inside of a PowerShell SINGLE-quoted literal.

    A single-quoted literal performs no variable or subexpression expansion, so the only
    thing that can end it is a quote character, which is doubled. Use with a template that
    wraps the placeholder in single quotes, never double quotes.
    """
    for q in _PS_QUOTES:
        value = value.replace(q, q + q)
    return value


def check_json_shape(obj: Any, *, max_depth: int, max_nodes: int) -> None:
    """Raise ValueError if `obj` nests deeper than max_depth or holds more than max_nodes values."""
    stack: list[tuple[Any, int]] = [(obj, 1)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            raise ValueError("too many values")
        if depth > max_depth:
            raise ValueError("nested too deeply")
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
