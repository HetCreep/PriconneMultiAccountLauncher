"""Redaction guarantees for lib/log_sanitizer.

Mandated by domain/log-sanitization.md and sequenced as the project's first test by
common/ci-gates.md. Runs under pytest, and also standalone (`python test/property/test_log_sanitizer.py`)
so it is useful before any test runner is installed.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "PriconneMultiAccountLauncher"))

from lib import log_sanitizer
from lib.log_sanitizer import RedactionFilter, redact, redact_secrets

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc-_123"
LONG_HEX = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _record(msg, args=None, exc_info=None):
    return logging.LogRecord("test", logging.ERROR, __file__, 1, msg, args, exc_info)


def test_jwt_is_redacted():
    assert JWT not in redact(f"got {JWT} back")


def test_key_value_pair_is_redacted():
    out = redact("access_token=s3cr3tvalue")
    assert "s3cr3tvalue" not in out
    assert "[REDACTED]" in out


def test_long_hex_blob_is_redacted():
    assert LONG_HEX not in redact(f"blob {LONG_HEX}")


def test_redact_escapes_newlines_but_redact_secrets_does_not():
    # redact() neutralizes CR/LF so untrusted text cannot forge log lines...
    assert "\n" not in redact("line1\nline2")
    # ...while redact_secrets() keeps structure, so tracebacks stay readable.
    assert "\n" in redact_secrets("line1\nline2")
    assert LONG_HEX not in redact_secrets(f"line1\n{LONG_HEX}\nline2")


def test_filter_redacts_message_and_args():
    # The format string deliberately carries no redactable key: _KEY_PATTERN would
    # otherwise consume the "%s" itself and leave a record that cannot be formatted.
    record = _record("session opened with %s", (LONG_HEX,))
    assert RedactionFilter().filter(record) is True
    assert LONG_HEX not in str(record.msg)
    assert LONG_HEX not in str(record.args)
    assert LONG_HEX not in record.getMessage(), "the formatted line is what reaches disk"


def test_filter_keeps_numeric_args_formattable():
    """Regression: stringifying numbers broke every '%d' log call.

    `"%d" % ("200",)` raises TypeError, logging swallows it in handleError, and the
    record is dropped. lib/DGPSessionV2.py logs an HTTP status this way on every response.
    """
    record = _record("response %d (%d bytes)", (200, 1234))
    assert RedactionFilter().filter(record) is True
    assert record.args == (200, 1234)
    assert record.getMessage() == "response 200 (1234 bytes)"


def test_filter_redacts_mapping_args():
    """Covers the dict branch of _redact_args.

    A lone dict argument is NOT a one-element tuple: LogRecord stores "a dict whose
    values are used for the merge (when there is only one argument, and it is a
    dictionary)", so `record.args` is the dict itself.

    Note the secret here is caught by the long-hex token pattern, NOT by _KEY_PATTERN:
    in a dict repr the key is quoted (`'mac_address': ...`) and _KEY_PATTERN requires
    the separator to follow the key directly. Do not read this as proof that dict-key
    redaction works.
    """
    record = _record("device %s", ({"mac_address": LONG_HEX},))
    assert isinstance(record.args, dict), "LogRecord should have collapsed the lone dict"
    assert RedactionFilter().filter(record) is True
    assert LONG_HEX not in record.getMessage()


def test_filter_redacts_arbitrary_object_args():
    """Covers the `redact(str(value))` fallback in _redact_arg.

    Anything that is neither str nor a number reaches the fallback and must be
    stringified through redaction. Two args, so LogRecord keeps the tuple and the
    mapping collapse above does not apply.
    """

    class Device:
        def __str__(self):
            return f"Device(mac_address={LONG_HEX})"

    record = _record("device %s at %s", (Device(), "slot-1"))
    assert isinstance(record.args, tuple)
    assert RedactionFilter().filter(record) is True
    assert LONG_HEX not in record.getMessage()
    assert "slot-1" in record.getMessage(), "harmless args must survive intact"


def test_filter_redacts_exception_traceback_and_keeps_it_readable():
    try:
        raise ValueError(f"access_token={LONG_HEX}")
    except ValueError:
        record = _record("boom", None, sys.exc_info())

    assert RedactionFilter().filter(record) is True
    assert record.exc_text is not None
    assert LONG_HEX not in record.exc_text
    assert "\n" in record.exc_text, "traceback structure must survive redaction"


def test_filter_fails_CLOSED_when_redaction_raises():
    """The whole point: a redaction bug costs a log line, never a token."""
    original = log_sanitizer.redact

    def explode(_text):
        raise RuntimeError("redaction is broken")

    log_sanitizer.redact = explode
    try:
        record = _record("access_token=%s", (LONG_HEX,))
        assert RedactionFilter().filter(record) is True
        assert LONG_HEX not in str(record.msg)
        assert record.args is None
        assert record.msg == "[REDACTION FAILED - record suppressed]"
    finally:
        log_sanitizer.redact = original


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
