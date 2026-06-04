"""Explicit Phase 6 bridge for the legacy observability control owner."""

from __future__ import annotations

from app.runtime.control import observability as legacy_observability

OBSERVABILITY_FILE_SPECS = legacy_observability.OBSERVABILITY_FILE_SPECS
observability_ref = legacy_observability.observability_ref
operator_snapshot = legacy_observability.operator_snapshot
operator_trace = legacy_observability.operator_trace

__all__ = [
    "OBSERVABILITY_FILE_SPECS",
    "observability_ref",
    "operator_snapshot",
    "operator_trace",
]
