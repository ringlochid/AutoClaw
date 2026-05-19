from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    AssignmentModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    NodeSessionModel,
)
from app.runtime.contracts import FlowStatus
from app.runtime.control.failures import (
    illegal_caller_error,
    illegal_state_error,
    stale_dispatch_error,
)
from app.runtime.control.flow.queries import require_flow_for_task


@dataclass(frozen=True)
class NodeSessionAuthority:
    task_id: str
    dispatch_id: str
    assignment_id: str
    attempt_id: str
    node_key: str
    node_session_id: str
    session_key: str


async def validate_node_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    invalid_summary: str = "invalid session key",
    stale_summary: str = "stale session key",
    inactive_summary: str = "inactive session key",
) -> NodeSessionAuthority:
    node_session = await _load_live_node_session(
        session,
        session_key=session_key,
        invalid_summary=invalid_summary,
        stale_summary=stale_summary,
    )
    dispatch_id = node_session.dispatch_id
    assert dispatch_id is not None
    dispatch = await _require_bound_dispatch(
        session,
        task_id=task_id,
        session_key=session_key,
        dispatch_id=dispatch_id,
        stale_summary=stale_summary,
    )
    flow = await _require_running_current_flow(
        session,
        task_id=task_id,
        dispatch=dispatch,
        inactive_summary=inactive_summary,
        stale_summary=stale_summary,
    )
    await _require_current_assignment(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
        node_session=node_session,
        stale_summary=stale_summary,
    )
    assignment_id = dispatch.assignment_id
    attempt_id = dispatch.attempt_id
    assert assignment_id is not None
    assert attempt_id is not None
    return NodeSessionAuthority(
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        assignment_id=assignment_id,
        attempt_id=attempt_id,
        node_key=dispatch.node_key,
        node_session_id=node_session.node_session_id,
        session_key=node_session.session_key,
    )


async def _load_live_node_session(
    session: AsyncSession,
    *,
    session_key: str,
    invalid_summary: str,
    stale_summary: str,
) -> NodeSessionModel:
    node_session = await session.scalar(
        select(NodeSessionModel)
        .options(raiseload("*"))
        .where(
            NodeSessionModel.session_key == session_key,
            NodeSessionModel.session_status == "live",
            NodeSessionModel.closed_at.is_(None),
        )
    )
    if node_session is None:
        any_session = await session.scalar(
            select(NodeSessionModel.node_session_id)
            .where(NodeSessionModel.session_key == session_key)
            .limit(1)
        )
        if any_session is None:
            raise illegal_caller_error(invalid_summary)
        raise stale_dispatch_error(stale_summary)
    if node_session.dispatch_id is None:
        raise stale_dispatch_error(stale_summary)
    return node_session


async def _require_bound_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    dispatch_id: str,
    stale_summary: str,
) -> DispatchTurnModel:
    dispatch = await session.get(
        DispatchTurnModel,
        dispatch_id,
        options=(raiseload("*"),),
    )
    if dispatch is None:
        raise stale_dispatch_error(stale_summary)
    if dispatch.task_id != task_id:
        raise stale_dispatch_error(f"session key '{session_key}' is not bound to task '{task_id}'")
    return dispatch


async def _require_running_current_flow(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    inactive_summary: str,
    stale_summary: str,
) -> FlowModel:
    flow = await require_flow_for_task(session, task_id)
    if flow.status != FlowStatus.RUNNING.value:
        raise illegal_state_error(
            inactive_summary,
            suggested_next_step=(
                "Reread the current runtime status and dispatch context, then use the "
                "operator lane to resume or inspect the task before sending more "
                "callback writes."
            ),
        )

    if flow.current_open_dispatch_id != dispatch.dispatch_id:
        raise stale_dispatch_error(stale_summary)
    if dispatch.dispatch_id != flow.current_open_dispatch_id:
        raise stale_dispatch_error(stale_summary)
    if dispatch.control_state != "live" or dispatch.closed_at is not None:
        raise stale_dispatch_error(stale_summary)
    if dispatch.assignment_id is None or dispatch.attempt_id is None:
        raise stale_dispatch_error(stale_summary)
    if flow.current_node_key != dispatch.node_key:
        raise stale_dispatch_error(stale_summary)
    return flow


async def _require_current_assignment(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    node_session: NodeSessionModel,
    stale_summary: str,
) -> None:
    if dispatch.assignment_id is None or dispatch.attempt_id is None:
        raise stale_dispatch_error(stale_summary)
    if dispatch.flow_node_id is None:
        raise stale_dispatch_error(stale_summary)
    if node_session.flow_node_id != dispatch.flow_node_id:
        raise stale_dispatch_error(stale_summary)
    if node_session.assignment_id != dispatch.assignment_id:
        raise stale_dispatch_error(stale_summary)
    if node_session.attempt_id != dispatch.attempt_id:
        raise stale_dispatch_error(stale_summary)
    assignment = await session.get(
        AssignmentModel,
        dispatch.assignment_id,
        options=(raiseload("*"),),
    )
    if assignment is None or assignment.task_id != task_id:
        raise stale_dispatch_error(stale_summary)
    if assignment.current_attempt_id != dispatch.attempt_id:
        raise stale_dispatch_error(stale_summary)

    current_assignment_id = await session.scalar(
        select(FlowNodeModel.current_assignment_id).where(
            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
            FlowNodeModel.node_key == dispatch.node_key,
        )
    )
    if current_assignment_id != dispatch.assignment_id:
        raise stale_dispatch_error(stale_summary)


__all__ = ["NodeSessionAuthority", "validate_node_session_key"]
