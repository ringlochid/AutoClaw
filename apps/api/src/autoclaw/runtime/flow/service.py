from __future__ import annotations

from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.contracts import (
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
)
from autoclaw.runtime.errors import illegal_state_error


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    _runtime_flow_surface_unavailable()


async def list_runtime_flows(
    session: AsyncSession,
    *,
    q: str | None = None,
    cursor: str | None = None,
    status: str = "any",
    limit: int = 50,
    sort: str = "updated_at_desc",
) -> RuntimeFlowSummaryListResponse:
    _runtime_flow_surface_unavailable()


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowRead:
    _runtime_flow_surface_unavailable()


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowPauseResponse:
    _runtime_flow_surface_unavailable()


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowRead:
    _runtime_flow_surface_unavailable()


def _runtime_flow_surface_unavailable() -> NoReturn:
    raise illegal_state_error(
        "runtime flow reads and controls are not available in this build",
        suggested_next_step=(
            "Do not retry this request; use only the controller capabilities exposed "
            "by this installation."
        ),
    )


__all__ = [
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "list_runtime_flows",
    "pause_runtime_flow",
    "runtime_flow_read",
]
