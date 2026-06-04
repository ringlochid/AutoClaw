"""Temporary Phase 6 shims for the legacy runtime OpenClaw owners."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from app.db import session as legacy_db_session
from app.runtime import effects as legacy_runtime_effects
from app.runtime.openclaw import adapter as legacy_openclaw_adapter
from app.runtime.openclaw import contracts as legacy_openclaw_contracts
from app.runtime.openclaw import protocol as legacy_openclaw_protocol
from app.runtime.openclaw import runtime_handle as legacy_openclaw_runtime_handle

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

OPENCLAW_PROTOCOL_VERSION = legacy_openclaw_protocol.OPENCLAW_PROTOCOL_VERSION
OPENCLAW_RELEASE_FAMILY = legacy_openclaw_protocol.OPENCLAW_RELEASE_FAMILY
REQUIRED_GATEWAY_METHODS = legacy_openclaw_protocol.REQUIRED_GATEWAY_METHODS
REQUIRED_GATEWAY_ROLE = legacy_openclaw_protocol.REQUIRED_GATEWAY_ROLE
REQUIRED_GATEWAY_SCOPES = legacy_openclaw_protocol.REQUIRED_GATEWAY_SCOPES
OpenClawAbortRequest = legacy_openclaw_contracts.OpenClawAbortRequest
OpenClawAbortResult = legacy_openclaw_contracts.OpenClawAbortResult
OpenClawAdapterError = legacy_openclaw_contracts.OpenClawAdapterError
OpenClawAgentLaunchInput = legacy_openclaw_contracts.OpenClawAgentLaunchInput
OpenClawAuthError = legacy_openclaw_contracts.OpenClawAuthError
OpenClawCompatibilityError = legacy_openclaw_contracts.OpenClawCompatibilityError
OpenClawCompatibilityReport = legacy_openclaw_contracts.OpenClawCompatibilityReport
OpenClawConfigurationError = legacy_openclaw_contracts.OpenClawConfigurationError
OpenClawGatewayAdapter = legacy_openclaw_adapter.OpenClawGatewayAdapter
OpenClawGatewayRuntimeHandle = legacy_openclaw_runtime_handle.OpenClawGatewayRuntimeHandle
OpenClawLaunchResult = legacy_openclaw_contracts.OpenClawLaunchResult
OpenClawObservedEvent = legacy_openclaw_contracts.OpenClawObservedEvent
OpenClawProtocolError = legacy_openclaw_contracts.OpenClawProtocolError
OpenClawTransportError = legacy_openclaw_contracts.OpenClawTransportError
OpenClawWaitRequest = legacy_openclaw_contracts.OpenClawWaitRequest
OpenClawWaitResult = legacy_openclaw_contracts.OpenClawWaitResult
OpenClawWaitStatus = legacy_openclaw_contracts.OpenClawWaitStatus
build_openclaw_gateway_adapter = legacy_openclaw_adapter.build_openclaw_gateway_adapter
gateway_ws_url_from_base_url = legacy_openclaw_contracts.gateway_ws_url_from_base_url
openclaw_startup_compatibility_required = (
    legacy_openclaw_adapter.openclaw_startup_compatibility_required
)

ResultT = TypeVar("ResultT")


async def read_openclaw_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = legacy_db_session.get_session_factory()
    async with session_factory() as session:
        return await operation(session)


async def write_openclaw_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = legacy_db_session.get_session_factory()
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
    session_factory = legacy_db_session.get_session_factory()
    async with session_factory() as session:
        return await legacy_runtime_effects.run_runtime_write(
            session,
            lambda: operation(session),
        )


async def write_openclaw_runtime_operation_and_wait(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    task_id_getter: Callable[[ResultT], str],
) -> ResultT:
    session_factory = legacy_db_session.get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await legacy_runtime_effects.commit_runtime_session(session)
            await legacy_runtime_effects.wait_for_runtime_effects(task_id=task_id_getter(result))
            return result
        except Exception:
            await legacy_runtime_effects.rollback_runtime_session(session)
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
