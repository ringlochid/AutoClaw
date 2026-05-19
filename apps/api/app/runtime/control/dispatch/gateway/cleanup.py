from __future__ import annotations

from datetime import datetime

from app.config import get_settings
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch.gateway.abort import abort_gateway_run
from app.runtime.control.dispatch.gateway.contracts import CleanupState
from app.runtime.control.dispatch.gateway.wait import wait_for_gateway_run
from app.runtime.control.dispatch.openclaw_runtime import OpenClawDispatchLaunchLease
from app.runtime.openclaw import OpenClawLaunchResult


async def cleanup_accepted_gateway_run(
    launch_result: OpenClawLaunchResult,
    *,
    lease: OpenClawDispatchLaunchLease | None = None,
) -> CleanupState:
    del lease
    abort_state = await request_cleanup_abort(launch_result)
    if abort_state is not None:
        return abort_state
    wait_state, terminal_at = await wait_for_cleanup_terminal_state(launch_result)
    if wait_state is not None:
        return wait_state
    return (
        True,
        True,
        "provider_completed",
        "response_completed",
        "Gateway cleanup confirmed the accepted run is inactive.",
        "Controller aborted the accepted run and `agent.wait` confirmed it is inactive.",
        terminal_at,
        None,
        None,
    )


async def request_cleanup_abort(launch_result: OpenClawLaunchResult) -> CleanupState | None:
    try:
        await abort_gateway_run(
            session_key=launch_result.session_key,
            run_id=launch_result.run_id,
        )
    except Exception as exc:
        return ambiguous_cleanup_state(
            abort_requested=False,
            event_kind="transport_failed",
            summary="Gateway abort failed during post-acceptance cleanup.",
            detail=f"sessions.abort:{type(exc).__name__}:{exc}",
            observed_at=utc_now(),
        )
    return None


async def wait_for_cleanup_terminal_state(
    launch_result: OpenClawLaunchResult,
) -> tuple[CleanupState | None, datetime]:
    try:
        wait_result = await wait_for_gateway_run(
            run_id=launch_result.run_id,
            timeout_ms=get_settings().openclaw.timeout_ms,
        )
    except Exception as exc:
        observed_at = utc_now()
        return (
            ambiguous_cleanup_state(
                abort_requested=True,
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
                abort_requested=True,
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
        (
            True,
            True,
            "provider_failed",
            "response_failed",
            "Gateway cleanup confirmed terminal failure for the accepted run.",
            provider_error
            or "Controller aborted the accepted run and `agent.wait` reported failure.",
            wait_result.ended_at,
            wait_result.status.value,
            provider_error,
        ),
        wait_result.ended_at,
    )


def ambiguous_cleanup_state(
    *,
    abort_requested: bool,
    event_kind: str,
    summary: str,
    detail: str,
    observed_at: datetime,
) -> CleanupState:
    return (
        abort_requested,
        False,
        "transport_ambiguous",
        event_kind,
        summary,
        detail,
        observed_at,
        None,
        detail,
    )
