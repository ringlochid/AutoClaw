from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from autoclaw.db.session import get_session_factory
from autoclaw.integrations.openclaw.gateway.adapter import (
    OpenClawGatewayAdapter,
    build_openclaw_gateway_adapter,
    openclaw_startup_compatibility_required,
)
from autoclaw.integrations.openclaw.gateway.contracts import (
    OpenClawAbortRequest,
    OpenClawAbortResult,
    OpenClawAdapterError,
    OpenClawAgentLaunchInput,
    OpenClawAuthError,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawConfigurationError,
    OpenClawLaunchResult,
    OpenClawObservedEvent,
    OpenClawProtocolError,
    OpenClawTransportError,
    OpenClawWaitRequest,
    OpenClawWaitResult,
    OpenClawWaitStatus,
    gateway_ws_url_from_base_url,
)
from autoclaw.integrations.openclaw.gateway.protocol import (
    OPENCLAW_PROTOCOL_VERSION,
    OPENCLAW_RELEASE_FAMILY,
    REQUIRED_GATEWAY_METHODS,
    REQUIRED_GATEWAY_ROLE,
    REQUIRED_GATEWAY_SCOPES,
)
from autoclaw.integrations.openclaw.gateway.runtime_handle import OpenClawGatewayRuntimeHandle
from autoclaw.runtime.effects import (
    commit_runtime_session,
    rollback_runtime_session,
    run_runtime_write,
    wait_for_runtime_effects,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

ResultT = TypeVar("ResultT")


async def read_openclaw_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await operation(session)


async def write_openclaw_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def write_openclaw_runtime_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await run_runtime_write(
            session,
            lambda: operation(session),
        )


async def write_openclaw_runtime_operation_and_wait(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    task_id_getter: Callable[[ResultT], str],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await commit_runtime_session(session)
            await wait_for_runtime_effects(task_id=task_id_getter(result))
            return result
        except Exception:
            await rollback_runtime_session(session)
            raise


__all__ = [
    "OPENCLAW_PROTOCOL_VERSION",
    "OPENCLAW_RELEASE_FAMILY",
    "REQUIRED_GATEWAY_METHODS",
    "REQUIRED_GATEWAY_ROLE",
    "REQUIRED_GATEWAY_SCOPES",
    "OpenClawAbortRequest",
    "OpenClawAbortResult",
    "OpenClawAdapterError",
    "OpenClawAgentLaunchInput",
    "OpenClawAuthError",
    "OpenClawCompatibilityError",
    "OpenClawCompatibilityReport",
    "OpenClawConfigurationError",
    "OpenClawGatewayAdapter",
    "OpenClawGatewayRuntimeHandle",
    "OpenClawLaunchResult",
    "OpenClawObservedEvent",
    "OpenClawProtocolError",
    "OpenClawTransportError",
    "OpenClawWaitRequest",
    "OpenClawWaitResult",
    "OpenClawWaitStatus",
    "build_openclaw_gateway_adapter",
    "gateway_ws_url_from_base_url",
    "openclaw_startup_compatibility_required",
    "read_openclaw_operation",
    "write_openclaw_operation",
    "write_openclaw_runtime_operation",
    "write_openclaw_runtime_operation_and_wait",
]
