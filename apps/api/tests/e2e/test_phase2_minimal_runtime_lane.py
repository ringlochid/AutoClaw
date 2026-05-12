from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.db import DispatchCallbackBindingModel, DispatchTurnModel, FlowModel
from app.main import create_app
from app.runtime.post_commit import wait_for_runtime_effects
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2_runtime_bootstrap_support import phase2_runtime_context

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


async def _runtime_payload(
    client: AsyncClient,
    *,
    task_id: str,
) -> dict[str, Any]:
    response = await client.get(
        f"/runtime/tasks/{task_id}",
        headers=OPERATOR_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def _snapshot_dispatch_dir(
    client: AsyncClient,
    *,
    task_id: str,
    expected_node_key: str,
) -> Path:
    await wait_for_runtime_effects(task_id=task_id)
    response = await client.get(
        f"/operator/tasks/{task_id}/snapshot",
        headers=OPERATOR_HEADERS,
    )
    assert response.status_code == 200
    return _assert_materialized_snapshot(
        response.json(),
        expected_node_key=expected_node_key,
    )


async def _assign_child_and_yield(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    assign_child = await client.post(
        f"/callback/tasks/{task_id}/tools/assign_child",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": "assign_child",
            "payload": {
                "child_node_key": "implement_change",
                "assignment_intent": {
                    "summary": "Start the bounded implementation child.",
                    "instruction": "Stay inside the current child assignment only.",
                },
            },
            "expected_structural_revision_id": active_flow_revision_id,
        },
    )
    assert assign_child.status_code == 200
    yielded = await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"boundary": "yield"},
    )
    assert yielded.status_code == 200
    payload = yielded.json()
    assert isinstance(payload, dict)
    return payload


async def _continue_runtime(
    client: AsyncClient,
    *,
    task_id: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": active_flow_revision_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def test_phase2_minimal_runtime_lane_bootstraps_and_materializes_one_child_path(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_e2e_minimal"

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("minimal-implement-change"),
                compiler_version="phase-2-e2e-minimal",
            )

        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            runtime_payload = await _runtime_payload(client, task_id=task_id)
            assert runtime_payload["workflow_key"] == "minimal-implement-change"
            assert runtime_payload["current_node_key"] == "root"
            await wait_for_runtime_effects(task_id=task_id)
            assert await asyncio.to_thread(
                Path(str(runtime_payload["workflow_manifest_ref"]["path"])).is_file
            )

            root_dispatch_dir = await _snapshot_dispatch_dir(
                client,
                task_id=task_id,
                expected_node_key="root",
            )
            assert root_dispatch_dir.name == "dispatch.task_phase2_e2e_minimal.root.01"

            root_session_key = await _current_session_key(
                runtime.session_factory,
                task_id=task_id,
            )
            yielded = await _assign_child_and_yield(
                client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=str(runtime_payload["active_flow_revision_id"]),
            )
            assert yielded["flow"]["current_node_key"] == "root"

            await _mark_current_dispatch_provider_completed(
                runtime.session_factory,
                task_id=task_id,
            )
            continued = await _continue_runtime(
                client,
                task_id=task_id,
                active_flow_revision_id=str(yielded["flow"]["active_flow_revision_id"]),
            )
            assert continued["current_node_key"] == "implement_change"

            child_dispatch_dir = await _snapshot_dispatch_dir(
                client,
                task_id=task_id,
                expected_node_key="implement_change",
            )
            assert child_dispatch_dir != root_dispatch_dir

            runtime_after_continue = await _runtime_payload(client, task_id=task_id)
            assert runtime_after_continue["current_node_key"] == "implement_change"
