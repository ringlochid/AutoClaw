from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from autoclaw.main import create_app
from autoclaw.runtime.post_commit import drive_runtime_once
from httpx import ASGITransport, AsyncClient
from tests.e2e.phase2.minimal_runtime_lane_support import (
    add_child_and_reread_manifest,
    assert_gateway_dispatch_binding,
    assign_child_and_yield,
    current_session_key,
    runtime_payload,
    snapshot_dispatch_dir,
)
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase3.runtime_harness.child_dispatch import (
    current_session_key_after_dispatch_progress_for_node,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


def assert_agent_dispatch_ids(
    gateway_server: LocalGatewayTestServer,
    *,
    root_session_key: str,
    child_session_key: str,
) -> None:
    agent_requests = [request for request in gateway_server.requests if request.method == "agent"]
    assert len(agent_requests) == 2
    assert agent_requests[0].params["sessionKey"] == root_session_key
    assert agent_requests[1].params["sessionKey"] == child_session_key


async def _launch_minimal_runtime(runtime: Any, *, task_id: str) -> None:
    async with runtime.session_factory() as session:
        await launch_seeded_runtime(
            session,
            task_id=task_id,
            task_root=runtime.paths.task_root,
            task_compose=task_compose_payload("minimal-implement-change"),
            compiler_version="phase-2-e2e-minimal",
        )


async def _drive_minimal_root_to_child(
    client: AsyncClient,
    *,
    openclaw_gateway_test_server: LocalGatewayTestServer,
    runtime: Any,
    task_id: str,
    initial_runtime_payload: dict[str, object],
) -> tuple[str, str]:
    root_session_key = await current_session_key(runtime.session_factory, task_id=task_id)
    root_dispatch = await assert_gateway_dispatch_binding(
        runtime.session_factory,
        task_id=task_id,
        session_key=root_session_key,
        expected_run_id="run-1",
    )
    refreshed_flow_revision_id = await add_child_and_reread_manifest(
        client,
        task_id=task_id,
        session_key=root_session_key,
        active_flow_revision_id=str(initial_runtime_payload["active_flow_revision_id"]),
        task_root=runtime.paths.task_root,
    )
    root_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=runtime.session_factory,
        task_id=task_id,
        client=client,
        expected_active_flow_revision_id=refreshed_flow_revision_id,
        expected_node_key="root",
    )
    yielded = await assign_child_and_yield(
        client,
        session_factory=runtime.session_factory,
        task_id=task_id,
        session_key=root_session_key,
        active_flow_revision_id=refreshed_flow_revision_id,
    )
    assert yielded["flow"]["current_node_key"] == "implement_change"
    child_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=runtime.session_factory,
        task_id=task_id,
        client=client,
        expected_active_flow_revision_id=str(yielded["flow"]["active_flow_revision_id"]),
        expected_node_key="implement_change",
    )
    child_dispatch = await assert_gateway_dispatch_binding(
        runtime.session_factory,
        task_id=task_id,
        session_key=child_session_key,
        expected_run_id="run-2",
    )
    assert_agent_dispatch_ids(
        openclaw_gateway_test_server,
        root_session_key=root_dispatch.gateway_session_key or "",
        child_session_key=child_dispatch.gateway_session_key or "",
    )
    return root_session_key, child_session_key


async def test_phase2_minimal_runtime_lane_bootstraps_and_materializes_one_child_path(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase2_e2e_minimal"

    async with phase2_runtime_context(tmp_path) as runtime:
        await _launch_minimal_runtime(runtime, task_id=task_id)

        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            initial_runtime_payload = await runtime_payload(client, task_id=task_id)
            assert initial_runtime_payload["workflow_key"] == "minimal-implement-change"
            assert initial_runtime_payload["current_node_key"] == "root"
            await drive_runtime_once(task_id=task_id)
            assert await asyncio.to_thread(
                Path(str(initial_runtime_payload["workflow_manifest_ref"]["path"])).is_file
            )

            root_dispatch_dir = await snapshot_dispatch_dir(
                client, task_id=task_id, expected_node_key="root"
            )
            assert root_dispatch_dir.name == "dispatch.task_phase2_e2e_minimal.root.01"

            _root_session_key, _child_session_key = await _drive_minimal_root_to_child(
                client,
                openclaw_gateway_test_server=openclaw_gateway_test_server,
                runtime=runtime,
                task_id=task_id,
                initial_runtime_payload=initial_runtime_payload,
            )
            continued = await runtime_payload(client, task_id=task_id)
            assert continued["current_node_key"] == "implement_change"
            child_dispatch_dir = await snapshot_dispatch_dir(
                client, task_id=task_id, expected_node_key="implement_change"
            )
            assert child_dispatch_dir != root_dispatch_dir
            runtime_after_continue = await runtime_payload(client, task_id=task_id)
            assert runtime_after_continue["current_node_key"] == "implement_change"
