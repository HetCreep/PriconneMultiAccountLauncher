"""Log redaction filter.

Implements [domain/log-sanitization.md]. Substitutes credential-bearing
values in every LogRecord before any handler formats it.

`install_redaction_filter()` installs the filter on the root logger so
every module logger inherits it.
"""

import logging
import re
from typing import Any, Final

_TOKEN_PATTERNS: Final = [
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),  # JWT
    re.compile(r"\b[A-Fa-f0-9]{64,}\b"),                                    # long hex blob
    re.compile(r"Bearer\s+[A-Za-z0-9_.\-+/=]+", re.IGNORECASE),
    re.compile(r"Basic\s+[A-Za-z0-9+/=]+", re.IGNORECASE),
]

_KEY_PATTERN: Final = re.compile(
    r"(?i)(token|cookie|password|secret|auth|session|hwid|"
    r"mac[_-]?address|hdd[_-]?serial|motherboard|cpu[_-]?id|machine[_-]?guid|"
    r"accessToken|refreshToken|access_token|refresh_token|client_secret|api_key)"
    r"\s*[:=]\s*[\"']?([^\"'\s,}]+)"
)


def redact(text: str) -> str:
    """Return the input text with credential-shaped substrings replaced."""
    out = _KEY_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    for pat in _TOKEN_PATTERNS:
        out = pat.sub("[REDACTED:token]", out)
    return out


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            else:
                record.msg = redact(str(record.msg))
            if record.args:
                record.args = self._redact_args(record.args)
        except Exception:  # noqa: BLE001 — never block logging on redaction error
            pass
        return True

    def _redact_args(self, args: Any) -> Any:
        if isinstance(args, dict):
            return {k: redact(str(v)) for k, v in args.items()}
        if isinstance(args, tuple):
            return tuple(redact(str(a)) for a in args)
        return args


def install_redaction_filter() -> None:
    """Attach RedactionFilter to the root logger; idempotent."""
    root = logging.getLogger()
    for f in root.filters:
        if isinstance(f, RedactionFilter):
            return
    root.addFilter(RedactionFilter())
