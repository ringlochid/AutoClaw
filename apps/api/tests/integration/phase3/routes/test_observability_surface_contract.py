from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from app.db import FlowModel
from app.runtime.effects import drive_runtime_once, wait_for_runtime_effects
from app.runtime.openclaw.fixtures import agent_wait_fixture
from tests.integration.phase3.routes.observability_support import (
    assert_delivery_payload,
    assert_provider_event_payloads,
    observability_payloads,
)
from tests.integration.phase3.routes.support import (
    assert_operator_current_paths,
    assign_child,
    continue_into_child_dispatch,
    launch_route_task,
    phase3_route_context,
    yield_boundary,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


def _set_gateway_wait_ok(openclaw_gateway_test_server: LocalGatewayTestServer) -> None:
    openclaw_gateway_test_server.queue_method_payloads(
        "agent.wait",
        agent_wait_fixture(status="ok"),
    )


async def _wait_until_current_dispatch_clears(context: Any, *, task_id: str) -> None:
    for _ in range(40):
        async with context.session_factory() as session:
            flow = await session.get(FlowModel, f"flow.{task_id}")
            assert flow is not None
            if flow.current_open_dispatch_id is None:
                return
        await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
        await drive_runtime_once(task_id=task_id)
        await asyncio.sleep(0.05)
    raise AssertionError(f"task '{task_id}' kept a current_open_dispatch_id unexpectedly")


async def _assert_semantic_current_paths_after_close(context: Any, *, continued_task: Any) -> None:
    snapshot = await context.client.get(
        f"/operator/tasks/{continued_task.task_id}/snapshot",
        headers=context.operator_headers,
    )
    assert snapshot.status_code == 200
    snapshot_json = snapshot.json()
    assert_operator_current_paths(
        snapshot_json["current_paths"],
        include_dispatch_support=False,
    )
    assert (
        snapshot_json["top_actionable_items"][0]["current_paths"] == snapshot_json["current_paths"]
    )

    trace = await context.client.get(
        f"/operator/tasks/{continued_task.task_id}/trace",
        headers=context.operator_headers,
        params={"scope": "current", "q": "implementation_subtree", "limit": 1},
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    assert_operator_current_paths(
        trace_json["current_paths"],
        include_dispatch_support=False,
    )
    assert trace_json["dispatch_history"][0]["node_key"] == "implementation_subtree"


async def test_phase3_runtime_routes_materialize_observability_files_from_dispatch_rows(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    async with phase3_route_context(tmp_path) as context:
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

        trace = await context.client.get(
            f"/operator/tasks/{continued_task.task_id}/trace",
            headers=context.operator_headers,
            params={"scope": "current", "q": "implementation_subtree", "limit": 1},
        )
        assert trace.status_code == 200
        trace_json = trace.json()
        payloads = await observability_payloads(context, continued_task)
        assert_delivery_payload(payloads["delivery-state.json"], trace_json)
        await assert_provider_event_payloads(
            context,
            payloads["provider-events.ndjson"],
            trace_json,
        )


async def test_phase3_runtime_routes_reject_stale_callback_after_continue(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    async with phase3_route_context(tmp_path) as context:
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
        await continue_into_child_dispatch(context, task)

        stale_callback = await yield_boundary(context, task)
        assert stale_callback.status_code == 409
        assert stale_callback.json()["detail"]["code"] == "stale_dispatch"
        assert stale_callback.json()["detail"]["suggested_next_step"] == (
            "Reread the current dispatch context and retry only if this node is still the "
            "current caller for an open dispatch."
        )


async def test_phase3_runtime_routes_observability_reads_do_not_rematerialize_dispatch_files(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_observability_read_only",
            task_root_name="task-root",
        )
        delivery_path = (
            task.task_root
            / "_runtime"
            / "dispatch"
            / task.current_open_dispatch_id
            / "delivery-state.json"
        )
        dispatch_root = task.task_root / "_runtime" / "dispatch"
        shutil.rmtree(dispatch_root)

        response = await context.client.get(
            f"/observability/tasks/{task.task_id}/delivery-state",
            headers=context.operator_headers,
        )
        assert response.status_code == 200
        assert Path(str(response.json()["path"])) == delivery_path
        snapshot = await context.client.get(
            f"/operator/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        assert snapshot.status_code == 200
        await asyncio.sleep(0.1)
        assert not delivery_path.exists()
        assert not dispatch_root.exists()


async def test_phase3_runtime_routes_keep_snapshot_and_trace_current_paths_semantic_when_no_open_dispatch(  # noqa: E501
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_semantic_current_paths",
            task_root_name="task-root",
        )
        assign_response = await assign_child(context, task)
        assert assign_response.status_code == 200
        yielded = await yield_boundary(context, task)
        assert yielded.status_code == 200
        _set_gateway_wait_ok(openclaw_gateway_test_server)
        continued_task = await continue_into_child_dispatch(context, task)

        latest_trace = await context.client.get(
            f"/operator/tasks/{continued_task.task_id}/trace",
            headers=context.operator_headers,
            params={"scope": "current", "q": "implementation_subtree", "limit": 1},
        )
        assert latest_trace.status_code == 200
        latest_trace_json = latest_trace.json()
        assert latest_trace_json["dispatch_history"][0]["node_key"] == "implementation_subtree"
        async with context.session_factory() as session:
            flow = await session.get(FlowModel, f"flow.{continued_task.task_id}")
            assert flow is not None
            assert flow.current_open_dispatch_id is not None
            latest_dispatch_id = flow.current_open_dispatch_id

        _set_gateway_wait_ok(openclaw_gateway_test_server)
        await _wait_until_current_dispatch_clears(
            context,
            task_id=continued_task.task_id,
        )
        await _assert_semantic_current_paths_after_close(
            context,
            continued_task=continued_task,
        )

        observability = await context.client.get(
            f"/observability/tasks/{continued_task.task_id}/delivery-state",
            headers=context.operator_headers,
        )
        assert observability.status_code == 200
        observability_path = Path(str(observability.json()["path"]))
        delivery_path = (
            continued_task.task_root
            / "_runtime"
            / "dispatch"
            / latest_dispatch_id
            / "delivery-state.json"
        )
        assert observability_path == delivery_path
        assert delivery_path.name == "delivery-state.json"
        assert delivery_path.parent.name.startswith("dispatch.")
