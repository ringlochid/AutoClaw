from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_RUNTIME_ROOT = PACKAGE_ROOT.parents[3] / "src" / "autoclaw" / "runtime"

__path__ = [str(PACKAGE_ROOT), str(SRC_RUNTIME_ROOT)]
