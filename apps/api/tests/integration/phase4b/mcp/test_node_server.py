from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.openclaw.bindings import NodeToolContext, load_current_node_tool_context
from autoclaw.openclaw.node_server import (
    NODE_TOOL_NAMES,
    create_node_mcp_app,
    create_node_mcp_server,
)
from starlette.applications import Starlette
from tests.integration.phase3.contracts.workflows import root_descendant_replan_workflow
from tests.integration.phase3.runtime_support import prepare_runtime_db, runtime_read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_dispatch_support import (
    assert_same_dispatch_node_mcp_binding_state,
    revoke_same_dispatch_node_mcp_binding,
    seed_live_node_mcp_dispatch,
    seed_node_mcp_binding_pair,
)
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    call_node_parent_tool,
    call_tool_result,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    phase3_runtime_api,
    tool_input_schema,
    tool_names,
)

_OPERATOR_ONLY_TOOLS = {
    "list_runtime_tasks",
    "get_runtime_task",
    "get_operator_snapshot",
    "get_operator_trace",
    "pause_task",
    "continue_task",
    "cancel_task",
    "get_delivery_state_ref",
    "get_continuity_state_ref",
    "get_watchdog_state_ref",
    "get_provider_events_ref",
}
_NODE_CURRENT_LOOKUP_TOOLS = {"search_definitions", "get_definition"}
_OPERATOR_DEFINITION_ONLY_TOOLS = {"list_definition_versions", "upload_definition", "start_task"}


async def test_phase4b_node_mcp_call_parent_tool_keeps_top_level_revision_argument() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        schema = tool_input_schema(await session.list_tools(), "call_parent_tool")
        properties = schema.get("properties", {})
        assert "expected_structural_revision_id" in properties
        assert "task_id" in properties
        assert "session_key" in properties


def _node_mcp_app() -> Starlette:
    return create_node_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))


def _assert_static_node_tools(tools_result: Any) -> None:
    names = set(tool_names(tools_result))
    assert set(NODE_TOOL_NAMES) == names
    assert _NODE_CURRENT_LOOKUP_TOOLS <= names
    assert names.isdisjoint(_OPERATOR_ONLY_TOOLS)
    assert names.isdisjoint(_OPERATOR_DEFINITION_ONLY_TOOLS)
    for tool_name in NODE_TOOL_NAMES:
        schema = tool_input_schema(tools_result, tool_name)
        properties = set(schema.get("properties", {}))
        assert {"task_id", "session_key"} <= properties
        if tool_name == "call_parent_tool":
            assert "expected_structural_revision_id" in properties
        if tool_name == "search_definitions":
            assert "query" in properties and "q" not in properties
            assert set(schema.get("properties", {}).get("kind", {}).get("enum", [])) == {
                "policy",
                "role",
            }
        if tool_name == "get_definition":
            assert set(schema.get("properties", {}).get("kind", {}).get("enum", [])) == {
                "policy",
                "role",
            }


async def _read_current_role_from_bound_node(context: NodeToolContext) -> dict[str, Any]:
    async with mcp_client_session(_node_mcp_app(), include_operator_auth=False) as session:
        _assert_static_node_tools(await session.list_tools())
        return await call_tool_structured(
            session,
            "get_definition",
            {
                "session_key": context.session_key,
                "task_id": context.task_id,
                "kind": "role",
                "key": "researcher",
            },
        )


async def _assert_stale_boundary_rejected(context: NodeToolContext) -> None:
    async with mcp_client_session(_node_mcp_app(), include_operator_auth=False) as session:
        assert (
            await call_tool_result(
                session,
                "return_boundary",
                {
                    "session_key": context.session_key,
                    "task_id": context.task_id,
                    "boundary": "yield",
                },
            )
        ).isError is True


