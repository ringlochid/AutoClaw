from __future__ import annotations

from pathlib import Path

import pytest
from app.db import DispatchTurnModel, FlowModel
from app.db.session import dispose_db_engine
from app.runtime import continue_runtime_flow, runtime_flow_read
from app.runtime.effects import wait_for_runtime_effects
from app.runtime.openclaw.fixtures import agent_wait_fixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_test_config import set_dispatch_drain_timeout
from tests.integration.phase3.control.boundary_support import (
    assert_boundary_replacement_dispatch,
    assert_boundary_wait_state,
    assert_pause_resumption_state,
    assert_pause_wait_state,
    force_dispatch_deadline_to_closed_at,
    pause_flow_until_abort_requested,
)
from tests.integration.phase3.dispatch_support import (
    current_open_dispatch_id,
    delivery_state_path,
    read_json,
    stage_child_yield,
)
from tests.integration.phase3.runtime_support import (
    bootstrap_parent_runtime,
    phase3_runtime_api,
    prepare_runtime_db,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


async def _wait_ok_payload_for_dispatch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> dict[str, object]:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert isinstance(dispatch.gateway_run_id, str)
        return agent_wait_fixture(status="ok", run_id=dispatch.gateway_run_id)


@pytest.mark.asyncio
async def test_phase3_boundary_auto_opens_replacement_dispatch_after_inactivity_is_proven(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_wait"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
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
                with pytest.raises(ValueError, match="legal only for paused flows"):
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
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )
            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                assert flow_read.current_node_key == "implementation_subtree"
            replacement = await assert_boundary_replacement_dispatch(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                task_root=task_root,
            )
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                assert flow_read.active_attempt_id == replacement.attempt_id
            assert replacement.previous_dispatch_id == dispatch_id
            assert replacement.node_key == "implementation_subtree"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_ambiguous_previous_dispatch_blocks_replacement_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_ambiguous"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
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

            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            await force_dispatch_deadline_to_closed_at(
                api.session_factory,
                dispatch_id=dispatch_id,
            )
            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "ambiguous"
                assert dispatch.control_deadline_at is None
                delivery_state = read_json(
                    delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert delivery_state["transport_state"] == "transport_ambiguous"
                assert "controller_observation_state" not in delivery_state
                assert flow_read.current_node_key == "root"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_background_timeout_rematerializes_ambiguous_dispatch_files(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_background_timeout"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-background-timeout",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            await force_dispatch_deadline_to_closed_at(
                api.session_factory,
                dispatch_id=dispatch_id,
            )

            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)

            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert dispatch is not None
                assert flow is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "ambiguous"
                assert dispatch.control_deadline_at is None

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "transport_ambiguous"
            assert "controller_observation_state" not in delivery_state
            assert delivery_state["last_controller_terminal_at"] is not None
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_pause"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-pause",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            active_flow_revision_id, root_attempt_id = await pause_flow_until_abort_requested(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                task_root=task_root,
            )
            async with api.session_factory() as session:
                with pytest.raises(ValueError, match="awaiting inactivity proof"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=active_flow_revision_id,
                    )
            await assert_pause_wait_state(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )
            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
            async with api.session_factory() as session:
                resumed = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=active_flow_revision_id,
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
    "test_phase3_boundary_auto_opens_replacement_dispatch_after_inactivity_is_proven",
    "test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch",
]
