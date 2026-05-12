from __future__ import annotations

from pathlib import Path

import pytest
from app.db import DispatchTurnModel, FlowModel
from app.db.session import dispose_db_engine
from app.runtime import continue_runtime_flow, pause_runtime_flow, runtime_flow_read
from app.runtime.effects import wait_for_runtime_effects
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.dispatch_support import (
    current_open_dispatch_id,
    delivery_state_path,
    mark_dispatch_provider_completed,
    read_json,
    stage_child_yield,
)
from tests.integration.phase3.runtime_support import (
    bootstrap_parent_runtime,
    phase3_runtime_api,
    prepare_runtime_db,
)


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


@pytest.mark.asyncio
async def test_phase3_boundary_waits_for_inactivity_proof_before_opening_replacement_dispatch(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_wait"

    try:
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-wait",
        )

        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
                root_attempt_id = flow_read.active_attempt_id

            active_flow_revision_id = await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            async with api.session_factory() as session:
                with pytest.raises(ValueError, match="awaiting inactivity proof"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=active_flow_revision_id,
                    )
            await assert_boundary_wait_state(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                root_attempt_id=root_attempt_id,
                task_root=task_root,
            )

            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=dispatch_id,
            )
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                assert flow_read.current_node_key == "root"
                assert flow_read.active_attempt_id == root_attempt_id
            async with api.session_factory() as session:
                continued = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=active_flow_revision_id,
                )
                await session.commit()
                assert continued.current_node_key == "implementation_subtree"
            replacement = await assert_boundary_replacement_dispatch(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                task_root=task_root,
            )
            assert continued.active_attempt_id == replacement.attempt_id
            assert replacement.previous_dispatch_id == dispatch_id
            assert replacement.node_key == "implementation_subtree"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_ambiguous_previous_dispatch_blocks_replacement_dispatch(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_ambiguous"

    try:
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-ambiguous",
        )

        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)

            active_flow_revision_id = await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()
            async with api.session_factory() as session:
                with pytest.raises(ValueError, match="timed out"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=active_flow_revision_id,
                    )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "ambiguous"
                assert dispatch.control_deadline_at is None
                await wait_for_runtime_effects(task_id=task_id)
                delivery_state = read_json(
                    delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert delivery_state["transport_state"] == "transport_ambiguous"
                assert delivery_state["controller_observation_state"] == "ambiguous"
                assert flow_read.current_node_key == "root"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_pause"

    try:
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-pause",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            async with api.session_factory() as session:
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
            async with api.session_factory() as session:
                with pytest.raises(ValueError, match="awaiting inactivity proof"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                    )
            await assert_pause_wait_state(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )

            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=dispatch_id,
            )
            async with api.session_factory() as session:
                resumed = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                )
                await session.commit()
                assert resumed.current_node_key == "root"
                assert resumed.active_attempt_id == root_attempt_id
            await assert_pause_resumption_state(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                root_attempt_id=root_attempt_id,
            )
    finally:
        await dispose_db_engine()


__all__ = [
    "test_phase3_ambiguous_previous_dispatch_blocks_replacement_dispatch",
    "test_phase3_boundary_waits_for_inactivity_proof_before_opening_replacement_dispatch",
    "test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch",
]
