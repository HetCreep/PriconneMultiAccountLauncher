"""Bundle LICENSE files from project root + .venv into assets/license/LICENSE.

Robust to non-UTF8 files (some 3rd-party LICENSE files are cp1252 or latin1):
tries UTF-8 first, falls back to latin1, then logs and skips on hard error.
"""

import glob
import sys
from pathlib import Path

WIDTH = 62
DELIMITER = "\n\n" + ("=" * WIDTH) + "\n\n"


def read_text_robust(path: Path) -> str | None:
    for encoding in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            print(f"[build.py] WARN: cannot read {path}: {exc}", file=sys.stderr)
            return None
    print(f"[build.py] WARN: {path} not decodable in any common encoding; skipping", file=sys.stderr)
    return None


def main() -> int:
    output = ""
    Path("assets/license").mkdir(parents=True, exist_ok=True)

    files = ["./LICENSE", *glob.glob(".venv/**/*[Ll][Ii][Cc][Ee][Nn][SsCc][Ee]*", recursive=True)]
    for file in files:
        path = Path(file)
        if not path.is_file():
            continue
        text = read_text_robust(path)
        if text is None:
            continue
        output += DELIMITER + path.parent.name.center(WIDTH * 2 - 1) + DELIMITER + text

    with open("assets/license/LICENSE", "w", encoding="utf-8") as f:
        f.write(output)
    print(f"[build.py] wrote assets/license/LICENSE ({len(output)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
