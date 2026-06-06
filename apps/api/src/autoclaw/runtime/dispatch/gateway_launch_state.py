from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.integrations.openclaw.gateway import OpenClawLaunchResult
from autoclaw.persistence.models import (
    AssignmentModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.dispatch.gateway import (
    OPENCLAW_GATEWAY_TRANSPORT_FAMILY,
    AcceptedGatewayRunCleanupResult,
    abort_gateway_run_with_fallback,
    cleanup_accepted_gateway_run,
)
from autoclaw.runtime.dispatch.openclaw.models import OpenClawDispatchLaunchLease
from autoclaw.runtime.dispatch.provider_events import append_provider_event
from autoclaw.runtime.errors import illegal_state_error


@dataclass(frozen=True)
class GatewayDispatchContext:
    task_id: str
    flow: FlowModel
    dispatch: DispatchTurnModel
    assignment: AssignmentModel
    attempt: AttemptModel


async def record_gateway_dispatch_acceptance(
    session: AsyncSession,
    *,
    context: GatewayDispatchContext,
    launch_result: OpenClawLaunchResult,
    prompt_path: str,
    content_hash: str,
) -> None:
    dispatch = context.dispatch
    accepted_at = launch_result.accepted_at
    if dispatch.flow_node_id is None:
        raise illegal_state_error("gateway launch acceptance requires a persisted flow_node_id")
    dispatch.gateway_session_key = launch_result.session_key
    dispatch.gateway_run_id = launch_result.run_id
    dispatch.prompt_path = prompt_path
    dispatch.content_hash = content_hash
    dispatch.delivery_status = "accepted"
    dispatch.control_state, dispatch.control_state_reason = "live", "launch_confirmed"
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_family = OPENCLAW_GATEWAY_TRANSPORT_FAMILY
        delivery_state.transport_state = "accepted"
        delivery_state.accepted_at = accepted_at
        delivery_state.updated_at = accepted_at
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch.dispatch_id)
    if continuity_state is not None:
        continuity_state.session_key_present = True
        continuity_state.updated_at = accepted_at
    rows = await session.scalars(
        select(NodeSessionModel).where(
            NodeSessionModel.assignment_id == context.assignment.assignment_id,
            NodeSessionModel.closed_at.is_(None),
            NodeSessionModel.dispatch_id != dispatch.dispatch_id,
        )
    )
    closed_at = utc_now()
    superseded_dispatch_ids: set[str] = set()
    for row in rows:
        row.closed_at = closed_at
        row.session_status = "superseded"
        if row.dispatch_id is not None:
            superseded_dispatch_ids.add(row.dispatch_id)
    await _invalidate_superseded_dispatch_continuity(
        session,
        dispatch_ids=superseded_dispatch_ids,
        replacement_dispatch_id=dispatch.dispatch_id,
        invalidated_at=accepted_at,
    )
    session.add(
        NodeSessionModel(
            node_session_id=f"node-session.{dispatch.dispatch_id}",
            flow_node_id=dispatch.flow_node_id,
            assignment_id=context.assignment.assignment_id,
            attempt_id=context.attempt.attempt_id,
            dispatch_id=dispatch.dispatch_id,
            session_key=launch_result.session_key,
            session_status="live",
            opened_at=accepted_at,
        )
    )
    await append_dispatch_event(
        session,
        dispatch=dispatch,
        attempt_id=context.attempt.attempt_id,
        event_kind="accepted",
        summary="Dispatch accepted and waiting for provider or adapter progress.",
        detail=f"Dispatch opened for node '{dispatch.node_key}'.",
    )
    context.flow.current_open_dispatch_id = dispatch.dispatch_id
    context.flow.updated_at = accepted_at


