from __future__ import annotations

from pathlib import Path
from typing import cast

from autoclaw.openclaw.bindings import load_current_node_tool_context
from autoclaw.openclaw.node_server import create_node_mcp_server
from tests.integration.phase3.contracts.workflows import root_descendant_replan_workflow
from tests.integration.phase3.runtime_support import runtime_read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_server.inventory_support import (
    assert_static_node_tools,
    node_mcp_app,
)
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    call_node_checkpoint,
    call_node_parent_tool,
    call_tool_result,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    phase3_runtime_api,
    tool_failure,
    tool_input_schema,
    tool_output_schema,
)


async def test_phase4b_node_mcp_call_parent_tool_keeps_top_level_revision_argument() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        schema = tool_input_schema(await session.list_tools(), "call_parent_tool")
        assert schema["type"] == "object"
        for variant_ref in schema["oneOf"]:
            variant = schema["$defs"][variant_ref["$ref"].removeprefix("#/$defs/")]
            properties = variant["properties"]
            assert "expected_structural_revision_id" in properties
            assert "task_id" in properties
            assert "session_key" in properties


async def test_phase4b_node_mcp_call_parent_tool_schema_is_discriminated() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        schema = tool_input_schema(await session.list_tools(), "call_parent_tool")

    assert schema["type"] == "object"
    assert schema["discriminator"]["propertyName"] == "tool_name"
    mappings = schema["discriminator"]["mapping"]
    variants = schema["$defs"]
    expected_payloads = {
        "assign_child": "AssignChildPayload",
        "add_child": "AddChildPayload",
        "update_child": "UpdateChildPayload",
        "remove_child": "RemoveChildPayload",
        "release_green": "ReleaseGreenPayload",
        "release_blocked": "ReleaseBlockedPayload",
    }

    for tool_name, payload_name in expected_payloads.items():
        variant_name = mappings[tool_name].removeprefix("#/$defs/")
        variant = variants[variant_name]
        assert {"session_key", "task_id", "payload"} <= set(variant["required"])
        assert variant["properties"]["tool_name"]["const"] == tool_name
        assert variant["properties"]["tool_name"]["title"] == "Tool Name"
        assert variant["properties"]["payload"] == {"$ref": f"#/$defs/{payload_name}"}

    assert variants["AssignChildPayload"]["additionalProperties"] is False
    assert variants["AddChildPayload"]["additionalProperties"] is False
    assert variants["ReleaseGreenPayload"]["properties"] == {}
    assert variants["ReleaseBlockedPayload"]["properties"] == {}


async def test_phase4b_node_mcp_output_schemas_preserve_typed_result_contracts() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        tools = await session.list_tools()
        checkpoint_schema = tool_output_schema(tools, "record_checkpoint")
        boundary_schema = tool_output_schema(tools, "return_boundary")
        parent_tool_schema = tool_output_schema(tools, "call_parent_tool")

    assert checkpoint_schema is not None
    assert checkpoint_schema["required"] == [
        "attempt_id",
        "checkpoint_id",
        "checkpoint_ref",
        "latest_checkpoint_ref",
    ]
    assert checkpoint_schema["properties"]["checkpoint_ref"] == {
        "$ref": "#/$defs/CheckpointFileRef"
    }

    assert boundary_schema is not None
    assert boundary_schema["required"] == ["accepted_boundary", "flow"]
    assert boundary_schema["properties"]["flow"] == {"$ref": "#/$defs/RuntimeFlowRead"}
    assert boundary_schema["properties"]["latest_checkpoint_ref"]["anyOf"][1] == {"type": "null"}

    assert parent_tool_schema is not None
    assert parent_tool_schema["type"] == "object"
    assert parent_tool_schema["discriminator"]["propertyName"] == "tool_name"
    parent_mappings = parent_tool_schema["discriminator"]["mapping"]
    parent_variants = parent_tool_schema["$defs"]
    assert parent_variants[parent_mappings["assign_child"].removeprefix("#/$defs/")]["properties"][
        "target_assignment_key"
    ] == {"minLength": 1, "title": "Target Assignment Key", "type": "string"}
    assert parent_variants[parent_mappings["add_child"].removeprefix("#/$defs/")]["properties"][
        "flow"
    ] == {"$ref": "#/$defs/RuntimeFlowRead"}


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
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path):
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
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
        workflow_definition=root_descendant_replan_workflow(),
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
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
                assert "result" not in added
                assert added["tool_name"] == "add_child"
                assert added["target_node_key"] == "qa_probe"
                assert (
                    added["flow"]["active_flow_revision_id"] != runtime["active_flow_revision_id"]
                )


async def test_phase4b_node_mcp_mutation_results_keep_direct_typed_shapes(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.node-mcp-typed-results"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            runtime = await runtime_read_json(api.client, task_id)
            context = await load_current_node_tool_context(task_id)
            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                checkpoint = await call_node_checkpoint(
                    session,
                    context=context,
                    checkpoint={
                        "checkpoint_kind": "progress",
                        "handoff": {
                            "summary": "Checkpoint through node MCP.",
                            "next_step": "Continue the live dispatch.",
                        },
                    },
                )
                assigned = await call_node_parent_tool(
                    session,
                    context=context,
                    tool_name="assign_child",
                    payload={
                        "child_node_key": "implementation_subtree",
                        "assignment_intent": {
                            "summary": "Stage a bounded child before yielding.",
                            "instruction": "Return immediately after the child handoff.",
                        },
                    },
                    active_flow_revision_id=cast(str, runtime["active_flow_revision_id"]),
                )
                boundary = await call_tool_structured(
                    session,
                    "return_boundary",
                    {
                        "session_key": context.session_key,
                        "task_id": context.task_id,
                        "boundary": "yield",
                    },
                )

    assert "result" not in checkpoint
    assert set(checkpoint) == {
        "attempt_id",
        "checkpoint_id",
        "checkpoint_ref",
        "latest_checkpoint_ref",
    }
    assert set(checkpoint["checkpoint_ref"]) == {"path", "description"}

    assert "result" not in assigned
    assert assigned["tool_name"] == "assign_child"
    assert set(assigned) >= {
        "tool_name",
        "target_node_key",
        "target_assignment_key",
        "target_attempt_id",
        "flow",
    }

    assert "result" not in boundary
    assert set(boundary) == {"accepted_boundary", "flow", "latest_checkpoint_ref"}
    assert boundary["accepted_boundary"] == "yield"
    assert set(boundary["flow"]) >= {
        "task_id",
        "task_title",
        "task_summary",
        "status",
        "active_flow_revision_id",
        "workflow_manifest_ref",
        "updated_at",
    }
