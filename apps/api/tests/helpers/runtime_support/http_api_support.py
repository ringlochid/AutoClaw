from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.main import create_app
from autoclaw.persistence.session import dispose_test_db_engine, get_session_factory
from autoclaw.runtime.lifecycle import shutdown_runtime_lifecycle
from autoclaw.runtime.post_commit import drive_runtime_once
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.operator_auth_headers import OPERATOR_HEADERS, seeded_runtime_headers


def _callback_params(session_key: str) -> dict[str, str]:
    return {"session_key": session_key}


@dataclass(frozen=True)
class RuntimeApiContext:
    session_factory: async_sessionmaker[AsyncSession]
    client: AsyncClient


@dataclass(frozen=True)
class ChildDispatchStage:
    root_session_key: str
    worker_session_key: str
    active_flow_revision_id: str
    worker_node_key: str


@asynccontextmanager
async def runtime_api_context(config_path: Path) -> AsyncIterator[RuntimeApiContext]:
    await shutdown_runtime_lifecycle()
    await dispose_test_db_engine()
    with cli.command_env(config_path=config_path, env="test"):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        app = create_app(should_enable_mcp_mounts=False)
        try:
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    yield RuntimeApiContext(session_factory=session_factory, client=client)
        finally:
            await shutdown_runtime_lifecycle()
            await dispose_test_db_engine()


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
        params=_callback_params(session_key),
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
        params=_callback_params(session_key),
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
        headers=seeded_runtime_headers(task_id),
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
        headers=seeded_runtime_headers(task_id),
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
        params=_callback_params(session_key),
        json={"checkpoint": checkpoint},
    )
    if response.status_code == 200 and wait_for_effects:
        await drive_runtime_once(task_id=task_id)
    return response
