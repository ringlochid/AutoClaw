from __future__ import annotations

from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.contracts import (
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceResponse,
)
from autoclaw.runtime.errors import illegal_state_error

OBSERVABILITY_FILE_SPECS: tuple[tuple[str, str], ...] = (
    ("delivery-state.json", "Latest task-scoped delivery-state projection."),
    ("continuity-state.json", "Latest task-scoped continuity-state projection."),
    ("watchdog-state.json", "Latest task-scoped watchdog-state projection."),
    ("provider-events.ndjson", "Normalized provider-event history for the selected task."),
)


async def observability_ref(
    session: AsyncSession,
    task_id: str,
    filename: str,
    description: str,
) -> ObservabilityFileRef:
    _observability_surface_unavailable()


async def operator_snapshot(
    session: AsyncSession,
    task_id: str,
) -> OperatorFlowSnapshotResponse:
    _observability_surface_unavailable()


async def operator_trace(
    session: AsyncSession,
    task_id: str,
    *,
    scope: str = "current",
    q: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    sort: str = "occurred_at_desc",
) -> OperatorFlowTraceResponse:
    _observability_surface_unavailable()


def _observability_surface_unavailable() -> NoReturn:
    raise illegal_state_error(
        "operator snapshots, traces, and observability refs are not available in this build",
        suggested_next_step=(
            "Do not retry this request; use only the controller capabilities exposed "
            "by this installation."
        ),
    )


__all__ = [
    "OBSERVABILITY_FILE_SPECS",
    "observability_ref",
    "operator_snapshot",
    "operator_trace",
]
