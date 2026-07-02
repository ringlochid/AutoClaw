from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import autoclaw.runtime.projection.manifest.materialization as manifest_materialization
import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.runtime.routes.support import (
    assert_operator_current_paths,
    assign_child,
    continue_into_child_dispatch,
    launch_route_task,
    runtime_route_context,
    yield_boundary,
)
from tests.integration.runtime.routes.surface_contract_support import (
    assert_waiting_operator_surfaces,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


def _set_gateway_wait_ok(openclaw_gateway_test_server: LocalGatewayTestServer) -> None:
    openclaw_gateway_test_server.queue_method_payloads(
        "agent.wait",
        agent_wait_fixture(status="ok"),
    )


async def test_runtime_routes_wait_for_manifest_materialization_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_async_after_return",
            task_root_name="task-root",
        )
        manifest_started = asyncio.Event()
        release_manifest = asyncio.Event()
        materialize_manifest = manifest_materialization.materialize_manifest

        async def block_manifest_materialization(session: Any, task_id: str) -> Any:
            if task_id == task.task_id:
                manifest_started.set()
                await release_manifest.wait()
            return await materialize_manifest(session, task_id)

        monkeypatch.setattr(
            manifest_materialization, "materialize_manifest", block_manifest_materialization
        )
        assign_task = asyncio.create_task(assign_child(context, task))
        await asyncio.wait_for(manifest_started.wait(), timeout=3.0)
        assert not assign_task.done()
        release_manifest.set()
        assign_response = await asyncio.wait_for(assign_task, timeout=2.0)
        assert assign_response.status_code == 200


async def test_runtime_routes_reject_unauthorized_invalid_and_missing_reads(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        await launch_route_task(context, task_id="task_2026_0044", task_root_name="task-root")

        unauthorized_runtime = await context.client.get("/runtime/tasks")
        assert unauthorized_runtime.status_code == 401
        assert unauthorized_runtime.json()["detail"]["code"] == "illegal_caller"

        invalid_runtime_query = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"limit": 0},
        )
        assert invalid_runtime_query.status_code == 400
        assert invalid_runtime_query.json()["code"] == "invalid_request_shape"

        missing_runtime = await context.client.get(
            "/runtime/tasks/task_missing",
            headers=context.operator_headers,
        )
        assert missing_runtime.status_code == 404
        assert missing_runtime.json()["detail"]["code"] == "missing_resource"
        assert missing_runtime.json()["detail"]["suggested_next_step"] == (
            "Verify the task, flow, or dispatch id and reread the current runtime surface "
            "before retrying this request."
        )

        missing_observability = await context.client.get(
            "/observability/tasks/task_missing/delivery-state",
            headers=context.operator_headers,
        )
        assert missing_observability.status_code == 404
        assert missing_observability.json()["detail"]["code"] == "missing_resource"
        assert missing_observability.json()["detail"]["suggested_next_step"] == (
            "Verify the task, flow, or dispatch id and reread the current runtime surface "
            "before retrying this request."
        )


async def test_runtime_routes_surface_waiting_root_reads_after_yield(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    openclaw_gateway_test_server.set_default_method_payload(
        "agent.wait",
        agent_wait_fixture(status="timeout"),
    )
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_2026_0044",
            task_root_name="task-root",
        )

        runtime_list = await context.client.get("/runtime/tasks", headers=context.operator_headers)
        assert runtime_list.status_code == 200
        assert runtime_list.json()["items"][0]["task_id"] == task.task_id

        runtime_read = await context.client.get(
            f"/runtime/tasks/{task.task_id}",
            headers=context.operator_headers,
        )
        assert runtime_read.status_code == 200
        assert runtime_read.json()["current_node_key"] == "root"

        assign_response = await assign_child(context, task)
        assert assign_response.status_code == 200

        yielded = await yield_boundary(context, task)
        assert yielded.status_code == 200
        assert yielded.json()["flow"]["current_node_key"] == "implementation_subtree"

        waiting_runtime_read = await context.client.get(
            f"/runtime/tasks/{task.task_id}",
            headers=context.operator_headers,
        )
        assert waiting_runtime_read.status_code == 200
        assert waiting_runtime_read.json()["current_node_key"] == "implementation_subtree"

        waiting_runtime_list = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"q": task.task_id},
        )
        assert waiting_runtime_list.status_code == 200
        assert (
            waiting_runtime_list.json()["items"][0]["current_node_key"] == "implementation_subtree"
        )

        await assert_waiting_operator_surfaces(context, task)


async def test_runtime_routes_surface_child_snapshot_and_trace_after_continue(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_2026_0044",
            task_root_name="task-root",
        )

        assign_response = await assign_child(context, task)
        assert assign_response.status_code == 200
        yielded = await yield_boundary(context, task)
        assert yielded.status_code == 200
        _set_gateway_wait_ok(openclaw_gateway_test_server)

        continued_task = await continue_into_child_dispatch(context, task)

        snapshot = await context.client.get(
            f"/operator/tasks/{continued_task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        assert snapshot.status_code == 200
        snapshot_json = snapshot.json()
        assert snapshot_json["flow"]["current_node_key"] == "implementation_subtree"
        assert snapshot_json["top_actionable_items"][0]["suggested_action"] is None
        assert (
            snapshot_json["top_actionable_items"][0]["current_paths"]
            == snapshot_json["current_paths"]
        )
        assert_operator_current_paths(snapshot_json["current_paths"])

        trace = await context.client.get(
            f"/operator/tasks/{continued_task.task_id}/trace",
            headers=context.operator_headers,
            params={"scope": "current", "q": "implementation_subtree", "limit": 1},
        )
        assert trace.status_code == 200
        trace_json = trace.json()
        assert trace_json["scope"] == "current"
        assert trace_json["dispatch_history"][0]["node_key"] == "implementation_subtree"
        assert trace_json["dispatch_history"][0]["delivery_status"] == "accepted"
        graph_nodes = {node["node_key"]: node for node in trace_json["graph_nodes"]}
        assert "implementation_subtree" in graph_nodes["root"]["child_node_keys"]
        assert graph_nodes["implementation_subtree"]["parent_node_key"] == "root"
        assert trace_json["dependency_edges"]
        assert all(
            edge["provider_node_key"] != edge["consumer_node_key"]
            for edge in trace_json["dependency_edges"]
        )
        assert trace_json["next_cursor"] is None
        assert_operator_current_paths(trace_json["current_paths"])


async def test_runtime_routes_reject_parent_tool_path_body_mismatch(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_callback_tool_mismatch",
            task_root_name="task-root",
        )

        mismatch = await context.client.post(
            f"/callback/tasks/{task.task_id}/tools/assign_child",
            params={"session_key": task.session_key},
            json={
                "tool_name": "release_green",
                "payload": {},
                "expected_structural_revision_id": task.active_flow_revision_id,
            },
        )
        assert mismatch.status_code == 400
        detail = mismatch.json()["detail"]
        assert detail["code"] == "invalid_request_shape"
        assert detail["summary"] == "tool_name path/body mismatch"


async def test_runtime_routes_require_explicit_callback_session_key(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_callback_requires_query_session_key",
            task_root_name="task-root",
        )

        missing_session_key = await context.client.post(
            f"/callback/tasks/{task.task_id}/boundary",
            json={"boundary": "yield"},
        )
        assert missing_session_key.status_code == 400
        detail = missing_session_key.json()["detail"]
        assert detail["code"] == "invalid_request_shape"
        assert detail["summary"] == "callback session_key is required"
