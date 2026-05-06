from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app import cli
from app.config import get_settings
from app.db import AssignmentModel, DispatchCallbackBindingModel, FlowModel, FlowNodeModel
from app.db.session import dispose_db_engine, get_session_factory
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from tests.helpers.runtime_seed import (
    launch_seeded_runtime,
    task_compose_payload,
)

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


async def test_phase3_runtime_routes_surface_runtime_callback_operator_and_observability(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"

    try:
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

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_2026_0044",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-runtime-routes",
                )

            async with session_factory() as session:
                flow = await session.get(FlowModel, "flow.task_2026_0044")
                assert flow is not None
                binding = await session.get(
                    DispatchCallbackBindingModel,
                    f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
                )
                assert binding is not None
                session_key = binding.session_key

            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                operator_headers = {"X-AutoClaw-API-Key": "api-test-key"}

                unauthorized_runtime = await client.get("/runtime/tasks")
                assert unauthorized_runtime.status_code == 401
                assert unauthorized_runtime.json()["detail"]["code"] == "illegal_caller"

                runtime_list = await client.get("/runtime/tasks", headers=operator_headers)
                assert runtime_list.status_code == 200
                assert runtime_list.json()["items"][0]["task_id"] == "task_2026_0044"

                invalid_runtime_query = await client.get(
                    "/runtime/tasks",
                    headers=operator_headers,
                    params={"limit": 0},
                )
                assert invalid_runtime_query.status_code == 400
                assert invalid_runtime_query.json()["code"] == "invalid_request_shape"

                runtime_read = await client.get(
                    "/runtime/tasks/task_2026_0044",
                    headers=operator_headers,
                )
                assert runtime_read.status_code == 200
                assert runtime_read.json()["current_node_key"] == "root"

                missing_runtime = await client.get(
                    "/runtime/tasks/task_missing",
                    headers=operator_headers,
                )
                assert missing_runtime.status_code == 404
                assert missing_runtime.json()["detail"]["code"] == "missing_resource"
                assert missing_runtime.json()["detail"]["suggested_next_step"] == (
                    "Verify the task, flow, or dispatch id and reread the current runtime surface "
                    "before retrying this request."
                )
                missing_observability = await client.get(
                    "/observability/tasks/task_missing/delivery-state",
                    headers=operator_headers,
                )
                assert missing_observability.status_code == 404
                assert missing_observability.json()["detail"]["code"] == "missing_resource"
                assert missing_observability.json()["detail"]["suggested_next_step"] == (
                    "Verify the task, flow, or dispatch id and reread the current runtime surface "
                    "before retrying this request."
                )

                assign_child = await client.post(
                    "/callback/tasks/task_2026_0044/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {
                                "summary": "Start the implementation subtree.",
                                "instruction": "Stage only the current implementation subtree.",
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign_child.status_code == 200

                invalid_assign = await client.post(
                    "/callback/tasks/task_2026_0044/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": "invalid-session"},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {
                                "summary": "Start the implementation subtree.",
                                "instruction": "Stage only the current implementation subtree.",
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert invalid_assign.status_code == 401
                assert invalid_assign.json()["detail"]["code"] == "illegal_caller"
                assert invalid_assign.json()["detail"]["suggested_next_step"] == (
                    "Reread the current live callback binding and resend the request with the "
                    "bound X-Autoclaw-Session-Key for the open dispatch."
                )

                mismatched_tool = await client.post(
                    "/callback/tasks/task_2026_0044/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "child": {
                                "node_key": "illegal_child",
                                "role": "architect",
                                "description": "Should be rejected.",
                            }
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert mismatched_tool.status_code == 400
                assert mismatched_tool.json()["detail"]["code"] == "invalid_request_shape"

                yielded = await client.post(
                    "/callback/tasks/task_2026_0044/boundary",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200
                assert yielded.json()["flow"]["current_node_key"] == "implementation_subtree"
                continued = await client.post(
                    "/runtime/tasks/task_2026_0044/continue",
                    headers=operator_headers,
                    params={
                        "expected_active_flow_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ]
                    },
                )
                assert continued.status_code == 200

                snapshot = await client.get(
                    "/operator/tasks/task_2026_0044/snapshot",
                    headers=operator_headers,
                )
                assert snapshot.status_code == 200
                snapshot_json = snapshot.json()
                assert snapshot_json["flow"]["current_node_key"] == "implementation_subtree"
                assert snapshot_json["top_actionable_items"][0]["suggested_action"] is None
                assert (
                    snapshot_json["top_actionable_items"][0]["current_paths"]
                    == snapshot_json["current_paths"]
                )
                _assert_operator_current_paths(snapshot_json["current_paths"])
                snapshot_paths = [Path(entry["path"]) for entry in snapshot_json["current_paths"]]
                assert all([await asyncio.to_thread(path.is_file) for path in snapshot_paths])

                trace = await client.get(
                    "/operator/tasks/task_2026_0044/trace",
                    headers=operator_headers,
                    params={"scope": "current", "q": "implementation_subtree", "limit": 1},
                )
                assert trace.status_code == 200
                trace_json = trace.json()
                assert trace_json["scope"] == "current"
                assert trace_json["dispatch_history"][0]["node_key"] == "implementation_subtree"
                assert trace_json["dispatch_history"][0]["delivery_status"] == "accepted"
                assert trace_json["next_cursor"] is None
                _assert_operator_current_paths(trace_json["current_paths"])
                trace_paths = [Path(entry["path"]) for entry in trace_json["current_paths"]]
                assert all([await asyncio.to_thread(path.is_file) for path in trace_paths])

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
                observability_payloads: dict[str, dict[str, object]] = {}
                for (
                    route_name,
                    expected_kind,
                    expected_name,
                    expected_description,
                ) in observability_routes:
                    response = await client.get(
                        f"/observability/tasks/task_2026_0044/{route_name}",
                        headers=operator_headers,
                    )
                    assert response.status_code == 200
                    payload = response.json()
                    observability_payloads[expected_name] = payload
                    assert payload["kind"] == expected_kind
                    assert Path(payload["path"]).name == expected_name
                    assert payload["description"] == expected_description
                    assert await asyncio.to_thread(Path(payload["path"]).is_file)

                delivery_path = Path(str(observability_payloads["delivery-state.json"]["path"]))
                delivery_payload = json.loads(await asyncio.to_thread(delivery_path.read_text))
                assert set(delivery_payload) == {
                    "dispatch_id",
                    "attempt_id",
                    "assignment_key",
                    "node_key",
                    "transport_family",
                    "transport_state",
                    "controller_observation_state",
                    "last_provider_event_kind",
                    "provider_final_status",
                    "provider_error",
                    "send_mode",
                    "previous_dispatch_id",
                    "superseded_by_dispatch_id",
                    "prepared_at",
                    "accepted_at",
                    "last_provider_signal_at",
                    "last_controller_progress_at",
                    "last_controller_terminal_at",
                    "updated_at",
                }
                assert delivery_payload["dispatch_id"] == delivery_path.parent.name
                assert (
                    delivery_payload["attempt_id"]
                    == trace_json["dispatch_history"][0]["attempt_id"]
                )
                assert (
                    delivery_payload["assignment_key"]
                    == trace_json["dispatch_history"][0]["assignment_key"]
                )
                assert delivery_payload["node_key"] == "implementation_subtree"
                assert delivery_payload["transport_family"] == "phase3_local_runtime"
                assert delivery_payload["transport_state"] == "accepted"
                assert delivery_payload["controller_observation_state"] == "live"
                assert delivery_payload["last_provider_event_kind"] is None
                assert delivery_payload["provider_final_status"] is None
                assert delivery_payload["provider_error"] is None
                assert delivery_payload["send_mode"] == "full_prompt"
                assert delivery_payload["previous_dispatch_id"] == "dispatch.task_2026_0044.root.01"
                assert delivery_payload["superseded_by_dispatch_id"] is None
                assert delivery_payload["accepted_at"] is not None
                assert delivery_payload["prepared_at"] is not None
                assert delivery_payload["last_provider_signal_at"] is None
                assert delivery_payload["last_controller_progress_at"] is None
                assert delivery_payload["last_controller_terminal_at"] is None
                assert delivery_payload["updated_at"] is not None

                stale_callback = await client.post(
                    "/callback/tasks/task_2026_0044/boundary",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={"boundary": "yield"},
                )
                assert stale_callback.status_code == 409
                assert stale_callback.json()["detail"]["code"] == "stale_dispatch"
                assert stale_callback.json()["detail"]["suggested_next_step"] == (
                    "Reread the current dispatch context and callback binding, then retry only "
                    "if this node is still the current caller for an open dispatch."
                )
    finally:
        await dispose_db_engine()


async def test_phase3_runtime_routes_apply_task_filters_and_trace_queries(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    alpha_root = tmp_path / "task-alpha-root"
    zulu_root = tmp_path / "task-zulu-root"

    try:
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

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            alpha_compose = task_compose_payload("normal-parent-first-release")
            alpha_compose = alpha_compose.model_copy(
                update={
                    "task": alpha_compose.task.model_copy(
                        update={
                            "key": "alpha-runtime",
                            "title": "Alpha runtime",
                            "summary": "Alpha implementation subtree.",
                        }
                    )
                }
            )
            zulu_compose = task_compose_payload("normal-parent-first-release")
            zulu_compose = zulu_compose.model_copy(
                update={
                    "task": zulu_compose.task.model_copy(
                        update={
                            "key": "zulu-runtime",
                            "title": "Zulu runtime",
                            "summary": "Zulu implementation subtree.",
                        }
                    )
                }
            )
            session_factory = get_session_factory()
            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_alpha",
                    task_root=alpha_root,
                    task_compose=alpha_compose,
                    compiler_version="phase-3-runtime-routes",
                )
                await launch_seeded_runtime(
                    session,
                    task_id="task_zulu",
                    task_root=zulu_root,
                    task_compose=zulu_compose,
                    compiler_version="phase-3-runtime-routes",
                )

            async with session_factory() as session:
                flow = await session.get(FlowModel, "flow.task_alpha")
                assert flow is not None
                binding = await session.get(
                    DispatchCallbackBindingModel,
                    f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
                )
                assert binding is not None
                session_key = binding.session_key

            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                operator_headers = {"X-AutoClaw-API-Key": "api-test-key"}
                runtime_list = await client.get(
                    "/runtime/tasks",
                    headers=operator_headers,
                    params={"sort": "task_title_desc", "limit": 2},
                )
                assert runtime_list.status_code == 200
                assert [item["task_title"] for item in runtime_list.json()["items"]] == [
                    "Zulu runtime",
                    "Alpha runtime",
                ]
                paged_runtime_list = await client.get(
                    "/runtime/tasks",
                    headers=operator_headers,
                    params={"sort": "task_title_asc", "limit": 1},
                )
                assert paged_runtime_list.status_code == 200
                assert paged_runtime_list.json()["items"][0]["task_id"] == "task_alpha"
                assert paged_runtime_list.json()["next_cursor"] == "1"
                paged_runtime_list_2 = await client.get(
                    "/runtime/tasks",
                    headers=operator_headers,
                    params={
                        "sort": "task_title_asc",
                        "limit": 1,
                        "cursor": paged_runtime_list.json()["next_cursor"],
                    },
                )
                assert paged_runtime_list_2.status_code == 200
                assert paged_runtime_list_2.json()["items"][0]["task_id"] == "task_zulu"
                assert paged_runtime_list_2.json()["next_cursor"] is None

                filtered = await client.get(
                    "/runtime/tasks",
                    headers=operator_headers,
                    params={
                        "q": "alpha",
                        "status": "running",
                        "sort": "task_title_asc",
                        "limit": 1,
                    },
                )
                assert filtered.status_code == 200
                assert filtered.json()["items"][0]["task_id"] == "task_alpha"

                runtime_read = await client.get(
                    "/runtime/tasks/task_alpha",
                    headers=operator_headers,
                )
                assert runtime_read.status_code == 200
                assign_child = await client.post(
                    "/callback/tasks/task_alpha/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {
                                "summary": "Start the implementation subtree.",
                                "instruction": "Stage only the current implementation subtree.",
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign_child.status_code == 200

                yielded = await client.post(
                    "/callback/tasks/task_alpha/boundary",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                boundary_trace = await client.get(
                    "/operator/tasks/task_alpha/trace",
                    headers=operator_headers,
                    params={"scope": "whole", "q": "yield", "sort": "occurred_at_asc"},
                )
                assert boundary_trace.status_code == 200
                boundary_trace_json = boundary_trace.json()
                assert boundary_trace_json["boundary_history"][0]["boundary"] == "yield"
                _assert_operator_current_paths(boundary_trace_json["current_paths"])
                paged_trace = await client.get(
                    "/operator/tasks/task_alpha/trace",
                    headers=operator_headers,
                    params={"scope": "whole", "limit": 1, "sort": "occurred_at_asc"},
                )
                assert paged_trace.status_code == 200
                assert paged_trace.json()["next_cursor"] is None

                delivery_trace = await client.get(
                    "/operator/tasks/task_alpha/trace",
                    headers=operator_headers,
                    params={"scope": "whole", "q": "accepted"},
                )
                assert delivery_trace.status_code == 200
                delivery_trace_json = delivery_trace.json()
                assert delivery_trace_json["dispatch_history"]
                assert delivery_trace_json["dispatch_history"][0]["delivery_status"] == "accepted"
                _assert_operator_current_paths(delivery_trace_json["current_paths"])
    finally:
        await dispose_db_engine()


async def test_phase3_runtime_routes_tighten_callback_error_mapping_and_snapshot_guidance(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-guidance-root"

    try:
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

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_guidance",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-runtime-routes",
                )

            async with session_factory() as session:
                flow = await session.get(FlowModel, "flow.task_guidance")
                assert flow is not None
                binding = await session.get(
                    DispatchCallbackBindingModel,
                    f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
                )
                assert binding is not None
                session_key = binding.session_key
                active_flow_revision_id = flow.active_flow_revision_id

            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                operator_headers = {"X-AutoClaw-API-Key": "api-test-key"}

                async with session_factory() as session:
                    flow = await session.get(FlowModel, "flow.task_guidance")
                    assert flow is not None
                    flow.status = "paused"
                    await session.commit()

                inactive_callback = await client.post(
                    "/callback/tasks/task_guidance/boundary",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={"boundary": "yield"},
                )
                assert inactive_callback.status_code == 422
                assert inactive_callback.json()["detail"]["code"] == "illegal_state"
                assert inactive_callback.json()["detail"]["suggested_next_step"] == (
                    "Reread the current runtime status and dispatch context, then use the "
                    "operator lane to resume or inspect the task before sending more "
                    "callback writes."
                )

                paused_snapshot = await client.get(
                    "/operator/tasks/task_guidance/snapshot",
                    headers=operator_headers,
                )
                assert paused_snapshot.status_code == 200
                paused_snapshot_json = paused_snapshot.json()
                assert (
                    paused_snapshot_json["top_actionable_items"][0]["suggested_action"]
                    == "continue"
                )
                assert (
                    paused_snapshot_json["top_actionable_items"][0]["current_paths"]
                    == paused_snapshot_json["current_paths"]
                )
                _assert_operator_current_paths(paused_snapshot_json["current_paths"])

                async with session_factory() as session:
                    flow = await session.get(FlowModel, "flow.task_guidance")
                    assert flow is not None
                    flow.status = "running"
                    node = await session.scalar(
                        select(FlowNodeModel).where(
                            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                            FlowNodeModel.node_key == flow.current_node_key,
                        )
                    )
                    assert node is not None
                    assignment = await session.get(AssignmentModel, node.current_assignment_id)
                    assert assignment is not None
                    assignment.produces_json = [
                        {
                            "slot": "missing_release_basis",
                            "description": "Synthetic required release basis for route mapping.",
                            "file_hint": "missing_release_basis.md",
                        }
                    ]
                    await session.commit()

                missing_publication = await client.post(
                    "/callback/tasks/task_guidance/tools/release_green",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={
                        "tool_name": "release_green",
                        "payload": {},
                        "expected_structural_revision_id": active_flow_revision_id,
                    },
                )
                assert missing_publication.status_code == 422
                assert (
                    missing_publication.json()["detail"]["code"] == "missing_required_publication"
                )
                assert missing_publication.json()["detail"]["suggested_next_step"] == (
                    "Publish or republish the missing durable or surfaced release basis first, "
                    "then retry the control action or reread the surfaced release inputs."
                )

                async with session_factory() as session:
                    flow = await session.get(FlowModel, "flow.task_guidance")
                    assert flow is not None
                    flow.status = "blocked"
                    await session.commit()

                blocked_snapshot = await client.get(
                    "/operator/tasks/task_guidance/snapshot",
                    headers=operator_headers,
                )
                assert blocked_snapshot.status_code == 200
                blocked_snapshot_json = blocked_snapshot.json()
                assert blocked_snapshot_json["top_actionable_items"][0]["suggested_action"] is None
                assert (
                    blocked_snapshot_json["top_actionable_items"][0]["current_paths"]
                    == blocked_snapshot_json["current_paths"]
                )
                _assert_operator_current_paths(blocked_snapshot_json["current_paths"])
    finally:
        await dispose_db_engine()
