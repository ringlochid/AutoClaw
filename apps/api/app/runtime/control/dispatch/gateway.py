from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import DispatchDeliveryStateModel, DispatchTurnModel
from app.runtime.contract_models.prompt import PromptFamily
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch.gateway_observability import (
    OPENCLAW_GATEWAY_TRANSPORT_FAMILY,
    append_gateway_event,
    record_gateway_transport_failure,
    record_gateway_wait_terminal,
    record_gateway_wait_timeout,
)
from app.runtime.control.failures import illegal_state_error
from app.runtime.openclaw import (
    OpenClawAbortRequest,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawLaunchRequest,
    OpenClawLaunchResult,
    OpenClawWaitRequest,
    OpenClawWaitResult,
    build_openclaw_gateway_adapter,
)
from app.runtime.openclaw.protocol import OpenClawAgentAcceptedPayload, parse_response_payload
from app.runtime.openclaw.request_builders import (
    OpenClawGatewayRequest,
    agent_scoped_openclaw_session_key,
    build_openclaw_agent_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from app.runtime.projection.dispatch.prompt import build_dispatch_prompt

CleanupState = tuple[bool, bool, str, str, str, str, datetime, str | None, str | None]


@dataclass(frozen=True)
class GatewayDispatchLaunchError(Exception):
    error: Exception
    request_sent: bool
    session_key: str

    def __str__(self) -> str:
        return str(self.error)


async def perform_gateway_dispatch_launch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    assignment_key: str,
    attempt_id: str,
) -> tuple[OpenClawLaunchResult, str, str]:
    if dispatch.task_id is None:
        raise illegal_state_error("dispatch is missing task ownership")
    gateway_session_key = await resolve_gateway_session_key(session, dispatch=dispatch)
    _bundle, prompt_record = await build_dispatch_prompt(
        session,
        dispatch.task_id,
        dispatch,
        session_key_override=gateway_session_key,
    )
    result = await _launch_gateway_run_with_tracking(
        OpenClawLaunchRequest(
            task_id=dispatch.task_id,
            dispatch_id=dispatch.dispatch_id,
            assignment_key=assignment_key,
            attempt_id=attempt_id,
            node_key=dispatch.node_key,
            session_key=gateway_session_key,
            prompt_name=PromptFamily(dispatch.prompt_name),
            transport_request=prompt_record.transport_request,
            idempotency_key=f"dispatch:{dispatch.dispatch_id}",
        ),
    )
    return result, str(prompt_record.rendered_markdown_path), prompt_record.content_hash


async def abort_gateway_run(
    *,
    session_key: str,
    run_id: str | None,
) -> None:
    adapter = build_openclaw_gateway_adapter()
    await adapter.abort_run(OpenClawAbortRequest(session_key=session_key, run_id=run_id))


async def abort_gateway_dispatch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    if dispatch.gateway_session_key is None:
        raise illegal_state_error("gateway abort requires a persisted session key")
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if (
        dispatch.abort_requested_at is not None
        and delivery_state is not None
        and delivery_state.last_controller_progress_at is not None
        and delivery_state.last_controller_progress_at >= dispatch.abort_requested_at
    ):
        return False
    adapter = build_openclaw_gateway_adapter()
    await adapter.abort_run(
        OpenClawAbortRequest(
            session_key=dispatch.gateway_session_key, run_id=dispatch.gateway_run_id
        )
    )
    recorded_at = utc_now()
    if delivery_state is not None:
        delivery_state.last_controller_progress_at = recorded_at
        delivery_state.updated_at = recorded_at
    await append_gateway_event(
        session,
        dispatch=dispatch,
        event_kind="tool_event",
        summary="Gateway abort accepted for the current dispatch run.",
        detail="Foreground lifecycle requested `sessions.abort` for the current run.",
        provider_event_name="sessions.abort",
        gateway_run_id=dispatch.gateway_run_id,
    )
    return True


async def wait_for_gateway_dispatch(
    *,
    dispatch: DispatchTurnModel,
    timeout_ms: int,
) -> OpenClawWaitResult:
    if dispatch.gateway_run_id is None:
        raise illegal_state_error("gateway wait requires a persisted run id")
    return await wait_for_gateway_run(run_id=dispatch.gateway_run_id, timeout_ms=timeout_ms)


async def wait_for_gateway_run(
    *,
    run_id: str,
    timeout_ms: int,
) -> OpenClawWaitResult:
    adapter = build_openclaw_gateway_adapter()
    return await adapter.wait_for_run(OpenClawWaitRequest(run_id=run_id, timeout_ms=timeout_ms))


