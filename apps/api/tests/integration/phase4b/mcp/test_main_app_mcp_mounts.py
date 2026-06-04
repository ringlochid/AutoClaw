from __future__ import annotations

from pathlib import Path

from autoclaw.main import create_app
from autoclaw.openclaw.bindings import load_current_node_tool_context
from autoclaw.openclaw.node_server import NODE_TOOL_NAMES
from autoclaw.openclaw.operator_server import OPERATOR_TOOL_NAMES
from tests.integration.phase3.runtime_support import prepare_runtime_db
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_dispatch_support import seed_live_node_mcp_dispatch
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    call_tool_result,
    load_current_node_mcp_session_key,
    mcp_client_session,
    node_mcp_client_session,
    phase3_runtime_api,
    tool_failure,
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


async def test_phase4b_main_app_mounts_static_node_mcp(
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
        app = create_app(enable_mcp_mounts=True)
        async with node_mcp_client_session(app) as session:
            tools_result = await session.list_tools()
            assert set(tool_names(tools_result)) == set(NODE_TOOL_NAMES)


async def test_phase4b_main_app_node_mcp_rejects_tool_call_without_session_arguments(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.main-app-node-mcp-negative-auth"
    await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        app = create_app(enable_mcp_mounts=True)
        async with node_mcp_client_session(app) as session:
            result = await call_tool_result(
                session,
                "return_boundary",
                {"boundary": "yield"},
            )

    failure = tool_failure(result)
    assert failure["code"] == "invalid_request_shape"
    assert failure["retryable"] is False


async def test_phase4b_main_app_node_mcp_rejects_mismatched_session_and_task_arguments(
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
            async with node_mcp_client_session(app) as session:
                result = await call_tool_result(
                    session,
                    "return_boundary",
                    {
                        "session_key": session_key,
                        "task_id": task_b_id,
                        "boundary": "yield",
                    },
                )

    failure = tool_failure(result)
    assert failure["code"] == "stale_dispatch"
    assert failure["summary"] == f"session key '{session_key}' is not bound to task '{task_b_id}'"


async def test_phase4b_main_app_node_mcp_rejects_mismatched_parent_tool_discriminator_payload(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.main-app-node-mcp-parent-tool-shape-mismatch"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    mismatch_cases = (
        (
            "assign_child",
            {
                "child": {
                    "node_key": "qa_probe",
                    "role": "researcher",
                    "description": "Wrong payload family for assign_child.",
                }
            },
        ),
        (
            "add_child",
            {
                "child_node_key": "implementation_subtree",
                "assignment_intent": {
                    "summary": "Wrong payload family for add_child.",
                    "instruction": "Keep the mounted MCP validation strict.",
                },
            },
        ),
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path):
            context = await load_current_node_tool_context(task_id)
            app = create_app(enable_mcp_mounts=True)
            async with node_mcp_client_session(app) as session:
                for tool_name, payload in mismatch_cases:
                    result = await call_tool_result(
                        session,
                        tool_name,
                        {
                            "session_key": context.session_key,
                            "task_id": context.task_id,
                            "payload": payload,
                        },
                    )
                    failure = tool_failure(result)
                    assert failure["code"] == "invalid_request_shape"
                    assert (
                        failure["summary"]
                        == "request shape does not match the canonical runtime surface"
                    )
                    assert failure["retryable"] is False
                    assert result.content[0].text == failure["summary"]
