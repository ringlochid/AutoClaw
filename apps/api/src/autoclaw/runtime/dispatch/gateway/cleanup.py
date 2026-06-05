from __future__ import annotations

from datetime import datetime

from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import OpenClawLaunchResult
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.dispatch.gateway.abort import abort_gateway_run_with_fallback
from autoclaw.runtime.dispatch.gateway.contracts import AcceptedGatewayRunCleanupResult
from autoclaw.runtime.dispatch.gateway.wait import wait_for_gateway_run_with_fallback
from autoclaw.runtime.dispatch.openclaw.models import OpenClawDispatchLaunchLease


async def cleanup_accepted_gateway_run(
    launch_result: OpenClawLaunchResult,
    *,
    lease: OpenClawDispatchLaunchLease | None = None,
) -> AcceptedGatewayRunCleanupResult:
    abort_state = await request_cleanup_abort(launch_result, lease=lease)
    if abort_state is not None:
        return abort_state
    wait_state, terminal_at = await wait_for_cleanup_terminal_state(launch_result, lease=lease)
    if wait_state is not None:
        return wait_state
    return AcceptedGatewayRunCleanupResult(
        is_abort_requested=True,
        is_terminal=True,
        delivery_status="provider_completed",
        event_kind="response_completed",
        summary="Gateway cleanup confirmed the accepted run is inactive.",
        detail="Controller aborted the accepted run and `agent.wait` confirmed it is inactive.",
        observed_at=terminal_at,
    )


async def request_cleanup_abort(
    launch_result: OpenClawLaunchResult,
    lease: OpenClawDispatchLaunchLease | None = None,
) -> AcceptedGatewayRunCleanupResult | None:
    try:
        await abort_gateway_run_with_fallback(
            session_key=launch_result.session_key,
            run_id=launch_result.run_id,
            handle=None if lease is None else lease.handle,
        )
    except Exception as exc:
        return ambiguous_cleanup_state(
            is_abort_requested=False,
            event_kind="transport_failed",
            summary="Gateway abort failed during post-acceptance cleanup.",
            detail=f"sessions.abort:{type(exc).__name__}:{exc}",
            observed_at=utc_now(),
        )
    return None


async def wait_for_cleanup_terminal_state(
    launch_result: OpenClawLaunchResult,
    lease: OpenClawDispatchLaunchLease | None = None,
) -> tuple[AcceptedGatewayRunCleanupResult | None, datetime]:
    try:
        wait_result = await wait_for_gateway_run_with_fallback(
            run_id=launch_result.run_id,
            timeout_ms=get_settings().openclaw.timeout_ms,
            handle=None if lease is None else lease.handle,
        )
    except Exception as exc:
        observed_at = utc_now()
        return (
            ambiguous_cleanup_state(
                is_abort_requested=True,
                event_kind="transport_failed",
                summary="Gateway wait failed during post-acceptance cleanup.",
                detail=f"agent.wait:{type(exc).__name__}:{exc}",
                observed_at=observed_at,
            ),
            observed_at,
        )
    if wait_result.status.value == "timeout":
        return (
            ambiguous_cleanup_state(
                is_abort_requested=True,
                event_kind="transport_timeout",
                summary="Gateway wait timed out during post-acceptance cleanup.",
                detail="Gateway wait timed out during post-acceptance cleanup.",
                observed_at=wait_result.ended_at,
            ),
            wait_result.ended_at,
        )
    if wait_result.status.value == "ok":
        return None, wait_result.ended_at
    provider_error = None if wait_result.error is None else wait_result.error.message
    return (
        AcceptedGatewayRunCleanupResult(
            is_abort_requested=True,
            is_terminal=True,
            delivery_status="provider_failed",
            event_kind="response_failed",
            summary="Gateway cleanup confirmed terminal failure for the accepted run.",
            detail=provider_error
            or "Controller aborted the accepted run and `agent.wait` reported failure.",
            observed_at=wait_result.ended_at,
            provider_final_status=wait_result.status.value,
            provider_error=provider_error,
        ),
        wait_result.ended_at,
    )


def ambiguous_cleanup_state(
    *,
    is_abort_requested: bool,
    event_kind: str,
    summary: str,
    detail: str,
    observed_at: datetime,
) -> AcceptedGatewayRunCleanupResult:
    return AcceptedGatewayRunCleanupResult(
        is_abort_requested=is_abort_requested,
        is_terminal=False,
        delivery_status="transport_ambiguous",
        event_kind=event_kind,
        summary=summary,
        detail=detail,
        observed_at=observed_at,
        provider_error=detail,
    )
