"""lib/safe_names: the validators behind backup import, account_path handling and shortcut scripts.

Stdlib only, so the CI test job runs it without installing anything. Also runnable as a script.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "PriconneMultiAccountLauncher"))

from lib.safe_names import check_json_shape, check_name, is_reserved_account_name, ps_quote

BS = chr(92)


def _rejects(name, strict):
    try:
        check_name(name, strict=strict)
    except ValueError:
        return True
    return False


def test_traversal_names_are_rejected_in_both_modes():
    for bad in ("..", ".", "../x", "..\\x".replace("\\", BS), "a/b", "a" + BS + "b", "C:x", "/abs", BS + "abs", ""):
        assert _rejects(bad, False) and _rejects(bad, True), bad


def test_windows_aliasing_is_rejected():
    for bad in ("name.", "name ", " name", "na\x00me", "na\nme", "a*b", "a?b", "a|b"):
        assert _rejects(bad, False), repr(bad)


def test_non_text_and_oversize_are_rejected():
    for bad in (None, 5, ["a"], "x" * 129):
        assert _rejects(bad, False), repr(bad)


def test_ordinary_and_non_ascii_names_pass():
    for ok in ("Primary", "main account", "บัญชีหลัก", "アカウント", "a-b_c", "O'Brien"):
        assert check_name(ok, strict=True) == ok


def test_dots_and_shell_characters_only_rejected_when_strict():
    # An existing account may legitimately contain a dot mid-name; an untrusted bundle may not.
    assert check_name("my.account", strict=False) == "my.account"
    for bad in ("my.account", "a$b", "a`b", "a;b", "$(calc)"):
        assert _rejects(bad, True), bad
    assert not _rejects("a$b", False)


def test_reserved_names_are_case_insensitive():
    for name in ("_baseline_", "_BASELINE_", "Always_Extract_From_DMM", "ALWAYS_EXTRACT_FROM_DMM"):
        assert is_reserved_account_name(name), name
    assert not is_reserved_account_name("Primary")


def test_ps_quote_doubles_every_quote_form_powershell_accepts():
    assert ps_quote("a'b") == "a''b"
    for q in ("\u2018", "\u2019", "\u201a", "\u201b"):
        assert ps_quote("x" + q + "y") == "x" + q + q + "y", repr(q)
    # Nothing else is touched: in a single-quoted literal `$`, backtick and parens are inert.
    assert ps_quote("$(calc) `x`") == "$(calc) `x`"


def test_ps_quote_output_cannot_close_the_literal():
    payload = "'; Remove-Item C:\\x -Recurse; '"
    quoted = ps_quote(payload)
    # After doubling, every quote in the body appears in an even run, so the literal stays open.
    run = 0
    for ch in quoted + "\0":
        if ch == "'":
            run += 1
        else:
            assert run % 2 == 0, quoted
            run = 0


def test_json_shape_limits():
    check_json_shape({"a": [1, 2, {"b": 3}]}, max_depth=8, max_nodes=100)
    deep = cur = []
    for _ in range(50):
        nxt = []
        cur.append(nxt)
        cur = nxt
    for bad, kw in ((deep, dict(max_depth=8, max_nodes=10_000)), (list(range(200)), dict(max_depth=8, max_nodes=100))):
        try:
            check_json_shape(bad, **kw)
        except ValueError:
            continue
        raise AssertionError("shape limit not enforced")


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
