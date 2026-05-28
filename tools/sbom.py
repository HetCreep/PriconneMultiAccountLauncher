"""Generate a CycloneDX SBOM for the runtime dependency tree.

Usage:
    .venv\\Scripts\\python.exe tools\\sbom.py

Writes `dist/sbom.cdx.json`. Attach to each GitHub Release per
.claude/rules/ecc/domain/distribution-security.md.
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    out_dir = Path("dist")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "sbom.cdx.json"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "cyclonedx-json", "-r", "requirements.lock.txt"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("pip-audit not installed. Install with: pip install pip-audit", file=sys.stderr)
        return 2

    if result.returncode not in (0, 1):  # 1 = vulns found but SBOM still emitted
        print(f"pip-audit failed (rc={result.returncode})", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    # pip-audit prints the SBOM JSON to stdout in cyclonedx-json format.
    try:
        json.loads(result.stdout)  # validate
    except json.JSONDecodeError as exc:
        print(f"pip-audit output is not valid JSON: {exc}", file=sys.stderr)
        return 3

    out_file.write_text(result.stdout, encoding="utf-8")
    print(f"SBOM written: {out_file}")
    if result.returncode == 1:
        print("Warning: pip-audit reported vulnerabilities. See:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