async def cleanup_accepted_gateway_run(
    launch_result: OpenClawLaunchResult,
) -> CleanupState:
    def ambiguous(
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

    try:
        await abort_gateway_run(session_key=launch_result.session_key, run_id=launch_result.run_id)
    except Exception as exc:
        return ambiguous(
            abort_requested=False,
            event_kind="transport_failed",
            summary="Gateway abort failed during post-acceptance cleanup.",
            detail=f"sessions.abort:{type(exc).__name__}:{exc}",
            observed_at=utc_now(),
        )
    try:
        wait_result = await wait_for_gateway_run(
            run_id=launch_result.run_id,
            timeout_ms=get_settings().openclaw.timeout_ms,
        )
    except Exception as exc:
        return ambiguous(
            abort_requested=True,
            event_kind="transport_failed",
            summary="Gateway wait failed during post-acceptance cleanup.",
            detail=f"agent.wait:{type(exc).__name__}:{exc}",
            observed_at=utc_now(),
        )
    if wait_result.status.value == "timeout":
        return ambiguous(
            abort_requested=True,
            event_kind="transport_timeout",
            summary="Gateway wait timed out during post-acceptance cleanup.",
            detail="Gateway wait timed out during post-acceptance cleanup.",
            observed_at=wait_result.ended_at,
        )
    if wait_result.status.value == "ok":
        return (
            True,
            True,
            "provider_completed",
            "response_completed",
            "Gateway cleanup confirmed the accepted run is inactive.",
            "Controller aborted the accepted run and `agent.wait` confirmed it is inactive.",
            wait_result.ended_at,
            wait_result.status.value,
            None,
        )
    provider_error = None if wait_result.error is None else wait_result.error.message
    return (
        True,
        True,
        "provider_failed",
        "response_failed",
        "Gateway cleanup confirmed terminal failure for the accepted run.",
        provider_error or "Controller aborted the accepted run and `agent.wait` reported failure.",
        wait_result.ended_at,
        wait_result.status.value,
        provider_error,
    )


def mint_gateway_session_key(dispatch_id: str) -> str:
    base_session_key = f"gateway-session.{dispatch_id}.{token_urlsafe(12)}"
    return agent_scoped_openclaw_session_key(
        base_session_key,
        get_settings().openclaw.agent_id,
    )


async def resolve_gateway_session_key(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str:
    reusable_session_key = await _latest_parent_root_session_key_for_attempt(
        session,
        dispatch=dispatch,
    )
    if reusable_session_key is not None:
        return reusable_session_key
    return mint_gateway_session_key(dispatch.dispatch_id)


async def _latest_parent_root_session_key_for_attempt(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str | None:
    if (
        dispatch.task_id is None
        or dispatch.assignment_id is None
        or dispatch.assignment_key is None
        or dispatch.attempt_id is None
        or dispatch.prompt_name != PromptFamily.PARENT_ROOT_DISPATCH.value
    ):
        return None
    return await session.scalar(
        select(DispatchTurnModel.gateway_session_key)
        .where(
            DispatchTurnModel.task_id == dispatch.task_id,
            DispatchTurnModel.node_key == dispatch.node_key,
            DispatchTurnModel.assignment_id == dispatch.assignment_id,
            DispatchTurnModel.assignment_key == dispatch.assignment_key,
            DispatchTurnModel.attempt_id == dispatch.attempt_id,
            DispatchTurnModel.dispatch_id != dispatch.dispatch_id,
            DispatchTurnModel.gateway_session_key.is_not(None),
            DispatchTurnModel.fenced_at.is_not(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
        .limit(1)
    )


async def _launch_gateway_run_with_tracking(
    request: OpenClawLaunchRequest,
) -> OpenClawLaunchResult:
    settings = get_settings()
    adapter = build_openclaw_gateway_adapter(settings)
    gateway_request = build_openclaw_agent_request(
        config=settings.openclaw,
        request_id=next_openclaw_request_id("agent"),
        launch_request=request,
    )
    request_sent = False
    try:
        async with adapter.gateway_session() as gateway_session:
            _validate_gateway_launch_pre_send_policy(
                gateway_request,
                compatibility=gateway_session.require_compatibility(),
            )
            request_sent = True
            response, observed_events = await gateway_session.send_request(gateway_request)
            accepted = parse_response_payload(response, OpenClawAgentAcceptedPayload)
            return OpenClawLaunchResult(
                session_key=request.session_key,
                run_id=accepted.run_id,
                accepted_at=accepted.accepted_at,
                compatibility=gateway_session.require_compatibility(),
                observed_events=tuple(observed_events),
            )
    except Exception as exc:
        raise GatewayDispatchLaunchError(
            error=exc,
            request_sent=request_sent,
            session_key=request.session_key,
        ) from exc


def _validate_gateway_launch_pre_send_policy(
    gateway_request: OpenClawGatewayRequest,
    *,
    compatibility: OpenClawCompatibilityReport,
) -> None:
    max_payload = compatibility.max_payload
    if max_payload is None:
        return
    serialized_request = serialize_openclaw_gateway_request(gateway_request)
    if len(serialized_request.encode("utf-8")) <= max_payload:
        return
    raise OpenClawCompatibilityError(
        f"OpenClaw request exceeded hello-ok.policy.maxPayload={max_payload}"
    )


__all__ = [
    "OPENCLAW_GATEWAY_TRANSPORT_FAMILY",
    "GatewayDispatchLaunchError",
    "abort_gateway_dispatch",
    "abort_gateway_run",
    "cleanup_accepted_gateway_run",
    "mint_gateway_session_key",
    "perform_gateway_dispatch_launch",
    "record_gateway_transport_failure",
    "record_gateway_wait_terminal",
    "record_gateway_wait_timeout",
    "wait_for_gateway_dispatch",
    "wait_for_gateway_run",
]
