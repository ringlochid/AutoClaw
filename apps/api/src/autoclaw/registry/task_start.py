"""Temporary Phase 6 shim for the legacy registry task-start owner."""

from __future__ import annotations

from app.registry.task_start import start_task_from_definition_service

__all__ = ["start_task_from_definition_service"]
