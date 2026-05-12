from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tests.e2e.phase3_normal_lane_support import (
    EXPECTED_TRACE_NODE_KEYS,
    OBSERVABILITY_ROUTES,
    OPERATOR_HEADERS,
    JsonMap,
    NormalLaneDriver,
    assert_operator_current_paths,
    json_map,
)


async def assert_final_readback(
    driver: NormalLaneDriver,
    final_green: JsonMap,
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
    await _assert_trace(driver)
    observability_payloads = await _observability_payloads(driver)
    await _assert_observability_files(
        observability_payloads,
        final_attempt_id=str(final_green["active_attempt_id"]),
    )


async def _assert_snapshot(driver: NormalLaneDriver) -> None:
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
    assert_operator_current_paths(snapshot_json["current_paths"])
    snapshot_paths = [Path(str(entry["path"])) for entry in snapshot_json["current_paths"]]
    assert all(path.is_file() for path in snapshot_paths)


async def _assert_trace(driver: NormalLaneDriver) -> None:
    trace_json = json_map(
        await driver.client.get(
            f"/operator/tasks/{driver.task_id}/trace",
            headers=OPERATOR_HEADERS,
            params={"scope": "whole", "sort": "occurred_at_asc", "limit": 50},
        )
    )
    assert trace_json["scope"] == "whole"
    assert [entry["node_key"] for entry in trace_json["dispatch_history"]] == list(
        EXPECTED_TRACE_NODE_KEYS
    )
    assert trace_json["boundary_history"][-1]["node_key"] == "root"
    assert trace_json["boundary_history"][-1]["boundary"] == "green"
    assert_operator_current_paths(trace_json["current_paths"])


async def _observability_payloads(driver: NormalLaneDriver) -> dict[str, JsonMap]:
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
    delivery_state = json.loads(
        await asyncio.to_thread(
            Path(str(payloads["delivery-state.json"]["path"])).read_text,
            encoding="utf-8",
        )
    )
    assert delivery_state["node_key"] == "root"
    assert delivery_state["attempt_id"] == final_attempt_id

    provider_events_path = Path(str(payloads["provider-events.ndjson"]["path"]))
    provider_events = [
        json.loads(line)
        for line in (
            await asyncio.to_thread(
                provider_events_path.read_text,
                encoding="utf-8",
            )
        ).splitlines()
        if line.strip()
    ]
    assert provider_events[-1]["dispatch_id"] == delivery_state["dispatch_id"]
