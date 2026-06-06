from __future__ import annotations

from pathlib import Path

from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.runtime import EgressBoundary, accept_boundary, runtime_flow_read
from autoclaw.runtime.contracts import BoundaryWrite as BoundaryWriteSchema
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.runtime_dispatch_support import delivery_state_path, read_json


async def open_child_flow_after_yield(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    active_flow_revision_id: str,
    child_node_key: str = "implement_change",
) -> tuple[str, str]:
    await drive_runtime_until(
        lambda: _child_flow_opened(
            session_factory,
            task_id=task_id,
            active_flow_revision_id=active_flow_revision_id,
            child_node_key=child_node_key,
        ),
        task_id=task_id,
        max_cycles=20,
    )
    async with session_factory() as session:
        child_flow = await runtime_flow_read(session, task_id)
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.active_flow_revision_id == active_flow_revision_id
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        assert dispatch.node_key == child_node_key
        assert child_flow.active_attempt_id is not None
        assert child_flow.current_node_key == child_node_key
        assert flow.current_node_key == child_node_key
        return flow.current_open_dispatch_id, child_flow.active_attempt_id


async def assert_worker_green_flips_currentness_to_parent_while_worker_dispatch_stays_live(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    child_dispatch_id: str,
    task_root: Path,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        child_dispatch = await session.get(DispatchTurnModel, child_dispatch_id)
        flow_read = await runtime_flow_read(session, task_id)
        assert flow is not None
        assert child_dispatch is not None
        assert flow.current_open_dispatch_id == child_dispatch_id
        assert flow_read.current_node_key == "root"
        assert child_dispatch.closed_by_boundary == EgressBoundary.GREEN.value
        assert child_dispatch.control_state == "live"
        await drive_runtime_once(task_id=task_id)
        delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=child_dispatch_id)
        )
        assert delivery_state["transport_state"] == "accepted"


async def assert_parent_redispatch_after_worker_green(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    active_flow_revision_id: str,
    child_dispatch_id: str,
) -> None:
    await drive_runtime_until(
        lambda: _parent_redispatch_ready(
            session_factory,
            task_id=task_id,
            active_flow_revision_id=active_flow_revision_id,
            child_dispatch_id=child_dispatch_id,
        ),
        task_id=task_id,
        max_cycles=60,
    )
    async with session_factory() as session:
        flow_read = await runtime_flow_read(session, task_id)
        assert flow_read.current_node_key == "root"
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.active_flow_revision_id == active_flow_revision_id
        assert flow.current_open_dispatch_id is not None
        parent_dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert parent_dispatch is not None
        assert parent_dispatch.previous_dispatch_id == child_dispatch_id
        assert flow_read.active_attempt_id == parent_dispatch.attempt_id


async def accept_green_boundary(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    child_attempt_id: str,
) -> None:
    del child_attempt_id

    async with session_factory() as session:
        green = await accept_boundary(
            session,
            task_id,
            BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
        )
        await session.commit()
        assert green.flow.current_node_key == "root"


async def _child_flow_opened(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    active_flow_revision_id: str,
    child_node_key: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None:
            return False
        if flow.current_open_dispatch_id is None:
            return False
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        if dispatch is None:
            return False
        return (
            flow.active_flow_revision_id == active_flow_revision_id
            and dispatch.node_key == child_node_key
            and flow.current_node_key == child_node_key
        )


async def _parent_redispatch_ready(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    active_flow_revision_id: str,
    child_dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None or flow.active_flow_revision_id != active_flow_revision_id:
            return False
        if flow.current_open_dispatch_id is None:
            return False
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        return (
            dispatch is not None
            and dispatch.node_key == "root"
            and dispatch.previous_dispatch_id == child_dispatch_id
        )


__all__ = [
    "accept_green_boundary",
    "assert_parent_redispatch_after_worker_green",
    "assert_worker_green_flips_currentness_to_parent_while_worker_dispatch_stays_live",
    "open_child_flow_after_yield",
]
