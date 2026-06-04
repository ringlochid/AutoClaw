"""Compatibility shell for the src autoclaw owner."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_owner = import_module("autoclaw.cli.json_output")


def __getattr__(name: str) -> Any:
    return getattr(_owner, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_owner)))


__all__ = list(
    getattr(_owner, "__all__", [name for name in dir(_owner) if not name.startswith("_")])
)