async def test_phase4b_node_mcp_is_dispatch_bound_and_keeps_operator_tools_out(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.node-mcp"
    config_path, task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_id,
                task_root=task_root,
                bootstrap_runtime=False,
            )
            context = await load_current_node_tool_context(task_id)
            async with mcp_client_session(_node_mcp_app(), include_operator_auth=False) as session:
                _assert_static_node_tools(await session.list_tools())
                role_detail = await call_tool_structured(
                    session,
                    "get_definition",
                    {
                        "session_key": context.session_key,
                        "task_id": context.task_id,
                        "kind": "role",
                        "key": "researcher",
                    },
                )
            assert role_detail["key"] == "researcher"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flow_status", "control_state", "control_state_reason"),
    (
        ("running", "live", "manual_revoke"),
        ("paused", "abort_requested", "pause_requested"),
        ("cancelled", "abort_requested", "cancel_requested"),
    ),
    ids=("revoked-binding", "paused-same-dispatch", "cancelled-same-dispatch"),
)
async def test_phase4b_node_mcp_rejects_same_dispatch_stale_authority(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
    flow_status: str,
    control_state: str,
    control_state_reason: str,
) -> None:
    task_id = f"task.phase4b.node-mcp-stale-{flow_status}"
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context = await seed_live_node_mcp_dispatch(
                api.session_factory, task_id=task_id, task_root=task_root
            )
            await revoke_same_dispatch_node_mcp_binding(
                api.session_factory,
                task_id=task_id,
                context=context,
                flow_status=flow_status,
                control_state=control_state,
                control_state_reason=control_state_reason,
            )
            await assert_same_dispatch_node_mcp_binding_state(
                api.session_factory,
                task_id=task_id,
                context=context,
                flow_status=flow_status,
                control_state=control_state,
            )
            await _assert_stale_boundary_rejected(context)


async def test_phase4b_node_mcp_rejects_mismatched_task_and_session_binding(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_a_id = "task.phase4b.node-mcp-mismatch-a"
    task_b_id = "task.phase4b.node-mcp-mismatch-b"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context_a, context_b = await seed_node_mcp_binding_pair(
                api.session_factory,
                tmp_path,
                task_a_id=task_a_id,
                task_b_id=task_b_id,
                compiler_stem="phase-4b-node-mcp-mismatch",
            )
            mismatched_context = NodeToolContext(
                task_id=context_b.task_id,
                dispatch_id=context_a.dispatch_id,
                node_session_id=context_a.node_session_id,
                session_key=context_a.session_key,
            )
            async with mcp_client_session(_node_mcp_app(), include_operator_auth=False) as session:
                result = await call_tool_result(
                    session,
                    "return_boundary",
                    {
                        "session_key": mismatched_context.session_key,
                        "task_id": task_b_id,
                        "boundary": "yield",
                    },
                )
            assert result.isError is True


async def test_phase4b_node_mcp_isolates_concurrent_live_task_sessions(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_a_id = "task.phase4b.node-mcp-concurrent-a"
    task_b_id = "task.phase4b.node-mcp-concurrent-b"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context_a, context_b = await seed_node_mcp_binding_pair(
                api.session_factory,
                tmp_path,
                task_a_id=task_a_id,
                task_b_id=task_b_id,
                compiler_stem="phase-4b-node-mcp-concurrent",
            )
            role_a, role_b = await asyncio.gather(
                _read_current_role_from_bound_node(context_a),
                _read_current_role_from_bound_node(context_b),
            )
            assert role_a["key"] == "researcher"
            assert role_b["key"] == "researcher"


async def test_phase4b_node_mcp_exposes_current_only_lookup_and_structural_tools(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.node-mcp-current-only-lookup"
    config_path, task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
        workflow_definition=root_descendant_replan_workflow(),
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_id,
                task_root=task_root,
                bootstrap_runtime=False,
            )
            runtime = await runtime_read_json(api.client, task_id)
            context = await load_current_node_tool_context(task_id)
            async with mcp_client_session(_node_mcp_app(), include_operator_auth=False) as session:
                _assert_static_node_tools(await session.list_tools())
                role_search = await call_tool_structured(
                    session,
                    "search_definitions",
                    {
                        "session_key": context.session_key,
                        "task_id": context.task_id,
                        "kind": "role",
                        "query": "researcher",
                        "limit": 5,
                    },
                )
                role_detail = await call_tool_structured(
                    session,
                    "get_definition",
                    {
                        "session_key": context.session_key,
                        "task_id": context.task_id,
                        "kind": "role",
                        "key": "researcher",
                    },
                )
                added = await call_node_parent_tool(
                    session,
                    context=context,
                    tool_name="add_child",
                    payload={
                        "target_parent_node_key": "nested_parent",
                        "child": {
                            "node_key": "qa_probe",
                            "role": "researcher",
                            "description": "Added through node MCP current-only lookup.",
                        },
                    },
                    active_flow_revision_id=cast(str, runtime["active_flow_revision_id"]),
                )

                assert role_search["kind"] == "role"
                assert any(item["key"] == "researcher" for item in role_search["items"])
                assert role_detail["key"] == "researcher"
                assert added["tool_name"] == "add_child"
                assert added["target_node_key"] == "qa_probe"
                assert (
                    added["flow"]["active_flow_revision_id"] != runtime["active_flow_revision_id"]
                )
