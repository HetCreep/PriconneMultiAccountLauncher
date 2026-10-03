"""Dependency vulnerability audit — fails on any KNOWN CVE in pinned deps.

Usage:
    .venv\\Scripts\\python.exe tools\\audit.py

Runs `pip-audit` against `requirements.lock.txt` and prints a human-readable
report. Exit code: 0 = clean, 1 = vulns found, 2 = tool error.

CI should run this on every PR + before tagging a release per
.claude/rules/ecc/domain/distribution-security.md "Vulnerability Response".
"""

import subprocess
import sys


def main() -> int:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-r", "requirements.lock.txt"],
            check=False,
        )
    except FileNotFoundError:
        print("pip-audit not installed. Install with: pip install pip-audit", file=sys.stderr)
        return 2
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
