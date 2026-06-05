from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import (
    OpenClawAgentLaunchInput,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawLaunchResult,
)
from autoclaw.integrations.openclaw.gateway.protocol import (
    OpenClawAgentAcceptedPayload,
    parse_response_payload,
)
from autoclaw.integrations.openclaw.gateway.request_builders import (
    OpenClawGatewayRequest,
    build_openclaw_agent_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from autoclaw.integrations.openclaw.gateway.runtime_handle import OpenClawRequestDispatchError
from autoclaw.integrations.openclaw.gateway.session_keys import normalize_agent_launch_input
from autoclaw.persistence.models import DispatchTurnModel
from autoclaw.runtime.contracts import PromptTransportRequest
from autoclaw.runtime.dispatch.gateway.contracts import (
    GatewayDispatchLaunchError,
    GatewayDispatchLaunchOutcome,
)
from autoclaw.runtime.dispatch.gateway.session import resolve_gateway_session_key
from autoclaw.runtime.dispatch.openclaw.lease import (
    close_dispatch_launch_lease,
    open_dispatch_launch_lease,
)
from autoclaw.runtime.projection.dispatch.prompt import build_dispatch_prompt


async def perform_gateway_dispatch_launch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> GatewayDispatchLaunchOutcome:
    if dispatch.task_id is None:
        from autoclaw.runtime.errors import illegal_state_error

        raise illegal_state_error("dispatch is missing task ownership")
    gateway_session_key = await resolve_gateway_session_key(session, dispatch=dispatch)
    _bundle, prompt_record = await build_dispatch_prompt(
        session,
        dispatch.task_id,
        dispatch,
        session_key_override=gateway_session_key,
    )
    return await launch_gateway_run_with_tracking(
        OpenClawAgentLaunchInput(
            session_key=gateway_session_key,
            message=build_gateway_launch_message(prompt_record.transport_request),
            idempotency_key=f"dispatch:{dispatch.dispatch_id}",
        ),
        prompt_path=str(prompt_record.rendered_markdown_path),
        content_hash=prompt_record.content_hash,
    )


async def launch_gateway_run_with_tracking(
    request: OpenClawAgentLaunchInput,
    *,
    prompt_path: str,
    content_hash: str,
) -> GatewayDispatchLaunchOutcome:
    settings = get_settings()
    launch_input = normalize_agent_launch_input(request, settings.openclaw.agent_id)
    lease = await open_dispatch_launch_lease()
    gateway_request = build_openclaw_agent_request(
        request_id=next_openclaw_request_id("agent"),
        launch_input=launch_input,
    )
    request_sent = False
    try:
        validate_gateway_launch_pre_send_policy(
            gateway_request,
            compatibility=lease.handle.require_compatibility(),
        )
        response, request_sent = await lease.handle.send_request_with_tracking(gateway_request)
        accepted = parse_response_payload(response, OpenClawAgentAcceptedPayload)
        return GatewayDispatchLaunchOutcome(
            launch_result=OpenClawLaunchResult(
                session_key=launch_input.session_key,
                run_id=accepted.run_id,
                accepted_at=accepted.accepted_at,
                compatibility=lease.handle.require_compatibility(),
            ),
            prompt_path=prompt_path,
            content_hash=content_hash,
            lease=lease,
        )
    except OpenClawRequestDispatchError as exc:
        if not exc.request_sent:
            await close_dispatch_launch_lease(lease)
        raise GatewayDispatchLaunchError(
            error=exc.error,
            is_request_sent=exc.request_sent,
            session_key=launch_input.session_key,
            lease=lease,
        ) from exc
    except Exception as exc:
        if not request_sent:
            await close_dispatch_launch_lease(lease)
        raise GatewayDispatchLaunchError(
            error=exc,
            is_request_sent=request_sent,
            session_key=launch_input.session_key,
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


def build_gateway_launch_message(transport_request: PromptTransportRequest) -> str:
    parts = [
        transport_request.instructions_text,
        transport_request.input_text,
    ]
    return "\n\n".join(part for part in parts if part)
