from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel, NodeSessionModel
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_api_context,
)
from tests.helpers.runtime_support.dispatch import mark_dispatch_provider_completed
from tests.helpers.runtime_support.dispatch_progression import (
    assert_parent_redispatch_after_worker_green,
)
from tests.integration.gateway.redispatch_support import (
    assert_parent_redispatch_falls_back_to_fresh_root_session,
    prepare_parent_same_session_case,
)


async def remove_parent_node_session(api: Any, *, dispatch_id: str) -> None:
    async with api.session_factory() as session:
        node_session = await session.get(
            NodeSessionModel,
            f"node-session.{dispatch_id}",
        )
        assert node_session is not None
        await session.delete(node_session)
        await session.commit()


async def set_wait_ok_for_dispatch(
    api: Any,
    *,
    dispatch_id: str,
    gateway_server: LocalGatewayTestServer,
) -> None:
    async with api.session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert isinstance(dispatch.gateway_run_id, str)
        gateway_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="ok", run_id=dispatch.gateway_run_id),
        )


def assert_fresh_session_agent_requests(
    gateway_server: LocalGatewayTestServer,
    *,
    child_gateway_session_key: str,
    initial_root_gateway_session_key: str,
) -> None:
    agent_requests = [request for request in gateway_server.requests if request.method == "agent"]
    assert len(agent_requests) == 3
    assert agent_requests[0].params["sessionKey"] == initial_root_gateway_session_key
    assert agent_requests[1].params["sessionKey"] == child_gateway_session_key
    assert agent_requests[2].params["sessionKey"] not in {
        initial_root_gateway_session_key,
        child_gateway_session_key,
    }
    assert agent_requests[2].params["idempotencyKey"] != agent_requests[0].params["idempotencyKey"]


@pytest.mark.asyncio
async def test_parent_redispatch_falls_back_to_fresh_session_after_continuity_loss(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_parent_fresh_session_fallback"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-parent-fresh-session-fallback",
            workflow_key="minimal-implement-change",
        )

        async with runtime_api_context(config_path) as api:
            (
                initial_root_dispatch_id,
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
            await remove_parent_node_session(
                api,
                dispatch_id=initial_root_dispatch_id,
            )
            await set_wait_ok_for_dispatch(
                api,
                dispatch_id=child_dispatch_id,
                gateway_server=openclaw_gateway_test_server,
            )
            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=child_dispatch_id,
            )
            await assert_parent_redispatch_after_worker_green(
                session_factory=api.session_factory,
                task_id=task_id,
                active_flow_revision_id=active_flow_revision_id,
                child_dispatch_id=child_dispatch_id,
            )
            await assert_parent_redispatch_falls_back_to_fresh_root_session(
                api.session_factory,
                task_id=task_id,
                child_dispatch_id=child_dispatch_id,
                child_gateway_session_key=child_gateway_session_key,
                initial_root_gateway_session_key=initial_root_gateway_session_key,
                initial_root_gateway_run_id=initial_root_gateway_run_id,
            )
            assert_fresh_session_agent_requests(
                openclaw_gateway_test_server,
                child_gateway_session_key=child_gateway_session_key,
                initial_root_gateway_session_key=initial_root_gateway_session_key,
            )
    finally:
        await dispose_db_engine()
