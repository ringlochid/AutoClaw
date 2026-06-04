from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.models import DispatchDeliveryStateModel, DispatchTurnModel
from autoclaw.integrations.openclaw.gateway import OpenClawWaitResult
from autoclaw.runtime.control.clock import utc_now
from autoclaw.runtime.control.dispatch.provider_events import append_provider_event
from autoclaw.runtime.control.failures import illegal_state_error

OPENCLAW_GATEWAY_TRANSPORT_FAMILY = "openclaw_gateway_ws_rpc"


async def record_gateway_wait_terminal(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    wait_result: OpenClawWaitResult,
) -> None:
    terminal_at = wait_result.ended_at
    if wait_result.status.value == "ok":
        dispatch.delivery_status = "provider_completed"
        event_kind = "response_completed"
        summary = "Gateway wait confirmed terminal completion for the current dispatch run."
        detail = "Foreground lifecycle confirmed the run is inactive."
        provider_error = None
    else:
        dispatch.delivery_status = "provider_failed"
        event_kind = "response_failed"
        summary = "Gateway wait confirmed terminal failure for the current dispatch run."
        provider_error = None if wait_result.error is None else wait_result.error.message
        detail = provider_error or "Foreground lifecycle confirmed the run failed."
    event_payload: dict[str, object] = {"wait_status": wait_result.status.value}
    if wait_result.gateway_status is not None:
        event_payload["gateway_status"] = wait_result.gateway_status
    if wait_result.stop_reason is not None:
        event_payload["stop_reason"] = wait_result.stop_reason
    if wait_result.liveness_state is not None:
        event_payload["liveness_state"] = wait_result.liveness_state
    if wait_result.aborted is not None:
        event_payload["aborted"] = wait_result.aborted
    if wait_result.yielded is not None:
        event_payload["yielded"] = wait_result.yielded
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = dispatch.delivery_status
        delivery_state.last_provider_event_kind = event_kind
        delivery_state.provider_final_status = wait_result.status.value
        delivery_state.provider_error = provider_error
        delivery_state.last_provider_signal_at = terminal_at
        delivery_state.updated_at = terminal_at
    await append_gateway_event(
        session,
        dispatch=dispatch,
        event_kind=event_kind,
        summary=summary,
        detail=detail,
        provider_event_name="agent.wait",
        provider_occurred_at=terminal_at,
        gateway_run_id=dispatch.gateway_run_id,
        **event_payload,
    )


async def record_gateway_wait_timeout(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    detail: str,
) -> None:
    observed_at = utc_now()
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.last_provider_event_kind = "transport_timeout"
        delivery_state.provider_error = detail
        delivery_state.updated_at = observed_at
    await append_gateway_event(
        session,
        dispatch=dispatch,
        event_kind="transport_timeout",
        summary="Gateway wait timed out before the controller could prove inactivity.",
        detail=detail,
        provider_event_name="agent.wait",
        gateway_run_id=dispatch.gateway_run_id,
    )


async def record_gateway_transport_failure(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    operation: str,
    error: Exception,
) -> bool:
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    detail = f"{operation}:{type(error).__name__}:{error}"
    if delivery_state is not None and delivery_state.provider_error == detail:
        return False
    observed_at = utc_now()
    if delivery_state is not None:
        delivery_state.last_provider_event_kind = "transport_failed"
        delivery_state.provider_error = detail
        delivery_state.updated_at = observed_at
    await append_gateway_event(
        session,
        dispatch=dispatch,
        event_kind="transport_failed",
        summary=f"Gateway {operation} failed before inactivity could be proven.",
        detail=detail,
        provider_event_name=operation,
        gateway_run_id=dispatch.gateway_run_id,
        error_type=type(error).__name__,
    )
    return True


async def append_gateway_event(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    event_kind: str,
    summary: str,
    detail: str,
    provider_event_name: str,
    provider_occurred_at: datetime | None = None,
    **payload: object,
) -> None:
    await append_provider_event(
        session,
        dispatch=dispatch,
        attempt_id=_dispatch_attempt_id(dispatch),
        event_source="adapter",
        event_kind=event_kind,
        summary=summary,
        detail=detail,
        provider_event_name=provider_event_name,
        provider_occurred_at=provider_occurred_at,
        event_payload_json={"transport_family": OPENCLAW_GATEWAY_TRANSPORT_FAMILY, **payload},
    )


def _dispatch_attempt_id(dispatch: DispatchTurnModel) -> str:
    if dispatch.attempt_id is None:
        raise illegal_state_error("dispatch transport normalization requires attempt ownership")
    return dispatch.attempt_id


__all__ = [
    "OPENCLAW_GATEWAY_TRANSPORT_FAMILY",
    "append_gateway_event",
    "record_gateway_transport_failure",
    "record_gateway_wait_terminal",
    "record_gateway_wait_timeout",
]
