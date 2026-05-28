"""Anchor every project path to a deterministic base.

Avoids the failure mode where `Path("data")` resolves against the current
working directory — which is fragile when the launcher is invoked from a
shortcut, a scheduled task, or via the file-association handler from a
different folder.

In frozen PyInstaller builds: base = directory containing the bundled .exe.
In dev (source run via `python PriconneMultiAccountLauncher/...`): base =
the repository root (parent of the `PriconneMultiAccountLauncher/` package).
"""

import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR: Path = _base_dir()
DATA_DIR: Path = BASE_DIR / "data"
ASSETS_DIR: Path = BASE_DIR / "assets"
