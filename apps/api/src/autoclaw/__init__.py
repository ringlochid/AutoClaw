from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pkgutil import extend_path
from typing import Any

__path__ = extend_path(__path__, __name__)

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
