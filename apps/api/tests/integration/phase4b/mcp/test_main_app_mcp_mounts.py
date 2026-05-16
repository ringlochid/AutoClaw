from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from app.config import get_settings
from app.main import create_app
from autoclaw.openclaw.node_server import NODE_TOOL_NAMES
from autoclaw.openclaw.operator_server import OPERATOR_TOOL_NAMES
from fastapi import FastAPI
from tests.integration.phase3.runtime_support import prepare_runtime_db
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    load_current_node_mcp_session_key,
    mcp_client_session,
    node_mcp_client_session,
    node_mcp_headers,
    node_mcp_mount_path,
    phase3_runtime_api,
    seed_live_node_mcp_dispatch,
    tool_names,
)


@asynccontextmanager
async def _main_app_http_client(
    app: FastAPI,
    *,
    headers: dict[str, str] | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1",
            headers=headers,
        ) as client:
            yield client


async def test_phase4b_main_app_mounts_operator_mcp(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.main-app-operator-mcp"
    await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    app = create_app(enable_mcp_mounts=True)
    with openclaw_gateway_test_server.configured_env():
        async with mcp_client_session(app, url="http://127.0.0.1/operator/mcp") as session:
            tools_result = await session.list_tools()
            assert set(OPERATOR_TOOL_NAMES) <= set(tool_names(tools_result))


async def test_phase4b_main_app_mounts_task_bound_node_mcp(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.main-app-node-mcp"
    await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )
    with openclaw_gateway_test_server.configured_env():
        session_key = await load_current_node_mcp_session_key(task_id)
        app = create_app(enable_mcp_mounts=True)
        async with node_mcp_client_session(
            app,
            session_key=session_key,
            task_id=task_id,
        ) as session:
            tools_result = await session.list_tools()
            assert set(tool_names(tools_result)) == set(NODE_TOOL_NAMES)


async def test_phase4b_main_app_node_mcp_rejects_operator_bearer_without_session_identity(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.main-app-node-mcp-negative-auth"
    await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    app = create_app(enable_mcp_mounts=True)
    with openclaw_gateway_test_server.configured_env():
        async with _main_app_http_client(
            app,
            headers={"Authorization": f"Bearer {get_settings().api_key}"},
        ) as client:
            response = await client.get(node_mcp_mount_path())

    assert response.status_code == 400
    assert response.json() == {"error": "missing x-session-key header"}


async def test_phase4b_main_app_node_mcp_rejects_mismatched_session_and_task_headers(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_a_id = "task.phase4b.main-app-node-mcp-mismatch-a"
    task_b_id = "task.phase4b.main-app-node-mcp-mismatch-b"
    config_path = await prepare_runtime_db(tmp_path)
    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_a_id,
                task_root=tmp_path / "task-a-root",
                compiler_version="phase-4b-main-app-node-mcp-mismatch-a",
            )
            await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_b_id,
                task_root=tmp_path / "task-b-root",
                compiler_version="phase-4b-main-app-node-mcp-mismatch-b",
            )
            session_key = await load_current_node_mcp_session_key(task_a_id)
            app = create_app(enable_mcp_mounts=True)
            async with _main_app_http_client(
                app,
                headers=node_mcp_headers(
                    session_key=session_key,
                    task_id=task_b_id,
                ),
            ) as client:
                response = await client.get(node_mcp_mount_path())

    assert response.status_code == 409
    assert response.json() == {
        "error": (
            f"session key '{session_key}' is not bound to task "
            f"'{task_b_id}'"
        )
    }
