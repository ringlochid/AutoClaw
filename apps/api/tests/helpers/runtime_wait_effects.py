from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from autoclaw.db import DispatchTurnModel, FlowModel
from autoclaw.runtime.effects import drive_runtime_once, wait_for_runtime_effects
from autoclaw.runtime.openclaw.fixtures import agent_wait_fixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_PHASE3_GATEWAY_TEST_SERVER: ContextVar[Any | None] = ContextVar(
    "phase3_gateway_test_server",
    default=None,
)


@contextmanager
def phase3_gateway_test_server_context(gateway_server: Any) -> Any:
    token: Token[Any | None] = _PHASE3_GATEWAY_TEST_SERVER.set(gateway_server)
    try:
        yield
    finally:
        _PHASE3_GATEWAY_TEST_SERVER.reset(token)


async def commit_current_dispatch_wait_ok(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> str:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch_id = flow.current_open_dispatch_id
    return await commit_dispatch_wait_ok(session_factory, dispatch_id=dispatch_id)


async def commit_dispatch_wait_ok(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> str:
    task_id: str | None = None
    for _ in range(40):
        async with session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert dispatch is not None
            task_id = dispatch.task_id
            if dispatch.delivery_status in {"provider_completed", "provider_failed"}:
                return task_id
            if dispatch.control_state in {"fenced", "ambiguous"}:
                return task_id
        assert task_id is not None
        await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
        await drive_runtime_once(task_id=task_id)
        await asyncio.sleep(0.05)
    assert task_id is not None
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        raise AssertionError(
            f"dispatch '{dispatch_id}' did not commit a terminal gateway wait result"
        )


async def mark_dispatch_provider_completed(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> None:
    await queue_gateway_wait_ok_if_available(
        session_factory,
        dispatch_id=dispatch_id,
    )
    task_id = await commit_dispatch_wait_ok(
        session_factory,
        dispatch_id=dispatch_id,
    )
    await drive_runtime_once(task_id=task_id)
    await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)


async def queue_gateway_wait_ok_if_available(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> None:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        gateway_run_id = dispatch.gateway_run_id
    gateway_server = _PHASE3_GATEWAY_TEST_SERVER.get()
    if gateway_server is not None and isinstance(gateway_run_id, str):
        gateway_server.queue_method_payloads(
            "agent.wait",
            agent_wait_fixture(status="ok", run_id=gateway_run_id),
        )


__all__ = [
    "commit_current_dispatch_wait_ok",
    "commit_dispatch_wait_ok",
    "mark_dispatch_provider_completed",
    "phase3_gateway_test_server_context",
    "queue_gateway_wait_ok_if_available",
]
