from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel, FlowModel, PendingHumanRequestModel
from autoclaw.runtime.contracts import HumanRequestRead, HumanRequestStatus
from autoclaw.runtime.human_request.records import human_request_read_from_model

_SEMANTIC_TARGET_INCOMPLETE_SUMMARY = "current semantic target is incomplete"
_SEMANTIC_TARGET_REPAIR_NEXT_STEP = (
    "Inspect the current node assignment and attempt currentness, then repair the "
    "incomplete semantic target before continuing this task."
)


async def human_request_continuation_context_for_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    previous_dispatch_id: str | None,
) -> HumanRequestRead | None:
    if previous_dispatch_id is None:
        return None

    pending_request = await terminal_human_request_for_dispatch(
        session,
        task_id=task_id,
        dispatch_id=previous_dispatch_id,
    )
    if pending_request is None:
        return None

    return human_request_read_from_model(pending_request)


async def human_request_terminal_continuation_matches_current_target(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel,
) -> bool:
    from autoclaw.runtime.flow.queries import current_semantic_flow_target

    pending_request = await terminal_human_request_for_dispatch(
        session,
        task_id=task_id,
        dispatch_id=previous_dispatch.dispatch_id,
    )
    if pending_request is None:
        return False
    if (
        pending_request.flow_id != flow.flow_id
        or pending_request.flow_revision_id != flow.active_flow_revision_id
    ):
        return False

    semantic_target = await current_semantic_flow_target(
        session,
        flow=flow,
        incomplete_summary=_SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
        suggested_next_step=_SEMANTIC_TARGET_REPAIR_NEXT_STEP,
    )
    if semantic_target is None:
        return False

    return (
        pending_request.flow_node_id == semantic_target.node.flow_node_id
        and pending_request.assignment_id == semantic_target.assignment.assignment_id
        and pending_request.attempt_id == semantic_target.attempt.attempt_id
    )


async def terminal_human_request_for_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> PendingHumanRequestModel | None:
    terminal_statuses = (
        HumanRequestStatus.RESOLVED.value,
        HumanRequestStatus.TIMED_OUT.value,
        HumanRequestStatus.CANCELLED.value,
    )
    return cast(
        PendingHumanRequestModel | None,
        await session.scalar(
            select(PendingHumanRequestModel)
            .where(
                PendingHumanRequestModel.task_id == task_id,
                PendingHumanRequestModel.dispatch_id == dispatch_id,
                PendingHumanRequestModel.status.in_(terminal_statuses),
                PendingHumanRequestModel.resolved_at.is_not(None),
            )
            .order_by(
                PendingHumanRequestModel.resolved_at.desc(),
                PendingHumanRequestModel.updated_at.desc(),
                PendingHumanRequestModel.request_id.desc(),
            )
            .limit(1)
        ),
    )


__all__ = [
    "human_request_continuation_context_for_dispatch",
    "human_request_terminal_continuation_matches_current_target",
    "terminal_human_request_for_dispatch",
]
