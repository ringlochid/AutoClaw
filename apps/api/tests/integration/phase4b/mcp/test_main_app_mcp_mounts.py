from __future__ import annotations

from pathlib import Path

from app.main import create_app
from autoclaw.openclaw.bindings import load_current_node_mcp_binding
from autoclaw.openclaw.node_server import NODE_TOOL_NAMES
from autoclaw.openclaw.operator_server import OPERATOR_TOOL_NAMES
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    mcp_client_session,
    tool_names,
)


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
    _config_path, task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )
    del _config_path
    del task_root
    with openclaw_gateway_test_server.configured_env():
        await load_current_node_mcp_binding(task_id)
        app = create_app(enable_mcp_mounts=True)
        async with mcp_client_session(
            app,
            url=f"http://127.0.0.1/node/mcp/?task_id={task_id}",
        ) as session:
            tools_result = await session.list_tools()
            assert set(tool_names(tools_result)) == set(NODE_TOOL_NAMES)
