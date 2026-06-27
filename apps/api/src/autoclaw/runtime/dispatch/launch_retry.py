from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import DispatchDeliveryStatus
from autoclaw.runtime.errors import RuntimeOperationError

PRE_SEND_LAUNCH_FAILURE_PHASE = "pre_send"
POST_SEND_LAUNCH_FAILURE_PHASE = "post_send"


@dataclass(frozen=True, slots=True)
class LaunchRetryCandidate:
    failed_dispatch: DispatchTurnModel
    semantic_source_dispatch: DispatchTurnModel | None


def dispatch_is_pre_send_launch_failure(dispatch: DispatchTurnModel | None) -> bool:
    return (
        dispatch is not None
        and dispatch.control_state == "fenced"
        and dispatch.delivery_status == DispatchDeliveryStatus.TRANSPORT_FAILED.value
        and dispatch.gateway_run_id is None
        and dispatch.accepted_boundary is None
        and dispatch.launch_failure_phase == PRE_SEND_LAUNCH_FAILURE_PHASE
        and dispatch.launch_request_sent is False
    )


def launch_retry_attempts_remaining(dispatch: DispatchTurnModel) -> bool:
    return dispatch.launch_retry_count < _dispatch_launch_retry_max_attempts()


def launch_retry_due(dispatch: DispatchTurnModel, *, now: datetime | None = None) -> bool:
    next_retry_at = _coerce_datetime_to_utc(dispatch.next_launch_retry_at)
    return next_retry_at is None or next_retry_at <= (now or utc_now())


def launch_retry_scheduled(dispatch: DispatchTurnModel) -> bool:
    return launch_retry_attempts_remaining(dispatch) and not launch_retry_due(dispatch)


async def active_launch_retry_candidate_for_current_target(
    session: AsyncSession,
    *,
    flow: FlowModel,
) -> LaunchRetryCandidate | None:
    from autoclaw.runtime.flow.queries import current_semantic_flow_target
    from autoclaw.runtime.post_commit.dispatch_progression import (
        SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
        SEMANTIC_TARGET_REPAIR_NEXT_STEP,
    )

    try:
        semantic_target = await current_semantic_flow_target(
            session,
            flow=flow,
            incomplete_summary=SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
            suggested_next_step=SEMANTIC_TARGET_REPAIR_NEXT_STEP,
        )
    except RuntimeOperationError:
        return None
    if semantic_target is None:
        return None

    latest_dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == flow.task_id,
            DispatchTurnModel.node_key == semantic_target.node.node_key,
            DispatchTurnModel.attempt_id == semantic_target.attempt.attempt_id,
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
        .limit(1)
    )
    if not dispatch_is_pre_send_launch_failure(latest_dispatch):
        return None

    semantic_source_dispatch = None
    assert latest_dispatch is not None
    if latest_dispatch.previous_dispatch_id is not None:
        semantic_source_dispatch = await session.get(
            DispatchTurnModel,
            latest_dispatch.previous_dispatch_id,
        )
    return LaunchRetryCandidate(
        failed_dispatch=latest_dispatch,
        semantic_source_dispatch=semantic_source_dispatch,
    )


async def record_pre_send_launch_retry_state(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    error: Exception,
    failed_at: datetime,
) -> None:
    retry_count = await _next_pre_send_launch_retry_count(session, dispatch=dispatch)
    dispatch.launch_retry_count = retry_count
    dispatch.next_launch_retry_at = _next_launch_retry_at(
        failed_at=failed_at,
        retry_count=retry_count,
    )
    dispatch.launch_retry_exhausted_at = (
        failed_at if dispatch.next_launch_retry_at is None else None
    )
    _record_launch_failure_provenance(
        dispatch,
        phase=PRE_SEND_LAUNCH_FAILURE_PHASE,
        request_sent=False,
        error=error,
    )


def record_post_send_launch_failure_provenance(
    dispatch: DispatchTurnModel,
    *,
    error: Exception,
) -> None:
    dispatch.launch_retry_count = 0
    dispatch.next_launch_retry_at = None
    dispatch.launch_retry_exhausted_at = None
    _record_launch_failure_provenance(
        dispatch,
        phase=POST_SEND_LAUNCH_FAILURE_PHASE,
        request_sent=True,
        error=error,
    )


async def _next_pre_send_launch_retry_count(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> int:
    stmt = select(func.max(DispatchTurnModel.launch_retry_count)).where(
        DispatchTurnModel.task_id == dispatch.task_id,
        DispatchTurnModel.node_key == dispatch.node_key,
        DispatchTurnModel.attempt_id == dispatch.attempt_id,
        DispatchTurnModel.dispatch_id != dispatch.dispatch_id,
        DispatchTurnModel.launch_failure_phase == PRE_SEND_LAUNCH_FAILURE_PHASE,
        DispatchTurnModel.launch_request_sent.is_(False),
    )
    if dispatch.previous_dispatch_id is None:
        stmt = stmt.where(DispatchTurnModel.previous_dispatch_id.is_(None))
    else:
        stmt = stmt.where(DispatchTurnModel.previous_dispatch_id == dispatch.previous_dispatch_id)
    previous_retry_count = await session.scalar(stmt)
    return int(previous_retry_count or 0) + 1


def _record_launch_failure_provenance(
    dispatch: DispatchTurnModel,
    *,
    phase: str,
    request_sent: bool,
    error: Exception,
) -> None:
    dispatch.launch_failure_phase = phase
    dispatch.launch_request_sent = request_sent
    dispatch.launch_error_type = type(error).__name__
    dispatch.launch_error_detail = str(error)


def _next_launch_retry_at(
    *,
    failed_at: datetime,
    retry_count: int,
) -> datetime | None:
    if retry_count >= _dispatch_launch_retry_max_attempts():
        return None
    retry_delay_seconds = min(
        _dispatch_launch_retry_max_backoff_seconds(),
        _dispatch_launch_retry_initial_backoff_seconds() * (2 ** max(0, retry_count - 1)),
    )
    return failed_at + timedelta(seconds=retry_delay_seconds)


def _dispatch_launch_retry_max_attempts() -> int:
    return max(1, get_settings().runtime.dispatch_launch_retry_max_attempts)


def _dispatch_launch_retry_initial_backoff_seconds() -> float:
    return max(0.0, get_settings().runtime.dispatch_launch_retry_initial_backoff_seconds)


def _dispatch_launch_retry_max_backoff_seconds() -> float:
    runtime_settings = get_settings().runtime
    return max(
        _dispatch_launch_retry_initial_backoff_seconds(),
        runtime_settings.dispatch_launch_retry_max_backoff_seconds,
    )


def _coerce_datetime_to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "POST_SEND_LAUNCH_FAILURE_PHASE",
    "PRE_SEND_LAUNCH_FAILURE_PHASE",
    "LaunchRetryCandidate",
    "active_launch_retry_candidate_for_current_target",
    "dispatch_is_pre_send_launch_failure",
    "launch_retry_attempts_remaining",
    "launch_retry_due",
    "launch_retry_scheduled",
    "record_post_send_launch_failure_provenance",
    "record_pre_send_launch_retry_state",
]
