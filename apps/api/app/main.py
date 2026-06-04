"""Temporary Phase 6 shim for the legacy app startup entrypoint."""

from __future__ import annotations

from collections.abc import Callable

from autoclaw.main import app as _autoclaw_app
from autoclaw.main import create_app as _autoclaw_create_app
from fastapi import FastAPI

app: FastAPI = _autoclaw_app
create_app: Callable[..., FastAPI] = _autoclaw_create_app

__all__ = ["app", "create_app"]
