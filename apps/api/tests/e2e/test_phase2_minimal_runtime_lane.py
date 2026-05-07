from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app import cli
from app.config import get_settings
from app.db import DispatchCallbackBindingModel, DispatchTurnModel, FlowModel
from app.db.session import dispose_db_engine, get_session_factory
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}
EXPECTED_CURRENT_PATH_NAMES = (
    "workflow-manifest.md",
    "delivery-state.json",
    "continuity-state.json",
    "watchdog-state.json",
    "provider-events.ndjson",
)


async def _current_session_key(
    session_factory: async_sessionmaker,
    *,
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
        assert isinstance(binding.session_key, str)
        return binding.session_key


async def _mark_current_dispatch_provider_completed(
    session_factory: async_sessionmaker,
    *,
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


def _assert_materialized_snapshot(
    snapshot_payload: dict[str, object],
    *,
    expected_node_key: str,
) -> Path:
    flow = snapshot_payload["flow"]
    assert isinstance(flow, dict)
    assert flow["current_node_key"] == expected_node_key

    current_paths = snapshot_payload["current_paths"]
    assert isinstance(current_paths, list)
    assert (
        tuple(Path(str(entry["path"])).name for entry in current_paths)
        == EXPECTED_CURRENT_PATH_NAMES
    )

    manifest_path = Path(str(current_paths[0]["path"]))
    dispatch_dir = Path(str(current_paths[1]["path"])).parent
    prompt_path = dispatch_dir / "prompt.md"
    prompt_request_path = dispatch_dir / "prompt-request.json"

    assert manifest_path.is_file()
    assert prompt_path.is_file()
    assert prompt_request_path.is_file()
    assert all(Path(str(entry["path"])).is_file() for entry in current_paths)

    prompt_request = json.loads(prompt_request_path.read_text(encoding="utf-8"))
    assert prompt_request["send_mode"] == "full_prompt"
    assert prompt_request["previous_response_id"] is None
    assert f"- current node anchor: {expected_node_key}" in prompt_path.read_text(encoding="utf-8")

    return dispatch_dir


async def test_phase2_minimal_runtime_lane_bootstraps_and_materializes_one_child_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_e2e_minimal"

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
                    task_id=task_id,
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-2-e2e-minimal",
                )

            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    f"/runtime/tasks/{task_id}",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                runtime_payload = runtime_read.json()
                assert runtime_payload["workflow_key"] == "minimal-implement-change"
                assert runtime_payload["current_node_key"] == "root"
                assert await asyncio.to_thread(
                    Path(runtime_payload["workflow_manifest_ref"]["path"]).is_file
                )

                root_snapshot = await client.get(
                    f"/operator/tasks/{task_id}/snapshot",
                    headers=OPERATOR_HEADERS,
                )
                assert root_snapshot.status_code == 200
                root_dispatch_dir = _assert_materialized_snapshot(
                    root_snapshot.json(),
                    expected_node_key="root",
                )
                assert root_dispatch_dir.name == "dispatch.task_phase2_e2e_minimal.root.01"

                root_session_key = await _current_session_key(
                    session_factory,
                    task_id=task_id,
                )
                assign_child = await client.post(
                    f"/callback/tasks/{task_id}/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implement_change",
                            "assignment_intent": {
                                "summary": "Start the bounded implementation child.",
                                "instruction": "Stay inside the current child assignment only.",
                            },
                        },
                        "expected_structural_revision_id": runtime_payload[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign_child.status_code == 200

                yielded = await client.post(
                    f"/callback/tasks/{task_id}/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200
                assert yielded.json()["flow"]["current_node_key"] == "root"

                await _mark_current_dispatch_provider_completed(
                    session_factory,
                    task_id=task_id,
                )
                continued = await client.post(
                    f"/runtime/tasks/{task_id}/continue",
                    headers=OPERATOR_HEADERS,
                    params={
                        "expected_active_flow_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ]
                    },
                )
                assert continued.status_code == 200
                assert continued.json()["current_node_key"] == "implement_change"

                child_snapshot = await client.get(
                    f"/operator/tasks/{task_id}/snapshot",
                    headers=OPERATOR_HEADERS,
                )
                assert child_snapshot.status_code == 200
                child_dispatch_dir = _assert_materialized_snapshot(
                    child_snapshot.json(),
                    expected_node_key="implement_change",
                )
                assert child_dispatch_dir != root_dispatch_dir

                runtime_after_continue = await client.get(
                    f"/runtime/tasks/{task_id}",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_after_continue.status_code == 200
                assert runtime_after_continue.json()["current_node_key"] == "implement_change"
    finally:
        await dispose_db_engine()
