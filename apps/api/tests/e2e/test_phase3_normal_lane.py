from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app import cli
from app.config import get_settings
from app.db import DispatchCallbackBindingModel, DispatchTurnModel, FlowModel
from app.db.session import dispose_db_engine, get_session_factory
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}
_EXPECTED_OPERATOR_CURRENT_PATHS = (
    ("manifest", "workflow-manifest.md", "Whole-workflow visible contract for the current task."),
    ("delivery_state", "delivery-state.json", "Latest task-scoped delivery-state projection."),
    (
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    ("watchdog_state", "watchdog-state.json", "Latest task-scoped watchdog-state projection."),
    (
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)


async def _prepare_runtime_db(tmp_path: Path) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli._cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=None,
            host="127.0.0.1",
            port=8123,
            log_level="INFO",
            api_key="api-test-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=False,
            json=False,
        )
    )
    return config_path


async def _bootstrap_normal_runtime(
    *,
    session: AsyncSession,
    task_id: str,
    task_root: Path,
) -> None:
    await launch_seeded_runtime(
        session,
        task_id=task_id,
        task_root=task_root,
        task_compose=task_compose_payload("normal-parent-first-release"),
        compiler_version="phase-3-normal-e2e",
    )


async def _runtime_read(client: AsyncClient, task_id: str) -> dict[str, Any]:
    response = await client.get(f"/runtime/tasks/{task_id}", headers=OPERATOR_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def _current_session_key(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> str:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        binding = await session.get(
            DispatchCallbackBindingModel,
            f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
        )
        assert binding is not None
        assert binding.binding_status == "live"
        return binding.session_key


async def _mark_open_dispatch_inactive(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        dispatch.delivery_status = "provider_completed"
        await session.commit()


async def _continue_task(
    *,
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    expected_active_flow_revision_id: str,
) -> dict[str, Any]:
    await _mark_open_dispatch_inactive(session_factory=session_factory, task_id=task_id)
    response = await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def _assign_child(
    *,
    client: AsyncClient,
    task_id: str,
    session_key: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> None:
    response = await client.post(
        f"/callback/tasks/{task_id}/tools/assign_child",
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
    assert response.status_code == 200


async def _release_green(
    *,
    client: AsyncClient,
    task_id: str,
    session_key: str,
    expected_structural_revision_id: str,
) -> None:
    response = await client.post(
        f"/callback/tasks/{task_id}/tools/release_green",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": "release_green",
            "payload": {},
            "expected_structural_revision_id": expected_structural_revision_id,
        },
    )
    assert response.status_code == 200


async def _close_with_yield(
    *,
    client: AsyncClient,
    task_id: str,
    session_key: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"boundary": "yield"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return flow


async def _record_terminal_green_checkpoint(
    *,
    client: AsyncClient,
    task_id: str,
    session_key: str,
    summary: str,
    next_step: str,
    produced_artifacts: list[dict[str, str]] | None = None,
) -> None:
    checkpoint: dict[str, Any] = {
        "checkpoint_kind": "terminal",
        "outcome": "green",
        "handoff": {
            "summary": summary,
            "next_step": next_step,
        },
    }
    if produced_artifacts is not None:
        checkpoint["produced_artifacts"] = produced_artifacts
    response = await client.post(
        f"/callback/tasks/{task_id}/checkpoint",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"checkpoint": checkpoint},
    )
    assert response.status_code == 200


async def _close_with_green(
    *,
    client: AsyncClient,
    task_id: str,
    session_key: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"boundary": "green"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return flow


def _artifact_path(task_root: Path, relative_path: str, content: str) -> Path:
    path = task_root / "workspace" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _assert_operator_current_paths(entries: list[dict[str, object]]) -> None:
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
        for kind, name, description in _EXPECTED_OPERATOR_CURRENT_PATHS
    ]


async def test_phase3_normal_e2e_lane_runs_parent_subtree_release_and_final_readback(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_id = "task_phase3_normal_e2e"
    task_root = tmp_path / "task-root"

    findings_report = _artifact_path(
        task_root,
        "investigate/findings_report.md",
        "Findings: refresh token path regressed after scope narrowing.\n",
    )
    change_patch = _artifact_path(
        task_root,
        "implement/change_patch.diff",
        "diff --git a/auth.py b/auth.py\n",
    )
    verification_report = _artifact_path(
        task_root,
        "implement/verification_report.md",
        "Verification: targeted regression checks passed.\n",
    )
    review_report = _artifact_path(
        task_root,
        "review/review_report.md",
        "Review: patch is scoped and evidence is sufficient.\n",
    )
    closure_report = _artifact_path(
        task_root,
        "release/closure_report.md",
        "Release: bounded closure completed from current surfaced evidence.\n",
    )

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                await _bootstrap_normal_runtime(
                    session=session,
                    task_id=task_id,
                    task_root=task_root,
                )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime = await _runtime_read(client, task_id)
                assert runtime["status"] == "running"
                assert runtime["current_node_key"] == "root"

                root_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )

                await _assign_child(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                    expected_structural_revision_id=runtime["active_flow_revision_id"],
                    child_node_key="implementation_subtree",
                    summary="Start the implementation subtree.",
                    instruction="Stage only the bounded implementation subtree.",
                )
                yielded = await _close_with_yield(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                )
                assert yielded["current_node_key"] == "root"

                subtree_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=yielded["active_flow_revision_id"],
                )
                assert subtree_flow["current_node_key"] == "implementation_subtree"
                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )

                await _assign_child(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                    expected_structural_revision_id=subtree_flow["active_flow_revision_id"],
                    child_node_key="investigate_issue",
                    summary="Investigate the current auth refresh failure.",
                    instruction="Publish bounded findings for downstream implementation.",
                )
                yielded = await _close_with_yield(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                )
                investigate_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=yielded["active_flow_revision_id"],
                )
                assert investigate_flow["current_node_key"] == "investigate_issue"
                investigate_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )
                await _record_terminal_green_checkpoint(
                    client=client,
                    task_id=task_id,
                    session_key=investigate_session_key,
                    summary="Investigation completed with a bounded findings report.",
                    next_step="Return findings to the implementation subtree parent.",
                    produced_artifacts=[{"slot": "findings_report", "path": str(findings_report)}],
                )
                green = await _close_with_green(
                    client=client,
                    task_id=task_id,
                    session_key=investigate_session_key,
                )
                assert green["current_node_key"] == "investigate_issue"

                subtree_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=green["active_flow_revision_id"],
                )
                assert subtree_flow["current_node_key"] == "implementation_subtree"
                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )

                await _assign_child(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                    expected_structural_revision_id=subtree_flow["active_flow_revision_id"],
                    child_node_key="implement_change",
                    summary="Implement the auth refresh fix.",
                    instruction=(
                        "Use the current findings report and publish patch plus verification."
                    ),
                )
                yielded = await _close_with_yield(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                )
                implement_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=yielded["active_flow_revision_id"],
                )
                assert implement_flow["current_node_key"] == "implement_change"
                implement_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )
                await _record_terminal_green_checkpoint(
                    client=client,
                    task_id=task_id,
                    session_key=implement_session_key,
                    summary="Implementation completed with patch and verification evidence.",
                    next_step="Return to the implementation subtree for bounded review.",
                    produced_artifacts=[
                        {"slot": "change_patch", "path": str(change_patch)},
                        {"slot": "verification_report", "path": str(verification_report)},
                    ],
                )
                green = await _close_with_green(
                    client=client,
                    task_id=task_id,
                    session_key=implement_session_key,
                )

                subtree_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=green["active_flow_revision_id"],
                )
                assert subtree_flow["current_node_key"] == "implementation_subtree"
                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )

                await _assign_child(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                    expected_structural_revision_id=subtree_flow["active_flow_revision_id"],
                    child_node_key="review_change",
                    summary="Review the scoped auth refresh patch.",
                    instruction="Use the current patch and verification evidence only.",
                )
                yielded = await _close_with_yield(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                )
                review_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=yielded["active_flow_revision_id"],
                )
                assert review_flow["current_node_key"] == "review_change"
                review_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )
                await _record_terminal_green_checkpoint(
                    client=client,
                    task_id=task_id,
                    session_key=review_session_key,
                    summary="Review completed with a bounded review report.",
                    next_step="Return review evidence to the implementation subtree parent.",
                    produced_artifacts=[{"slot": "review_report", "path": str(review_report)}],
                )
                green = await _close_with_green(
                    client=client,
                    task_id=task_id,
                    session_key=review_session_key,
                )

                subtree_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=green["active_flow_revision_id"],
                )
                assert subtree_flow["current_node_key"] == "implementation_subtree"
                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )
                await _release_green(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                    expected_structural_revision_id=subtree_flow["active_flow_revision_id"],
                )
                await _record_terminal_green_checkpoint(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                    summary=(
                        "Implementation subtree verified current findings, patch, and "
                        "review evidence."
                    ),
                    next_step="Return release-ready subtree evidence to root.",
                )
                green = await _close_with_green(
                    client=client,
                    task_id=task_id,
                    session_key=subtree_session_key,
                )

                root_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=green["active_flow_revision_id"],
                )
                assert root_flow["current_node_key"] == "root"
                root_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )

                await _assign_child(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                    expected_structural_revision_id=root_flow["active_flow_revision_id"],
                    child_node_key="release_closure",
                    summary="Run the bounded release closure step.",
                    instruction="Use only the current surfaced release inputs.",
                )
                yielded = await _close_with_yield(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                )
                release_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=yielded["active_flow_revision_id"],
                )
                assert release_flow["current_node_key"] == "release_closure"
                release_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )
                await _record_terminal_green_checkpoint(
                    client=client,
                    task_id=task_id,
                    session_key=release_session_key,
                    summary="Release closure completed from current surfaced evidence.",
                    next_step="Return closure evidence to root for final release.",
                    produced_artifacts=[{"slot": "closure_report", "path": str(closure_report)}],
                )
                green = await _close_with_green(
                    client=client,
                    task_id=task_id,
                    session_key=release_session_key,
                )

                root_flow = await _continue_task(
                    client=client,
                    session_factory=session_factory,
                    task_id=task_id,
                    expected_active_flow_revision_id=green["active_flow_revision_id"],
                )
                assert root_flow["current_node_key"] == "root"
                root_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id=task_id,
                )
                await _release_green(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                    expected_structural_revision_id=root_flow["active_flow_revision_id"],
                )
                await _record_terminal_green_checkpoint(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                    summary="Root verified the current subtree, review, and closure evidence.",
                    next_step="Close the workflow successfully.",
                )
                final_green = await _close_with_green(
                    client=client,
                    task_id=task_id,
                    session_key=root_session_key,
                )
                assert final_green["status"] == "succeeded"
                assert final_green["current_node_key"] == "root"

                final_runtime = await _runtime_read(client, task_id)
                assert final_runtime["status"] == "succeeded"
                assert final_runtime["current_node_key"] == "root"
                assert final_runtime["active_attempt_id"] == final_green["active_attempt_id"]

                snapshot = await client.get(
                    f"/operator/tasks/{task_id}/snapshot",
                    headers=OPERATOR_HEADERS,
                )
                assert snapshot.status_code == 200
                snapshot_json = snapshot.json()
                assert snapshot_json["flow"]["status"] == "succeeded"
                assert snapshot_json["flow"]["current_node_key"] == "root"
                assert snapshot_json["top_actionable_items"][0]["suggested_action"] is None
                assert snapshot_json["top_actionable_items"][0]["summary"] == (
                    "Current runtime status is 'succeeded'."
                )
                _assert_operator_current_paths(snapshot_json["current_paths"])
                snapshot_paths = [Path(entry["path"]) for entry in snapshot_json["current_paths"]]
                assert all(path.is_file() for path in snapshot_paths)

                trace = await client.get(
                    f"/operator/tasks/{task_id}/trace",
                    headers=OPERATOR_HEADERS,
                    params={"scope": "whole", "sort": "occurred_at_asc", "limit": 50},
                )
                assert trace.status_code == 200
                trace_json = trace.json()
                assert trace_json["scope"] == "whole"
                assert [entry["node_key"] for entry in trace_json["dispatch_history"]] == [
                    "root",
                    "implementation_subtree",
                    "investigate_issue",
                    "implementation_subtree",
                    "implement_change",
                    "implementation_subtree",
                    "review_change",
                    "implementation_subtree",
                    "root",
                    "release_closure",
                    "root",
                ]
                assert trace_json["boundary_history"][-1]["node_key"] == "root"
                assert trace_json["boundary_history"][-1]["boundary"] == "green"
                _assert_operator_current_paths(trace_json["current_paths"])

                observability_routes = (
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
                observability_payloads: dict[str, dict[str, Any]] = {}
                for route_name, kind, filename, description in observability_routes:
                    response = await client.get(
                        f"/observability/tasks/{task_id}/{route_name}",
                        headers=OPERATOR_HEADERS,
                    )
                    assert response.status_code == 200
                    payload = response.json()
                    observability_payloads[filename] = payload
                    assert payload["kind"] == kind
                    assert Path(payload["path"]).name == filename
                    assert payload["description"] == description
                    assert await asyncio.to_thread(Path(payload["path"]).is_file)

                delivery_state = json.loads(
                    await asyncio.to_thread(
                        Path(observability_payloads["delivery-state.json"]["path"]).read_text,
                        encoding="utf-8",
                    )
                )
                assert delivery_state["node_key"] == "root"
                assert delivery_state["attempt_id"] == final_green["active_attempt_id"]

                provider_events_path = Path(
                    observability_payloads["provider-events.ndjson"]["path"]
                )
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
    finally:
        await dispose_db_engine()
