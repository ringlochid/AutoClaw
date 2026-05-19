from __future__ import annotations

from pathlib import Path
from typing import cast

from autoclaw.openclaw.bindings import load_current_node_tool_context
from autoclaw.openclaw.node_server import create_node_mcp_server
from tests.integration.phase3.contracts.workflows import root_descendant_replan_workflow
from tests.integration.phase3.runtime_support import runtime_read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_dispatch_support import seed_live_node_mcp_dispatch
from tests.integration.phase4b.mcp.node_server.inventory_support import (
    assert_static_node_tools,
    node_mcp_app,
)
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    call_node_parent_tool,
    call_tool_result,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    phase3_runtime_api,
    tool_failure,
    tool_input_schema,
)


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


async def test_phase4b_node_mcp_rejects_validation_failures_with_operation_failure_shape() -> None:
    async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
        result = await call_tool_result(
            session,
            "return_boundary",
            {
                "session_key": "session-missing-task",
                "boundary": "yield",
            },
        )

    failure = tool_failure(result)
    assert failure == {
        "ok": False,
        "code": "invalid_request_shape",
        "summary": "request shape does not match the canonical runtime surface",
        "retryable": False,
        "field_path": "task_id",
        "suggested_next_step": (
            "Reread the canonical request shape and resend the request with only the live "
            "required fields."
        ),
    }
    assert result.content[0].text == failure["summary"]


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
            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                assert_static_node_tools(await session.list_tools())
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
            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                assert_static_node_tools(await session.list_tools())
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