async def record_gateway_dispatch_post_send_failure(
    session: AsyncSession,
    *,
    context: GatewayDispatchContext,
    session_key: str,
    lease: OpenClawDispatchLaunchLease | None,
    error: Exception,
) -> None:
    observed_at = utc_now()
    reason = f"gateway_launch_post_send_failed:{type(error).__name__}"
    try:
        await abort_gateway_run_with_fallback(
            session_key=session_key,
            run_id=None,
            handle=None if lease is None else lease.handle,
        )
        abort_detail = None
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        abort_detail = f"sessions.abort:{type(exc).__name__}:{exc}"
    detail = f"agent:post_send:{type(error).__name__}:{error}"
    if abort_detail is not None:
        detail = f"{detail};{abort_detail}"
    dispatch = context.dispatch
    dispatch.gateway_session_key = session_key
    dispatch.gateway_run_id = None
    dispatch.delivery_status = "transport_ambiguous"
    dispatch.control_state, dispatch.control_state_reason = "ambiguous", reason
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_family = OPENCLAW_GATEWAY_TRANSPORT_FAMILY
        delivery_state.transport_state = "transport_ambiguous"
        delivery_state.last_provider_event_kind = "transport_failed"
        delivery_state.provider_error = detail
        if abort_detail is None:
            delivery_state.last_controller_progress_at = observed_at
        delivery_state.last_controller_terminal_at = observed_at
        delivery_state.updated_at = observed_at
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch.dispatch_id)
    if continuity_state is not None:
        continuity_state.session_key_present = True
        continuity_state.invalidation_reason = reason
        continuity_state.updated_at = observed_at
    await append_dispatch_event(
        session,
        dispatch=dispatch,
        attempt_id=context.attempt.attempt_id,
        event_kind="transport_failed",
        summary="OpenClaw dispatch launch became ambiguous after the agent request was sent.",
        detail=detail,
        event_payload_json=_transport_payload(
            launch_phase="post_send",
            cleanup_abort_error=abort_detail,
        ),
    )
    if abort_detail is None:
        await append_dispatch_event(
            session,
            dispatch=dispatch,
            attempt_id=context.attempt.attempt_id,
            event_kind="tool_event",
            summary="Gateway abort requested after post-send launch ambiguity.",
            detail=(
                "Controller requested `sessions.abort` by session key because acceptance could "
                "not be normalized."
            ),
            provider_event_name="sessions.abort",
            event_payload_json=_transport_payload(gateway_session_key=session_key),
        )
    context.flow.updated_at = observed_at


async def record_gateway_dispatch_launch_failure(
    session: AsyncSession,
    *,
    context: GatewayDispatchContext,
    error: Exception,
) -> None:
    failed_at = utc_now()
    reason = f"gateway_launch_failed:{type(error).__name__}"
    dispatch = context.dispatch
    dispatch.delivery_status = "transport_failed"
    dispatch.control_state, dispatch.control_state_reason = "fenced", reason
    dispatch.fenced_at = dispatch.closed_at = failed_at
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_family = OPENCLAW_GATEWAY_TRANSPORT_FAMILY
        delivery_state.transport_state = "transport_failed"
        delivery_state.provider_error = str(error)
        delivery_state.last_controller_terminal_at = failed_at
        delivery_state.updated_at = failed_at
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch.dispatch_id)
    if continuity_state is not None:
        continuity_state.invalidation_reason = reason
        continuity_state.updated_at = failed_at
    await append_dispatch_event(
        session,
        dispatch=dispatch,
        attempt_id=context.attempt.attempt_id,
        event_kind="transport_failed",
        summary="OpenClaw dispatch launch failed before acceptance.",
        detail=str(error),
        event_payload_json=_transport_payload(error_type=type(error).__name__),
    )
    if context.flow.current_open_dispatch_id == dispatch.dispatch_id:
        context.flow.current_open_dispatch_id = None
    context.flow.updated_at = failed_at


async def record_gateway_dispatch_post_acceptance_failure(
    session: AsyncSession,
    *,
    flow_id: str,
    dispatch_id: str,
    attempt_id: str,
    launch_result: OpenClawLaunchResult,
    prompt_path: str,
    content_hash: str,
    lease: OpenClawDispatchLaunchLease,
    error: Exception,
) -> None:
    cleanup_result = await cleanup_accepted_gateway_run(launch_result, lease=lease)
    await session.rollback()
    dispatch = await _restore_post_acceptance_cleanup_state(
        session,
        flow_id=flow_id,
        dispatch_id=dispatch_id,
        launch_result=launch_result,
        prompt_path=prompt_path,
        content_hash=content_hash,
        cleanup_result=cleanup_result,
        reason_prefix=f"gateway_acceptance_persist_failed:{type(error).__name__}",
    )
    await append_dispatch_event(
        session,
        dispatch=dispatch,
        attempt_id=attempt_id,
        event_kind="accepted",
        summary="Dispatch was accepted remotely before local acceptance persistence failed.",
        detail=(
            "The controller is recording remote acceptance during cleanup after local "
            "persistence failed."
        ),
        provider_occurred_at=launch_result.accepted_at,
    )
    if cleanup_result.is_abort_requested:
        await append_dispatch_event(
            session,
            dispatch=dispatch,
            attempt_id=attempt_id,
            event_kind="tool_event",
            summary="Gateway abort requested during post-acceptance cleanup.",
            detail=(
                "Controller requested `sessions.abort` for the accepted run after local "
                "persistence failed."
            ),
            provider_event_name="sessions.abort",
            event_payload_json=_transport_payload(gateway_run_id=launch_result.run_id),
        )
    await append_dispatch_event(
        session,
        dispatch=dispatch,
        attempt_id=attempt_id,
        event_kind=cleanup_result.event_kind,
        summary=cleanup_result.summary,
        detail=cleanup_result.detail,
        provider_event_name="agent.wait" if cleanup_result.is_abort_requested else "sessions.abort",
        provider_occurred_at=cleanup_result.observed_at,
        event_payload_json=_transport_payload(
            gateway_run_id=launch_result.run_id,
            cleanup_delivery_status=dispatch.delivery_status,
        ),
    )
    await session.flush()


