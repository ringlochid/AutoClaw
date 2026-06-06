from __future__ import annotations

from autoclaw.runtime.post_commit import drive_runtime_once
from tests.integration.runtime.routes.support import (
    Phase3RouteContext,
    SeededRouteTask,
    assert_operator_current_paths,
)


async def assert_waiting_operator_surfaces(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> None:
    await drive_runtime_once(task_id=task.task_id)
    snapshot = await context.client.get(
        f"/operator/tasks/{task.task_id}/snapshot",
        headers=context.operator_headers,
    )
    assert snapshot.status_code == 200
    snapshot_json = snapshot.json()
    assert snapshot_json["flow"]["current_node_key"] == "implementation_subtree"
    assert_operator_current_paths(snapshot_json["current_paths"])

    trace = await context.client.get(
        f"/operator/tasks/{task.task_id}/trace",
        headers=context.operator_headers,
        params={"scope": "current", "q": "implementation_subtree", "limit": 1},
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    if trace_json["dispatch_history"]:
        assert trace_json["dispatch_history"][0]["node_key"] == "implementation_subtree"
    assert_operator_current_paths(trace_json["current_paths"])
