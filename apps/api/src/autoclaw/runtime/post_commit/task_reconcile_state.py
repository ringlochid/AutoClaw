from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.persistence.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from autoclaw.runtime.command_run.continuation import (
    command_run_terminal_continuation_matches_current_target,
)
from autoclaw.runtime.contracts import FlowStatus
from autoclaw.runtime.dispatch.launch_retry import (
    active_launch_retry_candidate_for_current_target,
    dispatch_is_pre_send_launch_failure,
    launch_retry_attempts_remaining,
    launch_retry_due,
    launch_retry_scheduled,
)
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.flow.reads import latest_fenced_dispatch
from autoclaw.runtime.flow.resume import resolve_flow_resume_target
from autoclaw.runtime.human_request.continuation import (
    human_request_terminal_continuation_matches_current_target,
)
from autoclaw.runtime.post_commit.dispatch_reconcile import dispatch_requires_lifecycle_reconcile


async def task_pending_reconcile(
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None:
            return False
        if flow.current_open_dispatch_id is None:
            if flow.status != FlowStatus.RUNNING.value:
                return False
            return await task_can_auto_open_dispatch(
                session,
                task_id=task_id,
                flow=flow,
            ) or await task_has_scheduled_launch_retry(session, flow=flow)
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        if dispatch is None:
            return True
        if fenced_current_dispatch_needs_flow_cleanup(flow, dispatch):
            return True
        delivery_state = await session.get(
            DispatchDeliveryStateModel,
            flow.current_open_dispatch_id,
        )
        if dispatch_requires_lifecycle_reconcile(
            dispatch,
            delivery_state=delivery_state,
        ):
            return True
        lingering_boundary_dispatch = await latest_lingering_boundary_dispatch(
            session,
            task_id=task_id,
            current_open_dispatch_id=flow.current_open_dispatch_id,
        )
        if lingering_boundary_dispatch is not None:
            lingering_delivery_state = await session.get(
                DispatchDeliveryStateModel,
                lingering_boundary_dispatch.dispatch_id,
            )
            if dispatch_requires_lifecycle_reconcile(
                lingering_boundary_dispatch,
                delivery_state=lingering_delivery_state,
            ):
                return True
        return False


async def task_can_auto_open_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> bool:
    launch_retry_candidate = await active_launch_retry_candidate_for_current_target(
        session,
        flow=flow,
    )
    if launch_retry_candidate is not None:
        failed_dispatch = launch_retry_candidate.failed_dispatch
        if not launch_retry_attempts_remaining(failed_dispatch) or not launch_retry_due(
            failed_dispatch
        ):
            return False
        return await _dispatch_open_inputs_available(
            session,
            flow=flow,
            previous_dispatch=launch_retry_candidate.semantic_source_dispatch,
        )

    previous_dispatch = await _latest_semantic_continuation_dispatch(
        session,
        task_id=task_id,
    )
    if previous_dispatch is None:
        return False
    try:
        if previous_dispatch.accepted_boundary is None:
            can_continue_from_command_run = (
                await command_run_terminal_continuation_matches_current_target(
                    session,
                    task_id=task_id,
                    flow=flow,
                    previous_dispatch=previous_dispatch,
                )
            )
            can_continue_from_human_request = (
                await human_request_terminal_continuation_matches_current_target(
                    session,
                    task_id=task_id,
                    flow=flow,
                    previous_dispatch=previous_dispatch,
                )
            )
            if not can_continue_from_command_run and not can_continue_from_human_request:
                return False
    except RuntimeOperationError as exc:
        if exc.summary == "current semantic target is incomplete":
            return False
        raise
    return await _dispatch_open_inputs_available(
        session,
        flow=flow,
        previous_dispatch=previous_dispatch,
    )


async def task_has_scheduled_launch_retry(
    session: AsyncSession,
    *,
    flow: FlowModel,
) -> bool:
    launch_retry_candidate = await active_launch_retry_candidate_for_current_target(
        session,
        flow=flow,
    )
    return (
        launch_retry_candidate is not None
        and launch_retry_attempts_remaining(launch_retry_candidate.failed_dispatch)
        and launch_retry_scheduled(launch_retry_candidate.failed_dispatch)
    )


async def runtime_predicate_value(
    predicate: Callable[[], bool | Awaitable[bool]],
) -> bool:
    value = predicate()
    if isinstance(value, bool):
        return value
    return bool(await value)


def fenced_current_dispatch_needs_flow_cleanup(
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> bool:
    return (
        flow.current_open_dispatch_id == dispatch.dispatch_id and dispatch.control_state == "fenced"
    )


async def latest_lingering_boundary_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    current_open_dispatch_id: str | None,
) -> DispatchTurnModel | None:
    return cast(
        DispatchTurnModel | None,
        await session.scalar(
            select(DispatchTurnModel)
            .where(
                DispatchTurnModel.task_id == task_id,
                DispatchTurnModel.dispatch_id != (current_open_dispatch_id or ""),
                DispatchTurnModel.accepted_boundary.is_not(None),
                DispatchTurnModel.closed_at.is_not(None),
                DispatchTurnModel.fenced_at.is_(None),
                DispatchTurnModel.control_state.not_in(("fenced", "ambiguous")),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


async def _dispatch_open_inputs_available(
    session: AsyncSession,
    *,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> bool:
    try:
        resume_target = await resolve_flow_resume_target(
            session,
            flow=flow,
            previous_dispatch=previous_dispatch,
        )
    except RuntimeOperationError as exc:
        if exc.summary == "current semantic target is incomplete":
            return False
        raise
    return resume_target.dispatch_open_inputs() is not None


async def _latest_semantic_continuation_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchTurnModel | None:
    latest_dispatch = await latest_fenced_dispatch(session, task_id=task_id)
    if not dispatch_is_pre_send_launch_failure(latest_dispatch):
        return latest_dispatch
    assert latest_dispatch is not None
    if latest_dispatch.previous_dispatch_id is None:
        return None
    return await session.get(DispatchTurnModel, latest_dispatch.previous_dispatch_id)


__all__ = [
    "fenced_current_dispatch_needs_flow_cleanup",
    "latest_lingering_boundary_dispatch",
    "runtime_predicate_value",
    "task_can_auto_open_dispatch",
    "task_has_scheduled_launch_retry",
    "task_pending_reconcile",
]