async def append_dispatch_event(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    attempt_id: str,
    event_kind: str,
    summary: str,
    detail: str,
    provider_event_name: str | None = None,
    provider_occurred_at: datetime | None = None,
    event_payload_json: dict[str, object] | None = None,
) -> None:
    await append_provider_event(
        session,
        dispatch=dispatch,
        attempt_id=attempt_id,
        event_source="adapter",
        event_kind=event_kind,
        summary=summary,
        detail=detail,
        provider_event_name=provider_event_name,
        provider_occurred_at=provider_occurred_at,
        event_payload_json=event_payload_json,
    )


async def _restore_post_acceptance_cleanup_state(
    session: AsyncSession,
    *,
    flow_id: str,
    dispatch_id: str,
    launch_result: OpenClawLaunchResult,
    prompt_path: str,
    content_hash: str,
    cleanup_result: AcceptedGatewayRunCleanupResult,
    reason_prefix: str,
) -> DispatchTurnModel:
    flow = await session.get(FlowModel, flow_id)
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    if flow is None or dispatch is None:
        raise illegal_state_error(
            "gateway post-acceptance cleanup requires persisted flow and dispatch state"
        )
    dispatch.gateway_session_key = launch_result.session_key
    dispatch.gateway_run_id = launch_result.run_id
    dispatch.prompt_path = prompt_path
    dispatch.content_hash = content_hash
    if cleanup_result.is_terminal:
        dispatch.delivery_status = cleanup_result.delivery_status
        dispatch.control_state = "fenced"
        dispatch.control_state_reason = f"{reason_prefix}:cleanup_fenced"
        dispatch.closed_at = cleanup_result.observed_at
        dispatch.fenced_at = cleanup_result.observed_at
        flow.current_open_dispatch_id = None
    else:
        dispatch.delivery_status = "transport_ambiguous"
        dispatch.control_state = "ambiguous"
        dispatch.control_state_reason = f"{reason_prefix}:cleanup_ambiguous"
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_family = OPENCLAW_GATEWAY_TRANSPORT_FAMILY
        delivery_state.transport_state = dispatch.delivery_status
        delivery_state.accepted_at = launch_result.accepted_at
        delivery_state.last_provider_event_kind = cleanup_result.event_kind
        delivery_state.provider_final_status = cleanup_result.provider_final_status
        delivery_state.provider_error = cleanup_result.provider_error
        if cleanup_result.is_abort_requested:
            delivery_state.last_controller_progress_at = cleanup_result.observed_at
        delivery_state.last_controller_terminal_at = cleanup_result.observed_at
        delivery_state.updated_at = cleanup_result.observed_at
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
    if continuity_state is not None:
        continuity_state.session_key_present = True
        continuity_state.invalidation_reason = reason_prefix
        continuity_state.updated_at = cleanup_result.observed_at
    flow.updated_at = cleanup_result.observed_at
    return dispatch


async def _invalidate_superseded_dispatch_continuity(
    session: AsyncSession,
    *,
    dispatch_ids: set[str],
    replacement_dispatch_id: str,
    invalidated_at: datetime,
) -> None:
    if not dispatch_ids:
        return

    invalidation_reason = f"superseded:{replacement_dispatch_id}"
    for dispatch_id in dispatch_ids:
        continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
        if continuity_state is None:
            continue
        continuity_state.session_key_present = False
        continuity_state.invalidation_reason = invalidation_reason
        continuity_state.updated_at = invalidated_at


def _transport_payload(**extra: object) -> dict[str, object]:
    return {"transport_family": OPENCLAW_GATEWAY_TRANSPORT_FAMILY, **extra}


__all__ = [
    "GatewayDispatchContext",
    "record_gateway_dispatch_acceptance",
    "record_gateway_dispatch_launch_failure",
    "record_gateway_dispatch_post_acceptance_failure",
    "record_gateway_dispatch_post_send_failure",
]
