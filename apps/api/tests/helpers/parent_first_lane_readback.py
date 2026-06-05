from __future__ import annotations

import asyncio
from pathlib import Path

from autoclaw.persistence import FlowModel

from tests.helpers.parent_first_lane_runtime import (
    OPERATOR_HEADERS,
    JsonMap,
    ParentFirstLaneDriver,
    json_map,
)
from tests.integration.phase4b.support_state_shapes import (
    assert_continuity_state_shape,
    assert_delivery_state_shape,
    assert_provider_event_shape,
    assert_watchdog_state_shape,
    load_json_payload,
    load_provider_event_payloads,
)

EXPECTED_OPERATOR_CURRENT_PATHS = (
    (
        "manifest",
        "workflow-manifest.md",
        "Whole-workflow visible contract for the current task.",
    ),
    (
        "delivery_state",
        "delivery-state.json",
        "Latest task-scoped delivery-state projection.",
    ),
    (
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    (
        "watchdog_state",
        "watchdog-state.json",
        "Latest task-scoped watchdog-state projection.",
    ),
    (
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)
OBSERVABILITY_ROUTES = (
    (
        "delivery-state",
        "delivery_state",
        "delivery-state.json",
        "Latest task-scoped delivery-state projection.",
    ),
    (
        "continuity-state",
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    (
        "watchdog-state",
        "watchdog_state",
        "watchdog-state.json",
        "Latest task-scoped watchdog-state projection.",
    ),
    (
        "provider-events",
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)


def assert_operator_current_paths(entries: list[JsonMap]) -> None:
    assert_operator_current_paths_for_dispatch(entries, include_dispatch_support=True)


def assert_operator_current_paths_for_dispatch(
    entries: list[JsonMap],
    *,
    include_dispatch_support: bool,
) -> None:
    expected_entries = (
        EXPECTED_OPERATOR_CURRENT_PATHS
        if include_dispatch_support
        else EXPECTED_OPERATOR_CURRENT_PATHS[:1]
    )
    assert [
        (
            entry["kind"],
            Path(str(entry["path"])).name,
            entry["description"],
            entry["slot"],
            entry["version"],
        )
        for entry in entries
    ] == [(kind, name, description, None, None) for kind, name, description in expected_entries]


async def assert_parent_first_final_readback(
    driver: ParentFirstLaneDriver,
    final_green: JsonMap,
    *,
    expected_trace_node_keys: tuple[str, ...],
) -> None:
    final_runtime = json_map(
        await driver.client.get(
            f"/runtime/tasks/{driver.task_id}",
            headers=OPERATOR_HEADERS,
        )
    )
    assert final_runtime["status"] == "succeeded"
    assert final_runtime["current_node_key"] == "root"
    assert final_runtime["active_attempt_id"] == final_green["active_attempt_id"]

    await _assert_snapshot(driver)
    await _assert_trace(driver, expected_trace_node_keys=expected_trace_node_keys)
    observability_payloads = await _observability_payloads(driver)
    await _assert_observability_files(
        observability_payloads,
        final_attempt_id=str(final_green["active_attempt_id"]),
    )


async def _assert_snapshot(driver: ParentFirstLaneDriver) -> None:
    include_dispatch_support = await _include_dispatch_support_paths(driver)
    snapshot_json = json_map(
        await driver.client.get(
            f"/operator/tasks/{driver.task_id}/snapshot",
            headers=OPERATOR_HEADERS,
        )
    )
    assert snapshot_json["flow"]["status"] == "succeeded"
    assert snapshot_json["flow"]["current_node_key"] == "root"
    assert snapshot_json["top_actionable_items"][0]["suggested_action"] is None
    assert snapshot_json["top_actionable_items"][0]["summary"] == (
        "Current runtime status is 'succeeded'."
    )
    assert_operator_current_paths_for_dispatch(
        snapshot_json["current_paths"],
        include_dispatch_support=include_dispatch_support,
    )
    snapshot_paths = [Path(str(entry["path"])) for entry in snapshot_json["current_paths"]]
    assert all(path.is_file() for path in snapshot_paths)


async def _assert_trace(
    driver: ParentFirstLaneDriver,
    *,
    expected_trace_node_keys: tuple[str, ...],
) -> None:
    include_dispatch_support = await _include_dispatch_support_paths(driver)
    trace_json = json_map(
        await driver.client.get(
            f"/operator/tasks/{driver.task_id}/trace",
            headers=OPERATOR_HEADERS,
            params={"scope": "whole", "sort": "occurred_at_asc", "limit": 50},
        )
    )
    assert trace_json["scope"] == "whole"
    assert [entry["node_key"] for entry in trace_json["dispatch_history"]] == list(
        expected_trace_node_keys
    )
    assert trace_json["boundary_history"][-1]["node_key"] == "root"
    assert trace_json["boundary_history"][-1]["boundary"] == "green"
    assert_operator_current_paths_for_dispatch(
        trace_json["current_paths"],
        include_dispatch_support=include_dispatch_support,
    )


async def _include_dispatch_support_paths(driver: ParentFirstLaneDriver) -> bool:
    async with driver.session_factory() as session:
        flow = await session.get(FlowModel, f"flow.{driver.task_id}")
        assert flow is not None
        return flow.current_open_dispatch_id is not None


async def _observability_payloads(
    driver: ParentFirstLaneDriver,
) -> dict[str, JsonMap]:
    payloads: dict[str, JsonMap] = {}
    for route_name, kind, filename, description in OBSERVABILITY_ROUTES:
        payload = json_map(
            await driver.client.get(
                f"/observability/tasks/{driver.task_id}/{route_name}",
                headers=OPERATOR_HEADERS,
            )
        )
        payloads[filename] = payload
        assert payload["kind"] == kind
        assert Path(str(payload["path"])).name == filename
        assert payload["description"] == description
        assert await asyncio.to_thread(Path(str(payload["path"])).is_file)
    return payloads


async def _assert_observability_files(
    payloads: dict[str, JsonMap],
    *,
    final_attempt_id: str,
) -> None:
    delivery_path = Path(str(payloads["delivery-state.json"]["path"]))
    delivery_state = await asyncio.to_thread(load_json_payload, delivery_path)
    assert_delivery_state_shape(
        delivery_state,
        dispatch_id_from_path=delivery_path.parent.name,
    )
    assert delivery_state["node_key"] == "root"
    assert delivery_state["attempt_id"] == final_attempt_id

    continuity_path = Path(str(payloads["continuity-state.json"]["path"]))
    continuity_state = await asyncio.to_thread(load_json_payload, continuity_path)
    assert_continuity_state_shape(
        continuity_state,
        dispatch_id_from_path=continuity_path.parent.name,
    )
    assert continuity_state["dispatch_id"] == delivery_state["dispatch_id"]
    assert continuity_state["attempt_id"] == final_attempt_id
    assert continuity_state["node_key"] == "root"
    assert continuity_state["session_key_present"] is True

    watchdog_path = Path(str(payloads["watchdog-state.json"]["path"]))
    watchdog_state = await asyncio.to_thread(load_json_payload, watchdog_path)
    assert_watchdog_state_shape(
        watchdog_state,
        dispatch_id_from_path=watchdog_path.parent.name,
    )
    assert watchdog_state["dispatch_id"] == delivery_state["dispatch_id"]
    assert watchdog_state["attempt_id"] == final_attempt_id
    assert watchdog_state["node_key"] == "root"

    provider_events_path = Path(str(payloads["provider-events.ndjson"]["path"]))
    provider_events = await asyncio.to_thread(
        load_provider_event_payloads,
        provider_events_path,
    )
    assert provider_events
    for event_payload in provider_events:
        assert_provider_event_shape(
            event_payload,
            dispatch_id_from_path=provider_events_path.parent.name,
        )
    assert provider_events[-1]["dispatch_id"] == delivery_state["dispatch_id"]


__all__ = [
    "assert_operator_current_paths",
    "assert_operator_current_paths_for_dispatch",
    "assert_parent_first_final_readback",
]
