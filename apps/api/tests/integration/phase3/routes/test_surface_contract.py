from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from app.runtime.effects import wait_for_runtime_effects
from tests.integration.phase3.routes.observability_support import (
    assert_delivery_payload,
    assert_provider_event_payloads,
    observability_payloads,
)
from tests.integration.phase3.routes.support import (
    Phase3RouteContext,
    SeededRouteTask,
    assert_operator_current_paths,
    assert_operator_paths_exist,
    assign_child,
    continue_into_child_dispatch,
    launch_route_task,
    phase3_route_context,
    yield_boundary,
)


async def test_phase3_runtime_routes_return_before_manifest_effect_drain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.runtime.effects.worker as effect_worker

    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_async_after_return",
            task_root_name="task-root",
        )
        manifest_started = asyncio.Event()
        release_manifest = asyncio.Event()
        execute_effect = effect_worker.execute_runtime_effect

        async def block_manifest_effect(session_factory: Any, effect: Any) -> None:
            if (
                effect.effect_kind == "manifest_materialization"
                and effect.payload.get("task_id") == task.task_id
            ):
                manifest_started.set()
                await release_manifest.wait()
            await execute_effect(session_factory, effect)

        monkeypatch.setattr(effect_worker, "execute_runtime_effect", block_manifest_effect)
        assign_response = await asyncio.wait_for(assign_child(context, task), timeout=2.0)
        assert assign_response.status_code == 200
        await asyncio.wait_for(manifest_started.wait(), timeout=1.0)
        release_manifest.set()
        await wait_for_runtime_effects(task_id=task.task_id)


async def test_phase3_runtime_routes_reject_unauthorized_invalid_and_missing_reads(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
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


async def test_phase3_runtime_routes_surface_waiting_root_reads_after_yield(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
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
        assert yielded.json()["flow"]["current_node_key"] == "root"

        waiting_runtime_read = await context.client.get(
            f"/runtime/tasks/{task.task_id}",
            headers=context.operator_headers,
        )
        assert waiting_runtime_read.status_code == 200
        assert waiting_runtime_read.json()["current_node_key"] == "root"

        waiting_runtime_list = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"q": task.task_id},
        )
        assert waiting_runtime_list.status_code == 200
        assert waiting_runtime_list.json()["items"][0]["current_node_key"] == "root"

        await assert_waiting_operator_surfaces(context, task)


async def test_phase3_runtime_routes_surface_child_snapshot_and_trace_after_continue(
    tmp_path: Path,
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
        await assert_operator_paths_exist(snapshot_json["current_paths"])

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
        assert trace_json["next_cursor"] is None
        assert_operator_current_paths(trace_json["current_paths"])
        await assert_operator_paths_exist(trace_json["current_paths"])


async def test_phase3_runtime_routes_materialize_observability_files_from_dispatch_rows(
    tmp_path: Path,
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
            context, payloads["provider-events.ndjson"], trace_json
        )


async def test_phase3_runtime_routes_reject_stale_callback_after_continue(
    tmp_path: Path,
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
        await continue_into_child_dispatch(context, task)

        stale_callback = await yield_boundary(context, task)
        assert stale_callback.status_code == 409
        assert stale_callback.json()["detail"]["code"] == "stale_dispatch"
        assert stale_callback.json()["detail"]["suggested_next_step"] == (
            "Reread the current dispatch context and callback binding, then retry only if this "
            "node is still the current caller for an open dispatch."
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
        delivery_path.unlink()

        response = await context.client.get(
            f"/observability/tasks/{task.task_id}/delivery-state",
            headers=context.operator_headers,
        )
        assert response.status_code == 200
        assert Path(str(response.json()["path"])) == delivery_path
        await asyncio.sleep(0.1)
        assert not delivery_path.exists()


async def assert_waiting_operator_surfaces(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> None:
    await wait_for_runtime_effects(task_id=task.task_id)
    snapshot = await context.client.get(
        f"/operator/tasks/{task.task_id}/snapshot",
        headers=context.operator_headers,
    )
    assert snapshot.status_code == 200
    snapshot_json = snapshot.json()
    assert snapshot_json["flow"]["current_node_key"] == "root"
    assert_operator_current_paths(snapshot_json["current_paths"])

    trace = await context.client.get(
        f"/operator/tasks/{task.task_id}/trace",
        headers=context.operator_headers,
        params={"scope": "current", "q": "root", "limit": 1},
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    assert trace_json["dispatch_history"][0]["node_key"] == "root"
    assert_operator_current_paths(trace_json["current_paths"])
