from __future__ import annotations

from pathlib import Path

from app.db import DispatchTurnModel, FlowModel
from app.runtime import pause_runtime_flow, runtime_flow_read
from app.runtime.effects import wait_for_runtime_effects
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.dispatch_support import delivery_state_path, read_json


async def assert_boundary_wait_state(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
    root_attempt_id: str | None,
    task_root: Path,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        prior_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        flow_read = await runtime_flow_read(session, task_id)
        assert flow is not None
        assert prior_dispatch is not None
        assert flow.current_open_dispatch_id == dispatch_id
        assert flow_read.current_node_key == "root"
        assert flow_read.active_attempt_id == root_attempt_id
        assert prior_dispatch.control_state == "live"
        assert prior_dispatch.control_deadline_at is not None
        assert prior_dispatch.fenced_at is None
        await wait_for_runtime_effects(task_id=task_id)
        prior_delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
        )
        assert prior_delivery_state["transport_state"] == "accepted"
        assert prior_delivery_state["controller_observation_state"] == "live"


async def assert_boundary_replacement_dispatch(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
    task_root: Path,
) -> DispatchTurnModel:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        prior_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert prior_dispatch is not None
        assert prior_dispatch.control_state == "fenced"
        assert prior_dispatch.control_deadline_at is None
        assert prior_dispatch.fenced_at is not None
        assert flow.current_open_dispatch_id is not None
        replacement = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert replacement is not None
        await wait_for_runtime_effects(task_id=task_id)
        prior_delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
        )
        assert prior_delivery_state["transport_state"] == "provider_completed"
        assert prior_delivery_state["controller_observation_state"] == "fenced"
        assert prior_delivery_state["superseded_by_dispatch_id"] == replacement.dispatch_id
        return replacement


async def force_dispatch_deadline_to_closed_at(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> None:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        dispatch.control_deadline_at = dispatch.closed_at
        await session.commit()


async def pause_flow_until_abort_requested(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
    task_root: Path,
) -> tuple[str, str | None]:
    async with session_factory() as session:
        flow_read = await runtime_flow_read(session, task_id)
        root_attempt_id = flow_read.active_attempt_id
        paused = await pause_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=flow_read.active_flow_revision_id,
        )
        await session.commit()
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert flow is not None
        assert dispatch is not None
        assert paused.flow.status.value == "paused"
        assert paused.flow.current_node_key == "root"
        assert paused.flow.active_attempt_id == root_attempt_id
        assert flow.current_open_dispatch_id == dispatch_id
        assert dispatch.control_state == "abort_requested"
        assert dispatch.control_state_reason == "pause_requested"
        assert dispatch.control_deadline_at is not None
        assert dispatch.fenced_at is None
        assert dispatch.closed_at is not None
        assert dispatch.status == "closed"
        await wait_for_runtime_effects(task_id=task_id)
        delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
        )
        assert delivery_state["transport_state"] == "accepted"
        assert delivery_state["controller_observation_state"] == "abort_requested"
        assert delivery_state["last_controller_terminal_at"] is None
        return flow_read.active_flow_revision_id, root_attempt_id


async def assert_pause_wait_state(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert flow is not None
        assert dispatch is not None
        assert flow.status == "paused"
        assert flow.current_open_dispatch_id == dispatch_id
        assert dispatch.control_state == "abort_requested"
        assert dispatch.fenced_at is None


async def assert_pause_resumption_state(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
    root_attempt_id: str | None,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        prior_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert flow is not None
        assert prior_dispatch is not None
        assert flow.status == "running"
        assert flow.current_open_dispatch_id is not None
        replacement = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert replacement is not None
        assert prior_dispatch.control_state == "fenced"
        assert prior_dispatch.control_deadline_at is None
        assert prior_dispatch.fenced_at is not None
        assert replacement.previous_dispatch_id == dispatch_id
        assert replacement.attempt_id == root_attempt_id
