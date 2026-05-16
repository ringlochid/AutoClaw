from __future__ import annotations

from pathlib import Path
from typing import Any

from app.db import DispatchTurnModel, FlowModel
from app.runtime.effects import wait_for_runtime_effects
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.control.abort_support import (
    accept_green_boundary,
    assert_worker_green_kept_current,
    open_child_flow_after_yield,
    record_green_checkpoint_for_child,
)
from tests.integration.phase3.dispatch_support import (
    current_open_dispatch_id,
    mark_dispatch_provider_completed,
)


async def capture_root_gateway_state(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> tuple[str, str, str | None]:
    dispatch_id = await current_open_dispatch_id(session_factory, task_id=task_id)
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert dispatch.gateway_session_key is not None
        return dispatch_id, dispatch.gateway_session_key, dispatch.gateway_run_id


async def complete_worker_green_cycle(
    api: Any,
    *,
    task_id: str,
    task_root: Path,
    initial_root_dispatch_id: str,
    active_flow_revision_id: str,
) -> tuple[str, str, str]:
    await mark_dispatch_provider_completed(
        api.session_factory,
        dispatch_id=initial_root_dispatch_id,
    )
    child_dispatch_id, child_attempt_id = await open_child_flow_after_yield(
        session_factory=api.session_factory,
        task_id=task_id,
        active_flow_revision_id=active_flow_revision_id,
    )
    async with api.session_factory() as session:
        child_dispatch = await session.get(DispatchTurnModel, child_dispatch_id)
        assert child_dispatch is not None
        assert child_dispatch.gateway_session_key is not None
        child_gateway_session_key = child_dispatch.gateway_session_key
        await record_green_checkpoint_for_child(
            session=session,
            task_id=task_id,
            task_root=task_root,
        )
        await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    await accept_green_boundary(
        api.session_factory,
        task_id=task_id,
        child_attempt_id=child_attempt_id,
    )
    await assert_worker_green_kept_current(
        session_factory=api.session_factory,
        task_id=task_id,
        child_dispatch_id=child_dispatch_id,
        child_attempt_id=child_attempt_id,
        task_root=task_root,
    )
    return child_dispatch_id, child_attempt_id, child_gateway_session_key


async def assert_parent_redispatch_reused_root_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    child_dispatch_id: str,
    child_gateway_session_key: str,
    initial_root_gateway_session_key: str,
    initial_root_gateway_run_id: str | None,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        resumed_root_dispatch = await session.get(
            DispatchTurnModel,
            flow.current_open_dispatch_id,
        )
        assert resumed_root_dispatch is not None
        assert resumed_root_dispatch.node_key == "root"
        assert resumed_root_dispatch.previous_dispatch_id == child_dispatch_id
        assert resumed_root_dispatch.gateway_session_key == initial_root_gateway_session_key
        assert resumed_root_dispatch.gateway_session_key != child_gateway_session_key
        assert resumed_root_dispatch.gateway_run_id != initial_root_gateway_run_id


__all__ = [
    "assert_parent_redispatch_reused_root_session",
    "capture_root_gateway_state",
    "complete_worker_green_cycle",
]
