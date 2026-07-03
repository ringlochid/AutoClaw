from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import (
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
    ProviderEventRecordModel,
)
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime import (
    cancel_runtime_flow,
    runtime_flow_read,
)
from autoclaw.runtime.post_commit import (
    drive_runtime_once,
    drive_runtime_until,
    stop_runtime_effect_runner,
)
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_api_context,
    set_dispatch_drain_timeout,
)
from tests.helpers.runtime_support.dispatch import (
    current_open_dispatch_id,
    delivery_state_path,
    read_json,
    stage_child_yield,
)
from tests.integration.gateway.foreground_lifecycle_support import (
    assert_pause_dispatch_fenced_after_wait_ok,
    assert_pause_timeout_replacement_dispatch,
    continue_fenced_paused_dispatch,
    dispatch_fenced_and_cleared,
    force_pause_timeout_fence,
    pause_dispatch_and_assert_abort_requested,
    wait_ok_payload_for_dispatch,
)
from tests.integration.gateway.redispatch_support import (
    finish_parent_same_session_case,
    prepare_parent_same_session_case,
)


@pytest.mark.asyncio
async def test_accepted_run_without_callback_is_polled_to_terminal(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_terminal_without_callback"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-terminal-without-callback",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )

            await drive_runtime_until(
                lambda: dispatch_fenced_and_cleared(
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
async def test_pause_uses_gateway_abort_and_wait_before_fencing(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_pause_abort_wait"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-pause-abort-wait",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await pause_dispatch_and_assert_abort_requested(
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
                await wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )
            await assert_pause_dispatch_fenced_after_wait_ok(
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
async def test_gateway_wait_timeout_transitions_boundary_dispatch_to_abort_requested(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_wait_timeout_abort_requested"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-wait-timeout-ambiguous",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="change_subtree",
            )
            await stop_runtime_effect_runner()
            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                initial_control_state = dispatch.control_state
                assert initial_control_state in {"live", "abort_requested"}
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()

            await drive_runtime_once(task_id=task_id)

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
                assert flow.current_node_key == "change_subtree"
                if initial_control_state == "live":
                    assert dispatch.control_state == "abort_requested"
                    assert dispatch.control_state_reason == "boundary:yield:abort_requested"
                    assert provider_events[-1].event_kind in {"tool_event", "accepted"}
                else:
                    assert dispatch.control_state == "fenced"
                    assert dispatch.control_state_reason == (
                        "boundary:yield:abort_requested:timed_out"
                    )
                    assert provider_events[-1].event_kind == "transport_timeout"

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            if initial_control_state == "live":
                assert delivery_state["transport_state"] == "accepted"
            else:
                assert delivery_state["transport_state"] == "transport_ambiguous"
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_paused_timeout_is_fenced_and_continue_reopens_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_pause_timeout_cleanup"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-pause-timeout-cleanup",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await force_pause_timeout_fence(
                api,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )
            await continue_fenced_paused_dispatch(
                api,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )
            await assert_pause_timeout_replacement_dispatch(
                api,
                dispatch_id=dispatch_id,
                task_id=task_id,
                task_root=task_root,
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_cancelled_timeout_is_fenced_and_clears_current_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_cancel_timeout_cleanup"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-cancel-timeout-cleanup",
        )

        async with runtime_api_context(config_path) as api:
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

            await drive_runtime_until(
                lambda: dispatch_fenced_and_cleared(
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
async def test_parent_redispatch_reuses_gateway_session_after_worker_green(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_parent_same_session_redispatch"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-parent-same-session-redispatch",
            workflow_key="bounded-change",
        )

        async with runtime_api_context(config_path) as api:
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
                await wait_ok_payload_for_dispatch(
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
