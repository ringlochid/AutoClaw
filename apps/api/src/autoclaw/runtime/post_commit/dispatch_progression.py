from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.command_run.continuation import (
    command_run_terminal_continuation_matches_current_target,
)
from autoclaw.runtime.contracts import FlowStatus
from autoclaw.runtime.dispatch.control import (
    open_dispatch_for_attempt,
    stage_previous_dispatch_outputs,
)
from autoclaw.runtime.dispatch.launch_retry import (
    LaunchRetryCandidate,
    active_launch_retry_candidate_for_current_target,
    dispatch_is_pre_send_launch_failure,
    launch_retry_attempts_remaining,
    launch_retry_due,
    launch_retry_scheduled,
)
from autoclaw.runtime.errors import illegal_state_error
from autoclaw.runtime.flow.reads import latest_fenced_dispatch
from autoclaw.runtime.flow.resume import resolve_flow_resume_target
from autoclaw.runtime.human_request.continuation import (
    human_request_terminal_continuation_matches_current_target,
)

SEMANTIC_TARGET_INCOMPLETE_SUMMARY = "current semantic target is incomplete"
SEMANTIC_TARGET_REPAIR_NEXT_STEP = (
    "Inspect the current node assignment and attempt currentness, then repair the "
    "incomplete semantic target before continuing this task."
)


@dataclass(frozen=True, slots=True)
class DispatchAutoOpenResult:
    has_changed_runtime_truth: bool = False
    has_scheduled_launch_retry: bool = False


async def auto_open_next_running_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> DispatchAutoOpenResult:
    if flow.status != FlowStatus.RUNNING.value or flow.current_open_dispatch_id is not None:
        return DispatchAutoOpenResult()
    launch_retry_candidate = await active_launch_retry_candidate_for_current_target(
        session,
        flow=flow,
    )
    if launch_retry_candidate is not None:
        return await _auto_open_launch_retry_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            retry_candidate=launch_retry_candidate,
        )
    resolved_previous_dispatch = await _resolved_previous_dispatch(
        session,
        task_id=task_id,
        previous_dispatch=previous_dispatch,
    )
    if resolved_previous_dispatch is None:
        return DispatchAutoOpenResult()
    if (
        resolved_previous_dispatch.accepted_boundary is None
        and not await command_run_terminal_continuation_matches_current_target(
            session,
            task_id=task_id,
            flow=flow,
            previous_dispatch=resolved_previous_dispatch,
        )
        and not await human_request_terminal_continuation_matches_current_target(
            session,
            task_id=task_id,
            flow=flow,
            previous_dispatch=resolved_previous_dispatch,
        )
    ):
        return DispatchAutoOpenResult()
    await _open_dispatch_from_semantic_source(
        session,
        task_id=task_id,
        flow=flow,
        semantic_source_dispatch=resolved_previous_dispatch,
    )
    return DispatchAutoOpenResult(has_changed_runtime_truth=True)


async def _auto_open_launch_retry_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    retry_candidate: LaunchRetryCandidate,
) -> DispatchAutoOpenResult:
    failed_dispatch = retry_candidate.failed_dispatch
    if not launch_retry_attempts_remaining(failed_dispatch):
        return DispatchAutoOpenResult()
    if launch_retry_scheduled(failed_dispatch):
        return DispatchAutoOpenResult(has_scheduled_launch_retry=True)
    if not launch_retry_due(failed_dispatch):
        return DispatchAutoOpenResult(has_scheduled_launch_retry=True)
    await _open_dispatch_from_semantic_source(
        session,
        task_id=task_id,
        flow=flow,
        semantic_source_dispatch=retry_candidate.semantic_source_dispatch,
    )
    return DispatchAutoOpenResult(has_changed_runtime_truth=True)


async def _open_dispatch_from_semantic_source(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    semantic_source_dispatch: DispatchTurnModel | None,
) -> None:
    resume_target = await resolve_flow_resume_target(
        session,
        flow=flow,
        previous_dispatch=semantic_source_dispatch,
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
    ):
        return await _semantic_source_dispatch(session, previous_dispatch)
    latest_dispatch = await latest_fenced_dispatch(session, task_id=task_id)
    return await _semantic_source_dispatch(session, latest_dispatch)


async def _semantic_source_dispatch(
    session: AsyncSession,
    dispatch: DispatchTurnModel | None,
) -> DispatchTurnModel | None:
    if not dispatch_is_pre_send_launch_failure(dispatch):
        return dispatch
    assert dispatch is not None
    if dispatch.previous_dispatch_id is None:
        return None
    return await session.get(DispatchTurnModel, dispatch.previous_dispatch_id)


__all__ = ["DispatchAutoOpenResult", "auto_open_next_running_dispatch"]
