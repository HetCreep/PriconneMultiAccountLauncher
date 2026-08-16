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


def redact_secrets(text: str) -> str:
    """Replace credential-shaped substrings. Line structure is left intact.

    Use for text whose newlines are ours and must stay readable (tracebacks). For
    anything user- or server-controlled use `redact()`, which also neutralizes CR/LF.
    """
    out = _KEY_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    for pat in _TOKEN_PATTERNS:
        out = pat.sub("[REDACTED:token]", out)
    return out


def redact(text: str) -> str:
    """Return the input text with control chars neutralized and credential-shaped substrings replaced."""
    return redact_secrets(_sanitize_for_log_injection(text))


_REDACTION_FAILED: Final = "[REDACTION FAILED - record suppressed]"


class RedactionFilter(logging.Filter):
    """Fail-CLOSED redaction.

    If anything in the redaction path raises, the record is replaced with a fixed
    placeholder rather than passed through raw. Emitting an unredacted record is the
    exact leak this filter exists to prevent, so a redaction bug must cost a log line,
    never a token. See domain/log-sanitization.md.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.msg if isinstance(record.msg, str) else str(record.msg)
            redacted_msg = redact(msg)
            redacted_args = self._redact_args(record.args) if record.args else record.args
            redacted_exc_text = self._redact_exc_text(record)
        except Exception:  # noqa: BLE001 - fail closed, see docstring
            record.msg = _REDACTION_FAILED
            record.args = None
            record.exc_info = None
            record.exc_text = None
            return True

        record.msg = redacted_msg
        record.args = redacted_args
        if redacted_exc_text is not None:
            # Materialize the traceback here so handlers format the redacted text
            # instead of re-rendering the raw exception from exc_info.
            record.exc_text = redacted_exc_text
        return True

    @staticmethod
    def _redact_exc_text(record: logging.LogRecord) -> str | None:
        if not record.exc_info and not record.exc_text:
            return None
        text = record.exc_text or logging.Formatter().formatException(record.exc_info)  # type: ignore[arg-type]
        # redact_secrets, not redact: a traceback's newlines are ours and must stay
        # readable. Escaping them would collapse every stack trace into one line.
        return redact_secrets(text)

    def _redact_args(self, args: Any) -> Any:
        if isinstance(args, dict):
            return {k: self._redact_arg(v) for k, v in args.items()}
        if isinstance(args, tuple):
            return tuple(self._redact_arg(a) for a in args)
        return args

    @staticmethod
    def _redact_arg(value: Any) -> Any:
        """Redact one positional arg while preserving the type `%`-formatting needs.

        Numbers must stay numbers: `"%d" % ("200",)` raises TypeError, logging swallows
        it in handleError, and the record is lost. Numeric types cannot carry a secret,
        so passing them through costs nothing. Everything else is stringified and
        redacted, which is safe because a non-numeric arg is formatted with %s/%r.
        """
        if isinstance(value, str):
            return redact(value)
        if value is None or isinstance(value, (int, float, complex)):  # bool is an int
            return value
        return redact(str(value))


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
