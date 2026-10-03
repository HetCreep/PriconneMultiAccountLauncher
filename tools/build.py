"""Bundle LICENSE files from project root + .venv into assets/license/LICENSE.

Robust to non-UTF8 files (some 3rd-party LICENSE files are cp1252 or latin1):
tries UTF-8 first, falls back to latin1, then logs and skips on hard error.
"""

import glob
import sys
import sysconfig
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

    # release.yml installs into the runner's interpreter, not .venv, so search the active
    # site-packages as well; otherwise the shipped file contained only the project LICENSE.
    pattern = "**/*[Ll][Ii][Cc][Ee][Nn][SsCc][Ee]*"
    roots = [".venv", sysconfig.get_paths()["purelib"]]
    files = ["./LICENSE"]
    for root in dict.fromkeys(roots):
        files.extend(glob.glob(str(Path(root) / pattern), recursive=True))
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
