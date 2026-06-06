from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autoclaw.persistence import DispatchTurnModel, FlowModel, NodeSessionModel
from autoclaw.runtime.post_commit import (
    drive_runtime_once,
    drive_runtime_until,
    wait_for_runtime_effects,
)
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.operator_auth_headers import OPERATOR_HEADERS

EXPECTED_CURRENT_PATH_NAMES = (
    "workflow-manifest.md",
    "delivery-state.json",
    "continuity-state.json",
    "watchdog-state.json",
    "provider-events.ndjson",
)


async def current_session_key(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    expected_node_key: str | None = None,
) -> str:
    current_live_session_key: str | None = None

    async def live_session_ready() -> bool:
        nonlocal current_live_session_key
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            if expected_node_key is not None:
                session_key = await session.scalar(
                    select(NodeSessionModel.session_key)
                    .join(
                        DispatchTurnModel,
                        DispatchTurnModel.dispatch_id == NodeSessionModel.dispatch_id,
                    )
                    .where(
                        DispatchTurnModel.task_id == task_id,
                        DispatchTurnModel.node_key == expected_node_key,
                        NodeSessionModel.session_status == "live",
                        NodeSessionModel.closed_at.is_(None),
                    )
                    .order_by(NodeSessionModel.opened_at.desc())
                    .limit(1)
                )
                if isinstance(session_key, str):
                    current_live_session_key = session_key
                    return True
            if flow.current_open_dispatch_id is None:
                return False
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            assert dispatch is not None
            if expected_node_key is not None and dispatch.node_key != expected_node_key:
                return False
            session_key = await session.scalar(
                select(NodeSessionModel.session_key)
                .where(
                    NodeSessionModel.dispatch_id == dispatch.dispatch_id,
                    NodeSessionModel.session_status == "live",
                    NodeSessionModel.closed_at.is_(None),
                )
                .order_by(NodeSessionModel.opened_at.desc())
                .limit(1)
            )
            if isinstance(session_key, str):
                current_live_session_key = session_key
                return True
        return False

    await drive_runtime_until(
        live_session_ready,
        task_id=task_id,
        max_cycles=40,
    )
    assert current_live_session_key is not None
    return current_live_session_key


async def current_dispatch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> DispatchTurnModel:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        return dispatch


async def assert_gateway_dispatch_binding(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    session_key: str,
    expected_run_id: str,
) -> DispatchTurnModel:
    dispatch = await current_dispatch(session_factory, task_id=task_id)
    assert dispatch.gateway_session_key is not None
    assert dispatch.gateway_session_key == session_key
    assert dispatch.gateway_run_id == expected_run_id
    return dispatch


def assert_materialized_snapshot(
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
    assert "previous_response_id" not in prompt_request
    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert f"- current node anchor: {expected_node_key}" in prompt_text
    return dispatch_dir


async def runtime_payload(
    client: AsyncClient,
    *,
    task_id: str,
) -> dict[str, Any]:
    response = await client.get(f"/runtime/tasks/{task_id}", headers=OPERATOR_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def snapshot_dispatch_dir(
    client: AsyncClient,
    *,
    task_id: str,
    expected_node_key: str,
) -> Path:
    last_payload: dict[str, Any] | None = None

    async def snapshot_ready() -> bool:
        nonlocal last_payload
        response = await client.get(
            f"/operator/tasks/{task_id}/snapshot",
            headers=OPERATOR_HEADERS,
        )
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        last_payload = payload
        current_paths = payload["current_paths"]
        return (
            isinstance(current_paths, list)
            and tuple(Path(str(entry["path"])).name for entry in current_paths)
            == EXPECTED_CURRENT_PATH_NAMES
        )

    await drive_runtime_until(
        snapshot_ready,
        task_id=task_id,
        max_cycles=40,
    )
    assert last_payload is not None
    return assert_materialized_snapshot(last_payload, expected_node_key=expected_node_key)


async def assign_child_and_yield(
    client: AsyncClient,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    session_key: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    assign_child = await client.post(
        f"/callback/tasks/{task_id}/tools/assign_child",
        params={"session_key": session_key},
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
    session_key = await current_session_key(
        session_factory,
        task_id=task_id,
        expected_node_key="root",
    )
    yielded = await client.post(
        f"/callback/tasks/{task_id}/boundary",
        params={"session_key": session_key},
        json={"boundary": "yield"},
    )
    assert yielded.status_code == 200
    payload = yielded.json()
    assert isinstance(payload, dict)
    return payload


async def add_child_and_reread_manifest(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    active_flow_revision_id: str,
    task_root: Path,
) -> str:
    add_child = await client.post(
        f"/callback/tasks/{task_id}/tools/add_child",
        params={"session_key": session_key},
        json={
            "tool_name": "add_child",
            "payload": {
                "child": {
                    "node_key": "qa_sweep",
                    "role": "architect",
                    "description": "Perform a bounded QA sweep before release.",
                }
            },
            "expected_structural_revision_id": active_flow_revision_id,
        },
    )
    assert add_child.status_code == 200
    payload = add_child.json()
    assert isinstance(payload, dict)
    manifest_markdown = (task_root / "_runtime" / "workflow-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "qa_sweep" in manifest_markdown
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return str(flow["active_flow_revision_id"])


async def continue_runtime(
    client: AsyncClient,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    await mark_current_dispatch_inactive(session_factory, task_id=task_id)
    response = await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": active_flow_revision_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    await drive_runtime_once(task_id=task_id)
    return payload


async def mark_current_dispatch_inactive(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> None:
    await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
    await drive_runtime_once(task_id=task_id)
