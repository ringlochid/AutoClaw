from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, cast

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    SeededRouteTask,
    assign_child,
    launch_route_task,
    runtime_route_context,
    yield_boundary,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]
type JsonObject = dict[str, Any]


class SupportsDefaultGatewayWait(Protocol):
    def set_default_method_payload(self, method: str, payload: dict[str, object]) -> None: ...


async def test_control_task_events_include_launch_event_families_on_task_launch(
    tmp_path: Path,
    openclaw_gateway_test_server: SupportsDefaultGatewayWait,
) -> None:
    set_default_gateway_wait_payload(
        openclaw_gateway_test_server,
        agent_wait_fixture(status="ok"),
    )
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_launch_event_families",
            task_root_name="task-root",
        )

        launch_events = [
            event
            for event in await control_task_events(context, task_id=task.task_id)
            if event["event_type"]
            in {"task_started", "provider_resolution_recorded", "dispatch_opened"}
        ]
        assert [event["event_type"] for event in launch_events] == [
            "task_started",
            "provider_resolution_recorded",
            "dispatch_opened",
        ]

        task_started = launch_events[0]
        task_started_payload = event_payload(task_started)
        assert task_started["event_source"] == "controller"
        assert task_started["flow_revision_id"] == task.active_flow_revision_id
        assert task_started["dispatch_id"] is None
        assert task_started_payload["task_title"] == "Harden auth refresh flow"
        assert task_started_payload["workflow_key"] == "normal-parent-first-release"
        assert task_started_payload["initial_node_key"] == "root"
        assert workflow_manifest_name(task_started_payload) == "workflow-manifest.md"

        provider_resolution = launch_events[1]
        assert provider_resolution["event_source"] == "controller"
        assert provider_resolution["dispatch_id"] == task.current_open_dispatch_id
        assert event_payload(provider_resolution) == {
            "requested_provider": "openclaw",
            "resolved_provider": "openclaw",
            "dispatch_id": task.current_open_dispatch_id,
            "attempt_id": provider_resolution["attempt_id"],
        }

        dispatch_opened = launch_events[2]
        dispatch_opened_payload = event_payload(dispatch_opened)
        assert dispatch_opened["event_source"] == "controller"
        assert dispatch_opened["dispatch_id"] == task.current_open_dispatch_id
        assert dispatch_opened_payload["node_key"] == "root"
        assert dispatch_opened_payload["delivery_status"] == "accepted"
        assert dispatch_opened_payload["control_state"] == "live"
        assert dispatch_opened_payload["previous_dispatch_id"] is None
        assert workflow_manifest_name(dispatch_opened_payload) == "workflow-manifest.md"

        await cancel_route_task(context, task)


async def test_control_task_events_include_checkpoint_recorded_for_callback_checkpoint(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_checkpoint_event_family",
            task_root_name="task-root",
        )

        checkpoint = await context.client.post(
            f"/callback/tasks/{task.task_id}/checkpoint",
            params={"session_key": task.session_key},
            json={
                "checkpoint": {
                    "checkpoint_kind": "progress",
                    "handoff": {
                        "summary": "Recorded a root checkpoint for event coverage.",
                        "next_step": "Keep the current root dispatch open.",
                    },
                }
            },
        )
        assert checkpoint.status_code == 200

        checkpoint_events = [
            event
            for event in await control_task_events(context, task_id=task.task_id)
            if event["event_type"] == "checkpoint_recorded"
        ]
        assert len(checkpoint_events) == 1

        checkpoint_event = checkpoint_events[0]
        checkpoint_payload = event_payload(checkpoint_event)
        assert checkpoint_event["event_source"] == "node"
        assert checkpoint_event["flow_revision_id"] == task.active_flow_revision_id
        assert checkpoint_event["dispatch_id"] == task.current_open_dispatch_id
        assert checkpoint_event["node_key"] == "root"
        assert checkpoint_payload["checkpoint_kind"] == "progress"
        assert checkpoint_payload["outcome"] is None
        assert checkpoint_payload["summary"] == "Recorded a root checkpoint for event coverage."
        assert checkpoint_payload["next_step"] == "Keep the current root dispatch open."
        assert checkpoint_payload["blockers"] == []
        assert checkpoint_payload["risks"] == []
        assert checkpoint_payload["produced_artifacts"] == []
        assert checkpoint_payload["transient_refs"] == []
        assert checkpoint_payload["task_memory_search_hints"] == []
        assert ref_path_name(checkpoint_payload, "checkpoint_ref") == "latest-checkpoint.md"
        assert ref_path_name(checkpoint_payload, "latest_checkpoint_ref") == "latest-checkpoint.md"

        await cancel_route_task(context, task)


