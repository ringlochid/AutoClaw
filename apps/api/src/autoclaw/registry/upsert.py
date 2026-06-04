"""Temporary Phase 6 shim for the legacy registry upsert owner."""

from __future__ import annotations

from app.registry.upsert import (
    upsert_policy_definition,
    upsert_role_definition,
    upsert_workflow_definition,
)

__all__ = [
    "upsert_policy_definition",
    "upsert_role_definition",
    "upsert_workflow_definition",
]
