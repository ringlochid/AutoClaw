from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from app import cli
from app.config import get_settings
from app.db.session import get_session_factory
from app.main import create_app
from app.runtime.effects import wait_for_runtime_effects
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}


@dataclass(frozen=True)
class Phase3RuntimeApi:
    session_factory: async_sessionmaker[AsyncSession]
    client: AsyncClient


@dataclass(frozen=True)
class ChildDispatchStage:
    root_session_key: str
    worker_session_key: str
    active_flow_revision_id: str


@asynccontextmanager
async def phase3_runtime_api(config_path: Path) -> AsyncIterator[Phase3RuntimeApi]:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        app = create_app()
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                yield Phase3RuntimeApi(session_factory=session_factory, client=client)


async def runtime_read_json(client: AsyncClient, task_id: str) -> dict[str, Any]:
    response = await client.get(f"/runtime/tasks/{task_id}", headers=OPERATOR_HEADERS)
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


async def parent_tool(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    tool_name: str,
    payload: dict[str, Any],
    active_flow_revision_id: str,
) -> Response:
    return await client.post(
        f"/callback/tasks/{task_id}/tools/{tool_name}",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": tool_name,
            "payload": payload,
            "expected_structural_revision_id": active_flow_revision_id,
        },
    )


async def assign_child(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    child_node_key: str,
    active_flow_revision_id: str,
    summary: str = "go",
    instruction: str = "go",
) -> Response:
    return await parent_tool(
        client,
        task_id=task_id,
        session_key=session_key,
        tool_name="assign_child",
        payload={
            "child_node_key": child_node_key,
            "assignment_intent": {
                "summary": summary,
                "instruction": instruction,
            },
        },
        active_flow_revision_id=active_flow_revision_id,
    )


async def boundary(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    boundary_name: str,
) -> Response:
    return await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"boundary": boundary_name},
    )


async def pause_flow(
    client: AsyncClient,
    *,
    task_id: str,
    active_flow_revision_id: str,
) -> Response:
    return await client.post(
        f"/runtime/tasks/{task_id}/pause",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": active_flow_revision_id},
    )


async def continue_flow(
    client: AsyncClient,
    *,
    task_id: str,
    active_flow_revision_id: str,
) -> Response:
    return await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": active_flow_revision_id},
    )


async def record_checkpoint(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    checkpoint_kind: str = "terminal",
    outcome: str | None,
    summary: str,
    next_step: str,
    produced_artifacts: Sequence[dict[str, str]] = (),
    transient_surfaces: Sequence[dict[str, str]] = (),
    wait_for_effects: bool = True,
) -> Response:
    checkpoint: dict[str, Any] = {
        "checkpoint_kind": checkpoint_kind,
        "handoff": {
            "summary": summary,
            "next_step": next_step,
        },
    }
    if outcome is not None:
        checkpoint["outcome"] = outcome
    if produced_artifacts:
        checkpoint["produced_artifacts"] = list(produced_artifacts)
    if transient_surfaces:
        checkpoint["transient_surfaces"] = list(transient_surfaces)
    response = await client.post(
        f"/callback/tasks/{task_id}/checkpoint",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"checkpoint": checkpoint},
    )
    if response.status_code == 200 and wait_for_effects:
        await wait_for_runtime_effects(task_id=task_id)
    return response
