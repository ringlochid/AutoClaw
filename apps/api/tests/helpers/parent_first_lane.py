from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import cli
from app.config import get_settings
from app.db import DispatchTurnModel, FlowModel
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime.effects import wait_for_runtime_effects
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase2.bootstrap.support import (
    Phase2RuntimeContext,
    phase2_init_args,
    phase2_runtime_paths,
)
from tests.integration.phase4b.support_state_shapes import (
    assert_continuity_state_shape,
    assert_delivery_state_shape,
    assert_provider_event_shape,
    assert_watchdog_state_shape,
    load_json_payload,
    load_provider_event_payloads,
)

JsonMap = dict[str, Any]
ArtifactClaims = list[dict[str, str]]

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}
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


@dataclass(frozen=True)
class ParentFirstLaneDriver:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]
    task_id: str


@asynccontextmanager
async def parent_first_lane_runtime_context(
    tmp_path: Path,
) -> AsyncIterator[Phase2RuntimeContext]:
    paths = phase2_runtime_paths(tmp_path)
    init_args = phase2_init_args(paths)
    init_args.log_level = "WARNING"
    with Path(os.devnull).open("w", encoding="utf-8") as devnull:
        with redirect_stdout(devnull), redirect_stderr(devnull):
            await cli._cmd_init(init_args)
            try:
                with cli._command_env(config_path=paths.config_path):
                    get_settings.cache_clear()
                    yield Phase2RuntimeContext(paths=paths, session_factory=get_session_factory())
            finally:
                await dispose_db_engine()


def write_lane_artifact(task_root: Path, relative_path: str, content: str) -> Path:
    path = task_root / "workspace" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def assert_operator_current_paths(entries: list[JsonMap]) -> None:
    assert [
        (
            entry["kind"],
            Path(str(entry["path"])).name,
            entry["description"],
            entry["slot"],
            entry["version"],
        )
        for entry in entries
    ] == [
        (kind, name, description, None, None)
        for kind, name, description in EXPECTED_OPERATOR_CURRENT_PATHS
    ]


def json_map(response: Response) -> JsonMap:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def run_child_cycle(
    driver: ParentFirstLaneDriver,
    *,
    parent_flow: JsonMap,
    parent_node_key: str,
    child_node_key: str,
    summary: str,
    instruction: str,
    checkpoint_summary: str,
    checkpoint_next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> JsonMap:
    await start_child_from_parent(
        driver,
        parent_node_key=parent_node_key,
        child_node_key=child_node_key,
        expected_flow_revision_id=str(parent_flow["active_flow_revision_id"]),
        summary=summary,
        instruction=instruction,
    )
    green = await _checkpoint_and_close_child(
        driver,
        child_node_key=child_node_key,
        summary=checkpoint_summary,
        next_step=checkpoint_next_step,
        produced_artifacts=produced_artifacts,
    )
    return await continue_flow(
        driver,
        expected_active_flow_revision_id=str(green["active_flow_revision_id"]),
        expected_node_key=parent_node_key,
    )


async def start_child_from_parent(
    driver: ParentFirstLaneDriver,
    *,
    parent_node_key: str,
    child_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    instruction: str,
) -> JsonMap:
    session_key = await current_session_key(driver)
    await _assign_child(
        driver,
        session_key=session_key,
        expected_structural_revision_id=expected_flow_revision_id,
        child_node_key=child_node_key,
        summary=summary,
        instruction=instruction,
    )
    yielded = await _close_boundary(driver, session_key=session_key, boundary="yield")
    assert yielded["current_node_key"] == parent_node_key
    return await continue_flow(
        driver,
        expected_active_flow_revision_id=str(yielded["active_flow_revision_id"]),
        expected_node_key=child_node_key,
    )


async def release_current_parent(
    driver: ParentFirstLaneDriver,
    *,
    expected_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    next_step: str,
) -> JsonMap:
    session_key = await current_session_key(driver)
    await _release_green(
        driver,
        session_key=session_key,
        expected_structural_revision_id=expected_flow_revision_id,
    )
    await _record_terminal_green_checkpoint(
        driver,
        session_key=session_key,
        summary=summary,
        next_step=next_step,
    )
    green = await _close_boundary(driver, session_key=session_key, boundary="green")
    assert green["current_node_key"] == expected_node_key
    return green


async def continue_flow(
    driver: ParentFirstLaneDriver,
    *,
    expected_active_flow_revision_id: str,
    expected_node_key: str,
) -> JsonMap:
    await _mark_open_dispatch_inactive(driver)
    flow = json_map(
        await driver.client.post(
            f"/runtime/tasks/{driver.task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
    )
    await wait_for_runtime_effects(task_id=driver.task_id)
    assert flow["current_node_key"] == expected_node_key
    return flow


async def current_session_key(driver: ParentFirstLaneDriver) -> str:
    async with driver.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == driver.task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        assert isinstance(dispatch.gateway_session_key, str)
        return dispatch.gateway_session_key


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


async def _checkpoint_and_close_child(
    driver: ParentFirstLaneDriver,
    *,
    child_node_key: str,
    summary: str,
    next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> JsonMap:
    session_key = await current_session_key(driver)
    await _record_terminal_green_checkpoint(
        driver,
        session_key=session_key,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    green = await _close_boundary(driver, session_key=session_key, boundary="green")
    assert green["current_node_key"] == child_node_key
    return green


async def _record_terminal_green_checkpoint(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    summary: str,
    next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> None:
    checkpoint: JsonMap = {
        "checkpoint_kind": "terminal",
        "outcome": "green",
        "handoff": {
            "summary": summary,
            "next_step": next_step,
        },
    }
    if produced_artifacts is not None:
        checkpoint["produced_artifacts"] = produced_artifacts

    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/checkpoint",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"checkpoint": checkpoint},
    )
    assert response.status_code == 200, response.text
    await wait_for_runtime_effects(task_id=driver.task_id)


async def _mark_open_dispatch_inactive(driver: ParentFirstLaneDriver) -> None:
    async with driver.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == driver.task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        dispatch.delivery_status = "provider_completed"
        await session.commit()


async def _assign_child(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> None:
    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/tools/assign_child",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": "assign_child",
            "payload": {
                "child_node_key": child_node_key,
                "assignment_intent": {
                    "summary": summary,
                    "instruction": instruction,
                },
            },
            "expected_structural_revision_id": expected_structural_revision_id,
        },
    )
    assert response.status_code == 200, response.text


async def _release_green(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
) -> None:
    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/tools/release_green",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": "release_green",
            "payload": {},
            "expected_structural_revision_id": expected_structural_revision_id,
        },
    )
    assert response.status_code == 200, response.text


async def _close_boundary(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    boundary: str,
) -> JsonMap:
    payload = json_map(
        await driver.client.post(
            f"/callback/tasks/{driver.task_id}/boundary",
            headers={"X-Autoclaw-Session-Key": session_key},
            json={"boundary": boundary},
        )
    )
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return flow


async def _assert_snapshot(driver: ParentFirstLaneDriver) -> None:
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


async def _assert_trace(
    driver: ParentFirstLaneDriver,
    *,
    expected_trace_node_keys: tuple[str, ...],
) -> None:
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
    assert_operator_current_paths(trace_json["current_paths"])


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
