"""Temporary Phase 6 shim for the legacy checkpoint-control owner."""

from __future__ import annotations

from app.runtime.control.checkpoint import record_checkpoint

__all__ = ["record_checkpoint"]
