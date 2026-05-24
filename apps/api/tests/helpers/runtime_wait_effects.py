from __future__ import annotations

import asyncio

from app.db import DispatchTurnModel, FlowModel
from app.runtime.effects import drive_runtime_once, wait_for_runtime_effects
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


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


__all__ = ["commit_current_dispatch_wait_ok", "commit_dispatch_wait_ok"]
