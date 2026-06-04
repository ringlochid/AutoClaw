from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.models import DispatchTurnModel
from autoclaw.runtime.control.failures import invalid_request_shape_error
from autoclaw.runtime.control.flow.listing import (
    RUNTIME_FLOW_LIST_SORTS,
    RUNTIME_FLOW_LIST_STATUSES,
    WORKFLOW_MANIFEST_REF_DESCRIPTION,
    parse_runtime_flow_cursor,
    runtime_flow_summary_page,
    runtime_root_paths_by_task,
)
from autoclaw.runtime.control.flow.queries import current_semantic_flow_target
from autoclaw.runtime.control.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from autoclaw.schemas.runtime import (
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
    WorkflowManifestRef,
)
from autoclaw.schemas.runtime.contracts import FlowStatus


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    state = await current_runtime_state(session, task_id)
    runtime_paths = await runtime_root_paths_by_task(session, (task_id,))
    semantic_target = await current_semantic_flow_target(
        session,
        flow=state.flow,
        incomplete_summary="current semantic target is incomplete",
        suggested_next_step=(
            "Inspect the current node assignment and attempt currentness, then repair the "
            "incomplete semantic target before rereading this task."
        ),
    )
    return RuntimeFlowRead(
        task_id=state.task.task_id,
        task_title=state.task.title,
        task_summary=state.task.summary,
        workflow_key=state.task.workflow_key,
        status=FlowStatus(state.flow.status),
        active_flow_revision_id=state.flow.active_flow_revision_id or "",
        workflow_manifest_ref=WorkflowManifestRef(
            path=runtime_paths[task_id] / "workflow-manifest.md",
            description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
        ),
        current_node_key=(
            state.current_node.node_key
            if semantic_target is None
            else semantic_target.node.node_key
        ),
        active_attempt_id=(
            state.current_attempt.attempt_id
            if semantic_target is None
            else semantic_target.attempt.attempt_id
        ),
        updated_at=coerce_datetime_to_utc(state.flow.updated_at),
    )


async def list_runtime_flows(
    session: AsyncSession,
    *,
    q: str | None = None,
    cursor: str | None = None,
    status: str = "any",
    limit: int = 50,
    sort: str = "updated_at_desc",
) -> RuntimeFlowSummaryListResponse:
    if status not in RUNTIME_FLOW_LIST_STATUSES:
        raise invalid_request_shape_error(f"unknown status filter '{status}'")
    if sort not in RUNTIME_FLOW_LIST_SORTS:
        raise invalid_request_shape_error(f"unknown runtime task sort '{sort}'")
    return await runtime_flow_summary_page(
        session,
        q=q,
        status=status,
        sort=sort,
        offset=parse_runtime_flow_cursor(cursor),
        limit=limit,
    )


async def latest_unreplaced_fenced_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchTurnModel | None:
    return cast(
        DispatchTurnModel | None,
        await session.scalar(
            select(DispatchTurnModel)
            .where(
                DispatchTurnModel.task_id == task_id,
                DispatchTurnModel.control_state == "fenced",
                DispatchTurnModel.superseded_by_dispatch_id.is_(None),
                DispatchTurnModel.closed_at.is_not(None),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


__all__ = [
    "latest_unreplaced_fenced_dispatch",
    "list_runtime_flows",
    "runtime_flow_read",
]
