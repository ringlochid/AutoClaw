from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime import continue_runtime_flow
from autoclaw.runtime.post_commit import drive_runtime_until
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.operator_auth_headers import OPERATOR_HEADERS
from tests.helpers.runtime_dispatch_support import current_open_dispatch_id, stage_child_yield
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    pause_flow,
    prepare_runtime_db,
    runtime_api_context,
    set_dispatch_drain_timeout,
)
from tests.integration.runtime.control.boundary_support import (
    assert_pause_resumption_state,
    assert_pause_wait_state,
    pause_flow_until_abort_requested,
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


async def _dispatch_fenced_and_cleared(
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
            and flow.current_open_dispatch_id is None
            and dispatch.control_state == "fenced"
        )


@pytest.mark.asyncio
async def test_pause_waits_for_inactivity_proof_before_reopening_dispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_pause"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-pause",
        )

        async with runtime_api_context(config_path) as api:
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
            assert await control_task_events(api.client, task_id=task_id) == [
                expected_control_task_event("task_paused", "paused")
            ]
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )
            await drive_runtime_until(
                lambda: _dispatch_fenced_and_cleared(
                    api.session_factory,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                ),
                task_id=task_id,
                max_cycles=40,
            )
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
            assert await control_task_events(api.client, task_id=task_id) == [
                expected_control_task_event("task_paused", "paused"),
                expected_control_task_event("task_resumed", "running"),
            ]
    finally:
        await dispose_db_engine()


async def control_task_events(
    client: AsyncClient,
    *,
    task_id: str,
) -> list[dict[str, object]]:
    response = await client.get(
        f"/control/tasks/{task_id}/events",
        headers=OPERATOR_HEADERS,
    )
    assert response.status_code == 200
    return [
        {
            "event_type": event["event_type"],
            "event_source": event["event_source"],
            "actor_ref": event["actor_ref"],
            "payload": event["payload"],
        }
        for event in response.json()["items"]
        if event["event_type"] in {"task_paused", "task_resumed", "task_cancelled"}
    ]


def expected_control_task_event(
    event_type: str,
    status: str,
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "event_source": "control_api",
        "actor_ref": None,
        "payload": {"status": status},
    }


@pytest.mark.asyncio
async def test_continue_rejects_yield_history_without_semantic_currentness(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_missing_semantic_resume"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-missing-semantic-resume",
        )

        async with runtime_api_context(config_path) as api:
            active_flow_revision_id = await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            paused = await pause_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert paused.status_code == 200
            paused_flow_revision_id = paused.json()["flow"]["active_flow_revision_id"]
            paused_dispatch_id = await current_open_dispatch_id(
                api.session_factory,
                task_id=task_id,
            )

            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=paused_dispatch_id,
                ),
            )
            await drive_runtime_until(
                lambda: _dispatch_fenced_and_cleared(
                    api.session_factory,
                    task_id=task_id,
                    dispatch_id=paused_dispatch_id,
                ),
                task_id=task_id,
                max_cycles=40,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                flow.current_node_key = None
                await session.commit()

            async with api.session_factory() as session:
                with pytest.raises(ValueError, match="current semantic target is incomplete"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=paused_flow_revision_id,
                    )
    finally:
        await dispose_db_engine()
