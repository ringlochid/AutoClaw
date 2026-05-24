from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel, FlowModel
from app.runtime.contracts import FlowStatus
from app.runtime.control.dispatch.control import (
    open_dispatch_for_attempt,
    stage_previous_dispatch_outputs,
)
from app.runtime.control.failures import illegal_state_error
from app.runtime.control.flow.resume import resolve_flow_resume_target
from app.runtime.control.flow.service import latest_unreplaced_fenced_dispatch

SEMANTIC_TARGET_INCOMPLETE_SUMMARY = "current semantic target is incomplete"
SEMANTIC_TARGET_REPAIR_NEXT_STEP = (
    "Inspect the current node assignment and attempt currentness, then repair the "
    "incomplete semantic target before continuing this task."
)


async def auto_open_next_running_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> bool:
    if flow.status != FlowStatus.RUNNING.value or flow.current_open_dispatch_id is not None:
        return False
    resolved_previous_dispatch = await _resolved_previous_dispatch(
        session,
        task_id=task_id,
        previous_dispatch=previous_dispatch,
    )
    if resolved_previous_dispatch is None or resolved_previous_dispatch.accepted_boundary is None:
        return False
    resume_target = await resolve_flow_resume_target(
        session,
        flow=flow,
        previous_dispatch=resolved_previous_dispatch,
    )
    dispatch_open_inputs = resume_target.dispatch_open_inputs()
    if dispatch_open_inputs is None:
        raise illegal_state_error(
            SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
            suggested_next_step=SEMANTIC_TARGET_REPAIR_NEXT_STEP,
        )
    node, assignment, attempt, previous_dispatch_id, staged_child_assignment_id = (
        dispatch_open_inputs
    )
    await open_dispatch_for_attempt(
        session,
        task_id=task_id,
        node=node,
        assignment=assignment,
        attempt=attempt,
        previous_dispatch_id=previous_dispatch_id,
        staged_child_assignment_id=staged_child_assignment_id,
    )
    if previous_dispatch_id is not None:
        stage_previous_dispatch_outputs(
            session,
            task_id=task_id,
            previous_dispatch_id=previous_dispatch_id,
        )
    return True


async def _resolved_previous_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    previous_dispatch: DispatchTurnModel | None,
) -> DispatchTurnModel | None:
    if (
        previous_dispatch is not None
        and previous_dispatch.task_id == task_id
        and previous_dispatch.control_state == "fenced"
        and previous_dispatch.closed_at is not None
        and previous_dispatch.superseded_by_dispatch_id is None
    ):
        return previous_dispatch
    return await latest_unreplaced_fenced_dispatch(session, task_id=task_id)


__all__ = ["auto_open_next_running_dispatch"]
