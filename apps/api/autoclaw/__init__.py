from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_PACKAGE_ROOT = PACKAGE_ROOT.parent / "src" / PACKAGE_ROOT.name

__path__ = [str(PACKAGE_ROOT)]
if SRC_PACKAGE_ROOT.is_dir():
    __path__.append(str(SRC_PACKAGE_ROOT))

try:
    __version__ = version("autoclaw")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"


def __getattr__(name: str) -> Any:
    if name == "app":
        from .main import app

        return app
    if name == "create_app":
        from .main import create_app

        return create_app
    raise AttributeError(name)


__all__ = ["__version__", "app", "create_app"]
