from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from autoclaw.interfaces.mcp.bindings import load_current_node_tool_context
from autoclaw.interfaces.mcp.node.server import create_node_mcp_server
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import runtime_read_json
from tests.integration.mcp.node_server.inventory_support import (
    assert_static_node_tools,
    node_mcp_app,
)
from tests.integration.mcp.support import (
    assert_tool_result_matches_output_schema,
    bootstrap_runtime_task,
    call_node_checkpoint,
    call_node_structural_tool,
    call_tool_result,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    runtime_api_context,
    tool_failure,
    tool_input_schema,
    tool_output_schema,
)
from tests.integration.runtime.contracts.workflows import root_descendant_replan_workflow


def _schema_object(value: object) -> dict[str, Any]:
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _schema_list(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def _failure_variant(schema: dict[str, Any]) -> dict[str, Any]:
    for variant in _schema_list(schema.get("oneOf", [])):
        if not isinstance(variant, dict):
            continue
        properties = variant.get("properties")
        if not isinstance(properties, dict):
            continue
        ok_schema = properties.get("ok")
        if isinstance(ok_schema, dict) and ok_schema.get("const") is False:
            return variant
    raise AssertionError("missing OperationFailure variant")


def _success_variant(schema: dict[str, Any]) -> dict[str, Any]:
    failure_variant = _failure_variant(schema)
    for variant in _schema_list(schema.get("oneOf", [])):
        if isinstance(variant, dict) and variant is not failure_variant:
            return cast(dict[str, Any], variant)
    raise AssertionError("missing success variant")


async def test_node_mcp_structural_tools_keep_top_level_revision_argument() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        tools = await session.list_tools()

    for tool_name in {
        "assign_child",
        "add_child",
        "update_child",
        "remove_child",
        "release_green",
        "release_blocked",
    }:
        schema = tool_input_schema(tools, tool_name)
        properties = _schema_object(schema["properties"])
        assert schema["type"] == "object"
        assert "expected_structural_revision_id" in properties
        assert "task_id" in properties
        assert "session_key" in properties


async def test_node_mcp_structural_tool_payload_schemas_stay_typed() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        tools = await session.list_tools()

    assign_schema = tool_input_schema(tools, "assign_child")
    assign_payload = _schema_object(_schema_object(assign_schema["properties"])["payload"])
    assert assign_schema["required"] == ["session_key", "task_id", "payload"]
    assert assign_payload["title"] == "AssignChildPayload"
    assert assign_payload["additionalProperties"] is False
    assert set(assign_payload["required"]) == {"child_node_key", "assignment_intent"}

    add_schema = tool_input_schema(tools, "add_child")
    add_payload = _schema_object(_schema_object(add_schema["properties"])["payload"])
    assert add_payload["title"] == "AddChildPayload"
    assert add_payload["additionalProperties"] is False
    assert set(add_payload["required"]) == {"child"}

    update_schema = tool_input_schema(tools, "update_child")
    update_payload = _schema_object(_schema_object(update_schema["properties"])["payload"])
    assert update_payload["title"] == "UpdateChildPayload"
    assert set(update_payload["required"]) == {"child_node_key", "patch"}

    remove_schema = tool_input_schema(tools, "remove_child")
    remove_payload = _schema_object(_schema_object(remove_schema["properties"])["payload"])
    assert remove_payload["title"] == "RemoveChildPayload"
    assert remove_payload["required"] == ["child_node_key"]

    release_green_schema = tool_input_schema(tools, "release_green")
    release_blocked_schema = tool_input_schema(tools, "release_blocked")
    assert "payload" not in _schema_object(release_green_schema["properties"])
    assert "payload" not in _schema_object(release_blocked_schema["properties"])


async def test_node_mcp_output_schemas_preserve_typed_result_contracts() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        tools = await session.list_tools()
        checkpoint_schema = tool_output_schema(tools, "record_checkpoint")
        boundary_schema = tool_output_schema(tools, "return_boundary")
        human_request_schema = tool_output_schema(tools, "open_human_request")
        command_run_schema = tool_output_schema(tools, "start_command_run")
        assign_child_schema = tool_output_schema(tools, "assign_child")
        add_child_schema = tool_output_schema(tools, "add_child")

    assert checkpoint_schema is not None
    assert checkpoint_schema["type"] == "object"
    assert checkpoint_schema["oneOf"]
    checkpoint_success_schema = _success_variant(checkpoint_schema)
    checkpoint_failure_schema = _failure_variant(checkpoint_schema)
    assert checkpoint_success_schema["required"] == [
        "attempt_id",
        "checkpoint_id",
        "checkpoint_ref",
        "latest_checkpoint_ref",
    ]
    checkpoint_ref_schema = _schema_object(
        _schema_object(checkpoint_success_schema["properties"])["checkpoint_ref"]
    )
    assert checkpoint_ref_schema["title"] == "CheckpointFileRef"
    assert set(checkpoint_ref_schema["required"]) == {"path", "description"}
    assert _schema_object(checkpoint_failure_schema["properties"])["code"] == {
        "$ref": "#/$defs/OperationFailureCode"
    }

    assert boundary_schema is not None
    assert boundary_schema["type"] == "object"
    assert boundary_schema["oneOf"]
    boundary_success_schema = _success_variant(boundary_schema)
    assert boundary_success_schema["required"] == ["accepted_boundary", "flow"]
    boundary_flow_schema = _schema_object(
        _schema_object(boundary_success_schema["properties"])["flow"]
    )
    assert boundary_flow_schema["title"] == "RuntimeFlowRead"
    assert "task_id" in boundary_flow_schema["properties"]
    latest_checkpoint_ref_schema = _schema_object(
        _schema_object(boundary_success_schema["properties"])["latest_checkpoint_ref"]
    )
    assert _schema_list(latest_checkpoint_ref_schema["anyOf"])[1] == {"type": "null"}

    assert assign_child_schema is not None
    assert assign_child_schema["type"] == "object"
    assert assign_child_schema["oneOf"]
    assign_child_success_schema = _success_variant(assign_child_schema)
    assert _schema_object(assign_child_success_schema["properties"])["target_assignment_key"] == {
        "minLength": 1,
        "title": "Target Assignment Key",
        "type": "string",
    }
    assert add_child_schema is not None
    assert add_child_schema["type"] == "object"
    assert add_child_schema["oneOf"]
    add_child_success_schema = _success_variant(add_child_schema)
    add_child_flow_schema = _schema_object(
        _schema_object(add_child_success_schema["properties"])["flow"]
    )
    assert add_child_flow_schema["title"] == "RuntimeFlowRead"
    assert "task_id" in add_child_flow_schema["properties"]

    assert human_request_schema is not None
    assert human_request_schema["type"] == "object"
    assert human_request_schema["oneOf"]
    human_request_success_schema = _success_variant(human_request_schema)
    assert human_request_success_schema["required"] == ["request_id", "task_id"]
    status_schema = _schema_object(
        _schema_object(human_request_success_schema["properties"])["status"]
    )
    assert status_schema["default"] == "open"
    assert set(status_schema["enum"]) == {"open", "resolved", "timed_out", "cancelled"}

    assert command_run_schema is not None
    assert command_run_schema["type"] == "object"
    assert command_run_schema["oneOf"]
    command_run_success_schema = _success_variant(command_run_schema)
    assert command_run_success_schema["required"] == ["run_id", "task_id", "state"]
    state_schema = _schema_object(_schema_object(command_run_success_schema["properties"])["state"])
    assert set(state_schema["enum"]) == {"pending_start", "running"}


async def test_node_mcp_human_request_open_schema_uses_shared_contract() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        tools = await session.list_tools()

    schema = tool_input_schema(tools, "open_human_request")
    properties = _schema_object(schema["properties"])
    request_schema = _schema_object(properties["request"])
    assert schema["required"] == ["session_key", "task_id", "request"]
    assert request_schema["title"] == "HumanRequestOpenRequest"
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "kind",
        "title",
        "summary",
        "items",
        "suggested_human_instruction",
    }
    assert set(_schema_object(request_schema["properties"])["kind"]["enum"]) == {
        "direction",
        "approval",
        "input",
        "review",
    }


