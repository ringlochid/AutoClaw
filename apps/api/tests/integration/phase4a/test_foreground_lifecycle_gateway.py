from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.db import DispatchTurnModel, FlowModel, NodeSessionModel, ProviderEventRecordModel
from app.db.session import dispose_db_engine
from app.runtime import (
    cancel_runtime_flow,
    continue_runtime_flow,
    pause_runtime_flow,
    runtime_flow_read,
)
from app.runtime.effects import drive_runtime_once, wait_for_runtime_effects
from app.runtime.openclaw.fixtures import agent_wait_fixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_test_config import set_dispatch_drain_timeout
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
from tests.integration.phase4a.dispatch_gateway_support import (
    wait_for_latest_dispatch_snapshot,
)
from tests.integration.phase4a.redispatch_support import (
    finish_parent_same_session_case,
    prepare_parent_same_session_case,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


async def _pause_dispatch_and_assert_abort_requested(
    api: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    async with api.session_factory() as session:
        flow_read = await runtime_flow_read(session, task_id)
        paused = await pause_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=flow_read.active_flow_revision_id,
        )
        await session.commit()
        assert paused.flow.status.value == "paused"

    await drive_runtime_once(task_id=task_id)

    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert flow is not None
        assert dispatch is not None
        assert flow.status == "paused"
        assert flow.current_open_dispatch_id == dispatch_id
        assert dispatch.control_state == "abort_requested"


async def _assert_pause_dispatch_fenced_after_wait_ok(
    api: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
    snapshot = await wait_for_latest_dispatch_snapshot(
        api.session_factory,
        task_id=task_id,
        predicate=lambda current: (
            current.flow.status == "paused"
            and current.flow.current_open_dispatch_id is None
            and current.dispatch.control_state == "fenced"
            and current.dispatch.fenced_at is not None
            and current.node_session is not None
            and current.node_session.session_status == "fenced"
            and current.node_session.closed_at is not None
        ),
        timeout_seconds=5.0,
        drive_runtime=True,
    )
    assert snapshot.flow.status == "paused"
    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.fenced_at is not None
    assert snapshot.node_session is not None
    assert snapshot.node_session.session_status == "fenced"
    assert snapshot.node_session.closed_at is not None


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
async def test_phase4a_accepted_run_without_callback_is_polled_to_terminal(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase4a_terminal_without_callback"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-4a-terminal-without-callback",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )

            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=5.0)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                node_session = await session.get(
                    NodeSessionModel,
                    f"node-session.{dispatch_id}",
                )
                provider_events = list(
                    await session.scalars(
                        select(ProviderEventRecordModel)
                        .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
                        .order_by(ProviderEventRecordModel.event_no.asc())
                    )
                )
                assert flow is not None
                assert dispatch is not None
                assert node_session is not None
                assert flow.current_open_dispatch_id is None
                assert dispatch.accepted_boundary is None
                assert dispatch.control_state == "fenced"
                assert dispatch.delivery_status == "provider_completed"
                assert node_session.session_status == "fenced"
                assert provider_events[-1].event_kind == "response_completed"

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "provider_completed"
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase4a_pause_uses_gateway_abort_and_wait_before_fencing(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase4a_pause_abort_wait"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-4a-pause-abort-wait",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await _pause_dispatch_and_assert_abort_requested(
                api,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )

            assert any(
                request.method == "sessions.abort"
                for request in openclaw_gateway_test_server.requests
            )
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )

            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )
            await _assert_pause_dispatch_fenced_after_wait_ok(
                api,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "provider_completed"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase4a_gateway_wait_timeout_marks_dispatch_ambiguous(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase4a_wait_timeout_ambiguous"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-4a-wait-timeout-ambiguous",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()

            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                provider_events = list(
                    await session.scalars(
                        select(ProviderEventRecordModel)
                        .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
                        .order_by(ProviderEventRecordModel.event_no.asc())
                    )
                )
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "ambiguous"
                assert provider_events[-1].event_kind == "transport_timeout"

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "transport_ambiguous"
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase4a_paused_timeout_is_fenced_and_continue_reopens_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase4a_pause_timeout_cleanup"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-4a-pause-timeout-cleanup",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await _pause_dispatch_and_assert_abort_requested(
                api,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )

            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()

            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                node_session = await session.get(
                    NodeSessionModel,
                    f"node-session.{dispatch_id}",
                )
                assert flow is not None
                assert dispatch is not None
                assert node_session is not None
                assert flow.status == "paused"
                assert flow.current_open_dispatch_id is None
                assert dispatch.control_state == "fenced"
                assert dispatch.delivery_status == "transport_ambiguous"
                assert node_session.session_status == "fenced"
                paused = await runtime_flow_read(session, task_id)
                resumed = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=paused.active_flow_revision_id,
                )
                await session.commit()
                assert resumed.status.value == "running"
                replacement_dispatch_id = flow.current_open_dispatch_id

            async with api.session_factory() as session:
                original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                replacement_dispatch_id = flow.current_open_dispatch_id
                replacement_dispatch = await session.get(
                    DispatchTurnModel,
                    replacement_dispatch_id,
                )
                assert original_dispatch is not None
                assert replacement_dispatch is not None
                assert replacement_dispatch.dispatch_id != dispatch_id
                assert replacement_dispatch.previous_dispatch_id == dispatch_id
                assert (
                    original_dispatch.superseded_by_dispatch_id == replacement_dispatch.dispatch_id
                )
                assert replacement_dispatch.attempt_id == original_dispatch.attempt_id

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "transport_ambiguous"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase4a_cancelled_timeout_is_fenced_and_clears_current_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase4a_cancel_timeout_cleanup"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-4a-cancel-timeout-cleanup",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)

            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                cancelled = await cancel_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()
                assert cancelled.status.value == "cancelled"

            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                node_session = await session.get(
                    NodeSessionModel,
                    f"node-session.{dispatch_id}",
                )
                assert flow is not None
                assert dispatch is not None
                assert node_session is not None
                assert flow.status == "cancelled"
                assert flow.current_open_dispatch_id is None
                assert dispatch.control_state == "fenced"
                assert dispatch.delivery_status == "transport_ambiguous"
                assert node_session.session_status == "fenced"

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "transport_ambiguous"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase4a_parent_redispatch_reuses_gateway_session_after_worker_green(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase4a_parent_same_session_redispatch"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-4a-parent-same-session-redispatch",
            workflow_key="minimal-implement-change",
        )

        async with phase3_runtime_api(config_path) as api:
            (
                _initial_root_dispatch_id,
                initial_root_gateway_session_key,
                initial_root_gateway_run_id,
                active_flow_revision_id,
                child_dispatch_id,
                child_gateway_session_key,
            ) = await prepare_parent_same_session_case(
                api,
                task_id=task_id,
                task_root=task_root,
            )
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=child_dispatch_id,
                ),
            )
            await finish_parent_same_session_case(
                api,
                task_id=task_id,
                active_flow_revision_id=active_flow_revision_id,
                child_dispatch_id=child_dispatch_id,
                child_gateway_session_key=child_gateway_session_key,
                initial_root_gateway_session_key=initial_root_gateway_session_key,
                initial_root_gateway_run_id=initial_root_gateway_run_id,
            )

            agent_requests = [
                request
                for request in openclaw_gateway_test_server.requests
                if request.method == "agent"
            ]
            assert len(agent_requests) == 3
            assert agent_requests[0].params["sessionKey"] == initial_root_gateway_session_key
            assert agent_requests[1].params["sessionKey"] == child_gateway_session_key
            assert agent_requests[2].params["sessionKey"] == initial_root_gateway_session_key
            assert (
                agent_requests[2].params["idempotencyKey"]
                != agent_requests[0].params["idempotencyKey"]
            )
    finally:
        await dispose_db_engine()
