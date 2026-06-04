from __future__ import annotations

from websockets.exceptions import WebSocketException

from autoclaw.db.models import DispatchTurnModel
from autoclaw.integrations.openclaw.gateway import (
    OpenClawConfigurationError,
    OpenClawGatewayRuntimeHandle,
    OpenClawProtocolError,
    OpenClawTransportError,
    OpenClawWaitRequest,
    OpenClawWaitResult,
    build_openclaw_gateway_adapter,
)
from autoclaw.runtime.control.dispatch.openclaw_runtime.lifecycle import wait_dispatch_runtime
from autoclaw.runtime.control.failures import illegal_state_error


async def wait_for_gateway_dispatch(
    *,
    dispatch: DispatchTurnModel,
    timeout_ms: int,
) -> OpenClawWaitResult:
    if dispatch.gateway_run_id is None:
        raise illegal_state_error("gateway wait requires a persisted run id")
    return await wait_for_gateway_run(
        dispatch_id=dispatch.dispatch_id,
        run_id=dispatch.gateway_run_id,
        timeout_ms=timeout_ms,
    )


async def wait_for_gateway_run_with_fallback(
    *,
    run_id: str,
    timeout_ms: int,
    handle: OpenClawGatewayRuntimeHandle | None = None,
) -> OpenClawWaitResult:
    if handle is None:
        return await wait_for_gateway_run(run_id=run_id, timeout_ms=timeout_ms)
    try:
        return await wait_for_gateway_run(
            run_id=run_id,
            timeout_ms=timeout_ms,
            handle=handle,
        )
    except (OpenClawTransportError, OpenClawProtocolError, WebSocketException, OSError):
        return await wait_for_gateway_run(
            run_id=run_id,
            timeout_ms=timeout_ms,
        )
    except OpenClawConfigurationError:
        raise


async def wait_for_gateway_run(
    *,
    dispatch_id: str | None = None,
    run_id: str,
    timeout_ms: int,
    handle: OpenClawGatewayRuntimeHandle | None = None,
) -> OpenClawWaitResult:
    if handle is not None:
        return await handle.wait_for_run(OpenClawWaitRequest(run_id=run_id, timeout_ms=timeout_ms))
    if dispatch_id is not None:
        wait_result = await wait_dispatch_runtime(
            dispatch_id,
            run_id=run_id,
            timeout_ms=timeout_ms,
        )
        if wait_result is not None:
            return wait_result
    adapter = build_openclaw_gateway_adapter()
    return await adapter.wait_for_run(OpenClawWaitRequest(run_id=run_id, timeout_ms=timeout_ms))