async def test_node_mcp_command_run_start_schema_uses_shared_contract() -> None:
    app = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app, include_operator_auth=False) as session:
        tools = await session.list_tools()

    schema = tool_input_schema(tools, "start_command_run")
    properties = _schema_object(schema["properties"])
    request_schema = _schema_object(properties["request"])
    assert schema["required"] == ["session_key", "task_id", "request"]
    assert request_schema["title"] == "CommandRunStartRequest"
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {"command", "description"}
    assert "timeout_seconds" in _schema_object(request_schema["properties"])


async def test_node_mcp_rejects_validation_failures_with_operation_failure_shape() -> None:
    async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
        tools = await session.list_tools()
        result = await call_tool_result(
            session,
            "return_boundary",
            {
                "session_key": "session-missing-task",
                "boundary": "yield",
            },
        )

    failure = tool_failure(result)
    assert_tool_result_matches_output_schema(tools, "return_boundary", result)
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


async def test_node_mcp_is_dispatch_bound_and_keeps_operator_tools_out(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-mcp"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path):
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


async def test_node_mcp_exposes_current_only_lookup_and_structural_tools(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-mcp-current-only-lookup"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
        workflow_definition=root_descendant_replan_workflow(),
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
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
                added = await call_node_structural_tool(
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


async def test_node_mcp_mutation_results_keep_direct_typed_shapes(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-mcp-typed-results"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
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
                assigned = await call_node_structural_tool(
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