async def test_control_task_events_include_child_assignment_committed_after_accepted_yield(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_child_assignment_committed_event_family",
            task_root_name="task-root",
        )

        assign_response = await assign_child(context, task)
        assert assign_response.status_code == 200
        assign_payload = assign_response.json()

        yielded = await yield_boundary(context, task)
        assert yielded.status_code == 200

        events = await control_task_events(context, task_id=task.task_id)
        yield_boundary_event = next(
            event
            for event in events
            if event["event_type"] == "boundary_accepted"
            and event_payload(event)["boundary"] == "yield"
        )
        committed_event = next(
            event for event in events if event["event_type"] == "child_assignment_committed"
        )
        yield_payload = event_payload(yield_boundary_event)
        committed_payload = event_payload(committed_event)

        assert yield_boundary_event["event_seq"] < committed_event["event_seq"]
        assert yield_payload["previous_node_key"] == "root"
        assert yield_payload["next_node_key"] == "implementation_subtree"
        assert yield_payload["next_attempt_id"] == assign_payload["target_attempt_id"]
        assert yield_payload["resulting_flow_status"] == "running"
        assert yield_payload["requires_reopen_after_inactivity"] is True
        assert yield_payload["latest_checkpoint_ref"] is None
        assert committed_event["event_source"] == "controller"
        assert committed_event["dispatch_id"] == task.current_open_dispatch_id
        assert committed_event["attempt_id"] == assign_payload["target_attempt_id"]
        assert committed_event["node_key"] == "implementation_subtree"
        assert committed_payload == {
            "target_node_key": "implementation_subtree",
            "target_assignment_key": assign_payload["target_assignment_key"],
            "target_attempt_id": assign_payload["target_attempt_id"],
            "parent_node_key": "root",
            "source_dispatch_id": task.current_open_dispatch_id,
            "boundary": "yield",
        }

        await cancel_route_task(context, task)


async def test_control_task_events_include_structural_revision_adopted_for_update_child(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_update_child_event_family",
            task_root_name="task-root",
        )

        update_child_response = await context.client.post(
            f"/callback/tasks/{task.task_id}/tools/update_child",
            params={"session_key": task.session_key},
            json={
                "tool_name": "update_child",
                "payload": {
                    "child_node_key": "implementation_subtree",
                    "patch": {"description": "Updated child description for task-event coverage."},
                },
                "expected_structural_revision_id": task.active_flow_revision_id,
            },
        )
        assert update_child_response.status_code == 200
        update_child_payload = update_child_response.json()

        structural_events = [
            event
            for event in await control_task_events(context, task_id=task.task_id)
            if event["event_type"] == "structural_revision_adopted"
        ]
        assert len(structural_events) == 1

        structural_event = structural_events[0]
        structural_payload = event_payload(structural_event)
        assert structural_event["event_source"] == "node"
        assert (
            structural_event["flow_revision_id"]
            == update_child_payload["flow"]["active_flow_revision_id"]
        )
        assert structural_event["dispatch_id"] == task.current_open_dispatch_id
        assert structural_event["node_key"] == "root"
        assert structural_payload["operation"] == "update_child"
        assert structural_payload["previous_flow_revision_id"] == task.active_flow_revision_id
        assert (
            structural_payload["active_flow_revision_id"]
            == update_child_payload["flow"]["active_flow_revision_id"]
        )
        assert structural_payload["target_node_key"] == "implementation_subtree"
        assert structural_payload["affected_node_keys"] == ["implementation_subtree"]
        assert structural_payload["summary"] == "Updated child node 'implementation_subtree'."
        assert workflow_manifest_name(structural_payload) == "workflow-manifest.md"

        await cancel_route_task(
            context,
            task,
            expected_active_flow_revision_id=update_child_payload["flow"][
                "active_flow_revision_id"
            ],
        )


async def control_task_events(
    context: RuntimeRouteContext,
    *,
    task_id: str,
) -> list[JsonObject]:
    response = await context.client.get(
        f"/control/tasks/{task_id}/events",
        headers=context.operator_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert isinstance(items, list)
    return [cast(JsonObject, item) for item in items]


def event_payload(event: JsonObject) -> JsonObject:
    payload = event["payload"]
    assert isinstance(payload, dict)
    return cast(JsonObject, payload)


def workflow_manifest_name(payload: JsonObject) -> str:
    return ref_path_name(payload, "workflow_manifest_ref")


def ref_path_name(payload: JsonObject, key: str) -> str:
    ref = payload[key]
    assert isinstance(ref, dict)
    path = ref["path"]
    assert isinstance(path, str)
    return Path(path).name


async def cancel_route_task(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    expected_active_flow_revision_id: str | None = None,
) -> None:
    response = await context.client.post(
        f"/control/tasks/{task.task_id}/cancel",
        headers=context.operator_headers,
        params={
            "expected_active_flow_revision_id": (
                task.active_flow_revision_id
                if expected_active_flow_revision_id is None
                else expected_active_flow_revision_id
            )
        },
    )
    assert response.status_code == 200


def set_default_gateway_wait_payload(
    openclaw_gateway_test_server: SupportsDefaultGatewayWait,
    payload: dict[str, object],
) -> None:
    openclaw_gateway_test_server.set_default_method_payload("agent.wait", payload)
