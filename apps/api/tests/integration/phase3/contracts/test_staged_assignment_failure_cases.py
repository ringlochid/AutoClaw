from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.db import AssignmentModel, DispatchTurnModel, FlowModel
from autoclaw.db.session import dispose_db_engine
from autoclaw.runtime.openclaw.fixtures import agent_wait_fixture
from sqlalchemy import select
from tests.helpers.runtime_seed import load_workflow_definition
from tests.integration.phase3.dispatch_support import mark_dispatch_provider_completed
from tests.integration.phase3.runtime_support import (
    Phase3RuntimeApi,
    assign_child,
    boundary,
    continue_flow,
    current_session_key,
    pause_flow,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    runtime_read_json,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


async def _prepare_paused_incomplete_staged_assignment(
    api: Phase3RuntimeApi,
    *,
    task_id: str,
) -> tuple[str, str]:
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
    )
    runtime_read = await runtime_read_json(api.client, task_id)
    assign = await assign_child(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        child_node_key="implementation_subtree",
        active_flow_revision_id=runtime_read["active_flow_revision_id"],
    )
    assert assign.status_code == 200
    yielded = await boundary(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    assert yielded.json()["flow"]["current_node_key"] == "implementation_subtree"
    runtime_after_yield = await runtime_read_json(api.client, task_id)
    yielded_flow_revision_id = runtime_after_yield["active_flow_revision_id"]

    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        paused_dispatch_id = flow.current_open_dispatch_id
        dispatch = await session.get(DispatchTurnModel, paused_dispatch_id)
        assert dispatch is not None
        assert dispatch.assignment_id is not None

    paused = await pause_flow(
        api.client,
        task_id=task_id,
        active_flow_revision_id=yielded_flow_revision_id,
    )
    assert paused.status_code == 200, paused.json()

    async with api.session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, paused_dispatch_id)
        assert dispatch is not None
        assert dispatch.staged_child_assignment_id is not None
        assignment = await session.get(AssignmentModel, dispatch.staged_child_assignment_id)
        assert assignment is not None
        assignment.current_attempt_id = None
        await session.commit()

    return paused_dispatch_id, yielded_flow_revision_id


@pytest.mark.asyncio
async def test_parent_retry_boundary_maps_to_illegal_caller(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_parent_retry_illegal"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            retry = await boundary(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                boundary_name="retry",
            )
            assert retry.status_code == 422
            detail = retry.json()["detail"]
            assert detail["code"] == "illegal_caller"
            assert detail["summary"] == "parent/root retry is illegal"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_incomplete_staged_child_continue"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            (
                paused_dispatch_id,
                yielded_flow_revision_id,
            ) = await _prepare_paused_incomplete_staged_assignment(
                api,
                task_id=task_id,
            )

            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                agent_wait_fixture(status="ok"),
            )
            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=paused_dispatch_id,
            )
            resumed = await continue_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=yielded_flow_revision_id,
            )
            assert resumed.status_code == 422
            detail = resumed.json()["detail"]
            assert detail["code"] == "illegal_state"
            assert detail["summary"] == "current semantic target is incomplete"
            assert "repair the incomplete semantic target" in detail["suggested_next_step"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_yield_maps_incomplete_staged_child_assignment_to_illegal_state(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_incomplete_staged_child_yield"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                child_node_key="implementation_subtree",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert assign.status_code == 200

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
                assert dispatch is not None
                assert dispatch.staged_child_assignment_id is not None
                assignment = await session.get(AssignmentModel, dispatch.staged_child_assignment_id)
                assert assignment is not None
                assignment.current_attempt_id = None
                await session.commit()

            yielded = await boundary(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                boundary_name="yield",
            )
            assert yielded.status_code == 422
            detail = yielded.json()["detail"]
            assert detail["code"] == "illegal_state"
            assert detail["summary"] == "staged child assignment is incomplete"
            assert (
                "repair or restage a complete child continuation" in detail["suggested_next_step"]
            )
    finally:
        await dispose_db_engine()


__all__ = [
    "test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state",
    "test_parent_retry_boundary_maps_to_illegal_caller",
    "test_yield_maps_incomplete_staged_child_assignment_to_illegal_state",
]
