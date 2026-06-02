"""Log redaction filter.

Implements [domain/log-sanitization.md]. Substitutes credential-bearing
values in every LogRecord before any handler formats it.

`install_redaction_filter()` installs the filter on every root HANDLER (not the
root logger): a filter on the root logger only runs for records that logger
processes directly, while records from child loggers (`getLogger(__name__)`)
propagate to the root *handlers* and bypass the root logger's filters.
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


def _sanitize_for_log_injection(text: str) -> str:
    """Encode CR/LF/TAB so user-controlled data cannot forge fake log lines (OWASP Log Injection)."""
    return text.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def redact(text: str) -> str:
    """Return the input text with control chars neutralized and credential-shaped substrings replaced."""
    out = _sanitize_for_log_injection(text)
    out = _KEY_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", out)
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
    """Attach RedactionFilter to every root handler + the root logger; idempotent.

    Must be called AFTER handlers are attached (e.g. after logging.basicConfig).
    Handler-level attachment is what actually redacts child-logger records.
    """
    root = logging.getLogger()
    if not any(isinstance(f, RedactionFilter) for f in root.filters):
        root.addFilter(RedactionFilter())
    for handler in root.handlers:
        if not any(isinstance(f, RedactionFilter) for f in handler.filters):
            handler.addFilter(RedactionFilter())
