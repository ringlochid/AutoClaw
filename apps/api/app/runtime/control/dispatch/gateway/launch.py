from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import DispatchTurnModel
from app.runtime.contract_models.prompt import PromptFamily
from app.runtime.control.dispatch.gateway.contracts import (
    GatewayDispatchLaunchError,
    GatewayDispatchLaunchOutcome,
)
from app.runtime.control.dispatch.gateway.session import resolve_gateway_session_key
from app.runtime.control.dispatch.openclaw_runtime import (
    OpenClawDispatchLaunchLease,
    close_dispatch_launch_lease,
    open_dispatch_launch_lease,
)
from app.runtime.openclaw import (
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawLaunchRequest,
    OpenClawLaunchResult,
)
from app.runtime.openclaw.protocol import OpenClawAgentAcceptedPayload, parse_response_payload
from app.runtime.openclaw.request_builders import (
    OpenClawGatewayRequest,
    build_openclaw_agent_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from app.runtime.projection.dispatch.prompt import build_dispatch_prompt


@dataclass(frozen=True)
class TrackedGatewayLaunchResult:
    launch_result: OpenClawLaunchResult
    lease: OpenClawDispatchLaunchLease


async def perform_gateway_dispatch_launch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    assignment_key: str,
    attempt_id: str,
) -> GatewayDispatchLaunchOutcome:
    if dispatch.task_id is None:
        from app.runtime.control.failures import illegal_state_error

        raise illegal_state_error("dispatch is missing task ownership")
    gateway_session_key = await resolve_gateway_session_key(session, dispatch=dispatch)
    _bundle, prompt_record = await build_dispatch_prompt(
        session,
        dispatch.task_id,
        dispatch,
        session_key_override=gateway_session_key,
    )
    result = await launch_gateway_run_with_tracking(
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
    return GatewayDispatchLaunchOutcome(
        launch_result=result.launch_result,
        prompt_path=str(prompt_record.rendered_markdown_path),
        content_hash=prompt_record.content_hash,
        lease=result.lease,
    )


async def launch_gateway_run_with_tracking(
    request: OpenClawLaunchRequest,
) -> TrackedGatewayLaunchResult:
    settings = get_settings()
    lease = await open_dispatch_launch_lease()
    gateway_request = build_openclaw_agent_request(
        config=settings.openclaw,
        request_id=next_openclaw_request_id("agent"),
        launch_request=request,
    )
    request_sent = False
    try:
        validate_gateway_launch_pre_send_policy(
            gateway_request,
            compatibility=lease.handle.require_compatibility(),
        )
        request_sent = True
        response, _observed_events = await lease.handle.send_request(gateway_request)
        accepted = parse_response_payload(response, OpenClawAgentAcceptedPayload)
        return TrackedGatewayLaunchResult(
            launch_result=OpenClawLaunchResult(
                session_key=request.session_key,
                run_id=accepted.run_id,
                accepted_at=accepted.accepted_at,
                compatibility=lease.handle.require_compatibility(),
                observed_events=(),
            ),
            lease=lease,
        )
    except Exception as exc:
        if not request_sent:
            await close_dispatch_launch_lease(lease)
        raise GatewayDispatchLaunchError(
            error=exc,
            request_sent=request_sent,
            session_key=request.session_key,
            lease=lease,
        ) from exc


def validate_gateway_launch_pre_send_policy(
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
