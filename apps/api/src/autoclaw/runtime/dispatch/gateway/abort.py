from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from websockets.exceptions import WebSocketException

from autoclaw.integrations.openclaw.gateway import (
    OpenClawAbortRequest,
    OpenClawConfigurationError,
    OpenClawGatewayRuntimeHandle,
    OpenClawProtocolError,
    OpenClawTransportError,
    build_openclaw_gateway_adapter,
)
from autoclaw.persistence.models import DispatchDeliveryStateModel, DispatchTurnModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.dispatch.gateway_observability import append_gateway_event
from autoclaw.runtime.dispatch.openclaw.lifecycle import abort_dispatch_runtime
from autoclaw.runtime.errors import illegal_state_error


async def abort_gateway_run_with_fallback(
    *,
    session_key: str,
    run_id: str | None,
    handle: OpenClawGatewayRuntimeHandle | None = None,
) -> None:
    if handle is None:
        await abort_gateway_run(session_key=session_key, run_id=run_id)
        return
    try:
        await abort_gateway_run(
            session_key=session_key,
            run_id=run_id,
            handle=handle,
        )
    except (OpenClawTransportError, OpenClawProtocolError, WebSocketException, OSError):
        await abort_gateway_run(
            session_key=session_key,
            run_id=run_id,
        )
    except OpenClawConfigurationError:
        raise


async def abort_gateway_dispatch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    if dispatch.gateway_session_key is None:
        raise illegal_state_error("gateway abort requires a persisted session key")
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if abort_already_recorded(dispatch, delivery_state):
        return False
    aborted_with_runtime = await abort_dispatch_runtime(
        dispatch.dispatch_id,
        session_key=dispatch.gateway_session_key,
        run_id=dispatch.gateway_run_id,
    )
    if not aborted_with_runtime:
        await abort_gateway_run(
            session_key=dispatch.gateway_session_key,
            run_id=dispatch.gateway_run_id,
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


async def abort_gateway_run(
    *,
    session_key: str,
    run_id: str | None,
    handle: OpenClawGatewayRuntimeHandle | None = None,
) -> None:
    request = OpenClawAbortRequest(session_key=session_key, run_id=run_id)
    if handle is not None:
        await handle.abort_run(request)
        return
    adapter = build_openclaw_gateway_adapter()
    await adapter.abort_run(request)


def abort_already_recorded(
    dispatch: DispatchTurnModel,
    delivery_state: DispatchDeliveryStateModel | None,
) -> bool:
    return (
        dispatch.abort_requested_at is not None
        and delivery_state is not None
        and delivery_state.last_controller_progress_at is not None
        and delivery_state.last_controller_progress_at >= dispatch.abort_requested_at
    )
