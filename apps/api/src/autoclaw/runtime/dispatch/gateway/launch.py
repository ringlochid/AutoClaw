from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import (
    OpenClawAgentLaunchInput,
    OpenClawLaunchResult,
)
from autoclaw.integrations.openclaw.gateway.protocol import (
    OpenClawAgentAcceptedPayload,
    parse_response_payload,
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
from autoclaw.runtime.prompt.bundle import render_prompt_transport_markdown


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
        build_gateway_launch_input(
            session_key=gateway_session_key,
            transport_request=prompt_record.transport_request,
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
    request_sent = False
    try:
        response, request_sent = await lease.handle.send_agent_launch_request_with_tracking(
            launch_input
        )
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


def build_gateway_launch_input(
    *,
    session_key: str,
    transport_request: PromptTransportRequest,
    idempotency_key: str,
) -> OpenClawAgentLaunchInput:
    instructions_text = transport_request.instructions_text
    if instructions_text is None:
        raise ValueError("full_prompt transport requests require instructions_text")
    return OpenClawAgentLaunchInput(
        session_key=session_key,
        message=transport_request.input_text,
        extra_system_prompt=instructions_text,
        flattened_message_fallback=render_prompt_transport_markdown(transport_request),
        idempotency_key=idempotency_key,
    )
