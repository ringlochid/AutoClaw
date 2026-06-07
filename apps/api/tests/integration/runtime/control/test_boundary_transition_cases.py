from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime import continue_runtime_flow, runtime_flow_read
from autoclaw.runtime.post_commit import (
    drive_runtime_once,
    drive_runtime_until,
    stop_runtime_effect_runner,
)
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_dispatch_support import (
    current_open_dispatch_id,
    delivery_state_path,
    read_json,
    stage_child_yield,
)
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_api_context,
    set_dispatch_drain_timeout,
)
from tests.integration.runtime.control.boundary_support import (
    assert_boundary_replacement_dispatch,
    assert_boundary_wait_state,
    force_dispatch_deadline_to_closed_at,
)


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


async def _dispatch_replaced(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        return (
            flow is not None
            and dispatch is not None
            and flow.current_open_dispatch_id is not None
            and flow.current_open_dispatch_id != dispatch_id
            and dispatch.control_state == "fenced"
        )


async def _current_dispatch_repaired(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        return flow is not None and flow.current_open_dispatch_id is None


@pytest.mark.asyncio
async def test_boundary_auto_opens_replacement_dispatch_after_inactivity_is_proven(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_boundary_wait"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-boundary-wait",
        )

        async with runtime_api_context(config_path) as api:
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
            replacement = await assert_boundary_replacement_dispatch(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                task_root=task_root,
            )
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                assert flow_read.current_node_key == "implementation_subtree"
                assert flow_read.active_attempt_id == replacement.attempt_id
            assert replacement.previous_dispatch_id == dispatch_id
            assert replacement.node_key == "implementation_subtree"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_boundary_timeout_transitions_to_abort_requested_and_blocks_replacement(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_boundary_timeout_abort_requested"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-boundary-timeout",
        )

        async with runtime_api_context(config_path) as api:
            async with api.session_factory() as session:
                await runtime_flow_read(session, task_id)
                dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)

            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            await stop_runtime_effect_runner()
            await force_dispatch_deadline_to_closed_at(
                api.session_factory,
                dispatch_id=dispatch_id,
            )
            await drive_runtime_once(task_id=task_id)
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                current_flow_read = await runtime_flow_read(session, task_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "abort_requested"
                assert dispatch.control_state_reason == "boundary:yield:abort_requested"
                assert dispatch.control_deadline_at is not None
                delivery_state = read_json(
                    delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert delivery_state["transport_state"] == "accepted"
                assert "controller_observation_state" not in delivery_state
                assert current_flow_read.current_node_key == "implementation_subtree"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_boundary_abort_timeout_force_fences_and_opens_replacement_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_boundary_abort_timeout_force_fence"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-boundary-abort-timeout-force-fence",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            await stop_runtime_effect_runner()
            await force_dispatch_deadline_to_closed_at(
                api.session_factory,
                dispatch_id=dispatch_id,
            )

            await drive_runtime_once(task_id=task_id)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "abort_requested"
                assert dispatch.accepted_boundary == "yield"
                assert dispatch.control_state_reason == "boundary:yield:abort_requested"
                assert dispatch.control_deadline_at is not None

                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()

            await drive_runtime_until(
                lambda: _dispatch_replaced(
                    api.session_factory,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                ),
                task_id=task_id,
                max_cycles=40,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                current_flow_read = await runtime_flow_read(session, task_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id is not None
                assert flow.current_open_dispatch_id != dispatch_id
                assert dispatch.control_state == "fenced"
                assert dispatch.delivery_status == "transport_ambiguous"
                assert dispatch.control_deadline_at is None
                assert current_flow_read.current_node_key == "implementation_subtree"

                replacement_dispatch = await session.get(
                    DispatchTurnModel,
                    flow.current_open_dispatch_id,
                )
                assert replacement_dispatch is not None
                assert replacement_dispatch.previous_dispatch_id == dispatch_id
                assert dispatch.superseded_by_dispatch_id == replacement_dispatch.dispatch_id

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "transport_ambiguous"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_background_timeout_force_fences_and_rematerializes_dispatch_files(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_background_force_fence"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-background-timeout",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            await stop_runtime_effect_runner()
            await force_dispatch_deadline_to_closed_at(
                api.session_factory,
                dispatch_id=dispatch_id,
            )

            await drive_runtime_once(task_id=task_id)

            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert dispatch is not None
                assert flow is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "abort_requested"
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()

            await drive_runtime_until(
                lambda: _dispatch_replaced(
                    api.session_factory,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                ),
                task_id=task_id,
                max_cycles=40,
            )

            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert dispatch is not None
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                assert flow.current_open_dispatch_id != dispatch_id
                assert dispatch.control_state == "fenced"
                assert dispatch.delivery_status == "transport_ambiguous"
                assert dispatch.control_deadline_at is None
                assert dispatch.fenced_at is not None

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert "controller_observation_state" not in delivery_state
            assert delivery_state["last_controller_terminal_at"] is not None
            assert delivery_state["transport_state"] == "transport_ambiguous"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_background_reconcile_clears_orphan_current_dispatch_pointer(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_orphan_current_dispatch_repair"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-orphan-current-dispatch-repair",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await stop_runtime_effect_runner()

            async with api.session_factory() as session:
                connection = await session.connection()
                await connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
                await connection.exec_driver_sql(
                    "DELETE FROM dispatch_turns WHERE dispatch_id = ?",
                    (dispatch_id,),
                )
                await session.commit()

            async with api.session_factory() as session:
                with pytest.raises(ValueError, match=f"missing dispatch '{dispatch_id}'"):
                    await current_runtime_state(session, task_id)
            await drive_runtime_until(
                lambda: _current_dispatch_repaired(
                    api.session_factory,
                    task_id=task_id,
                ),
                task_id=task_id,
                max_cycles=20,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                repaired_state = await current_runtime_state(session, task_id)
                assert flow is not None
                assert flow.current_open_dispatch_id is None
                assert repaired_state.flow.task_id == task_id
                assert repaired_state.current_attempt.task_id == task_id
    finally:
        await dispose_db_engine()


__all__ = [
    "test_background_reconcile_clears_orphan_current_dispatch_pointer",
    "test_background_timeout_force_fences_and_rematerializes_dispatch_files",
    "test_boundary_abort_timeout_force_fences_and_opens_replacement_dispatch",
    "test_boundary_auto_opens_replacement_dispatch_after_inactivity_is_proven",
    "test_boundary_timeout_transitions_to_abort_requested_and_blocks_replacement",
]
