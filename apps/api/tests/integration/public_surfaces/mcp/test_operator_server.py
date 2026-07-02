from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml
from anyio import Path as AnyioPath
from autoclaw.interfaces.mcp.operator.server import (
    create_operator_mcp_app,
    create_operator_mcp_server,
)
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import prepare_runtime_db
from tests.helpers.seeded_runtime_support import task_compose_payload
from tests.integration.mcp.support import (
    bootstrap_runtime_task,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    runtime_api_context,
    tool_description,
    tool_input_schema,
    tool_names,
    tool_read_only_hint,
)

_REMOVED_OPERATOR_DRAFT_MUTATION_TOOLS = {
    "list_definition_draft_sets",
    "get_definition_draft_set",
    "create_definition_draft_set",
    "delete_definition_draft_set",
    "materialize_definition_draft_set",
    "write_definition_draft_file",
    "reset_definition_draft_file",
    "rematerialize_current_definition_draft_file",
    "validate_definition_draft_set",
    "apply_definition_draft_set",
    "preview_definition_draft_set_task_compose",
}


def _assert_timestamp_has_timezone(value: str) -> None:
    assert value.endswith("Z") or "+" in value or value.rfind("-") > value.find("T"), value
    normalized = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
    assert datetime.fromisoformat(normalized).tzinfo is not None


def _assert_query_schema(tool_schema: dict[str, object]) -> None:
    properties = cast(dict[str, object], tool_schema.get("properties", {}))
    assert "query" in properties
    assert "q" not in properties


async def test_operator_mcp_uses_query_arguments_in_tool_schemas() -> None:
    app = create_operator_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))

    async with mcp_client_session(app) as session:
        tools_result = await session.list_tools()
        _assert_query_schema(tool_input_schema(tools_result, "list_runtime_tasks"))
        _assert_query_schema(tool_input_schema(tools_result, "get_operator_trace"))
        _assert_query_schema(tool_input_schema(tools_result, "search_definitions"))
        assert set(tool_input_schema(tools_result, "upload_definition").get("properties", {})) == {
            "definition_path"
        }
        assert set(tool_input_schema(tools_result, "start_task").get("properties", {})) == {
            "task_compose_path"
        }
        for tool_name in {"search_definitions", "get_definition", "list_definition_versions"}:
            description = tool_description(tools_result, tool_name)
            assert description.startswith("Read-only:"), (tool_name, description)
            assert tool_read_only_hint(tools_result, tool_name) is True, tool_name
        assert "discover candidates" in tool_description(tools_result, "search_definitions")
        assert "inspect one current revision" in tool_description(tools_result, "get_definition")
        assert "not normal planning" in tool_description(tools_result, "list_definition_versions")
        for tool_name in {"upload_definition", "start_task"}:
            description = tool_description(tools_result, tool_name)
            assert description.startswith("Mutating:"), (tool_name, description)
            assert "Local file path on the AutoClaw host." in description, (
                tool_name,
                description,
            )
            assert tool_read_only_hint(tools_result, tool_name) is False, tool_name
        assert "Inspect current definitions first if you are unsure" in tool_description(
            tools_result, "upload_definition"
        )
        assert "Creates task root and starts real runtime effects." in tool_description(
            tools_result, "start_task"
        )
        assert "create and start a real task" in tool_description(tools_result, "start_task")
        assert _REMOVED_OPERATOR_DRAFT_MUTATION_TOOLS.isdisjoint(set(tool_names(tools_result)))


async def test_operator_mcp_server_instructions_include_definition_writes() -> None:
    server = create_operator_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1")
    )
    instructions = server.instructions
    assert instructions is not None
    assert "Definitions and task start" in instructions
    assert "definition draft authoring stays on the trusted HTTP /authoring" in instructions
    assert "apply_definition_draft_set" not in instructions


async def test_operator_mcp_exposes_runtime_support_and_definition_tools(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.operator-mcp-surface"
    _config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(_config_path):
            app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            async with mcp_client_session(app) as session:
                runtime = await call_tool_structured(
                    session,
                    "get_runtime_task",
                    {"task_id": task_id},
                )
                assert runtime["task_id"] == task_id
                _assert_timestamp_has_timezone(str(runtime["updated_at"]))

                runtime_list = await call_tool_structured(
                    session,
                    "list_runtime_tasks",
                    {"query": task_id, "limit": 5},
                )
                assert runtime_list["items"]
                _assert_timestamp_has_timezone(str(runtime_list["items"][0]["updated_at"]))

                workflow_search = await call_tool_structured(
                    session,
                    "search_definitions",
                    {"kind": "workflow", "query": "normal-parent-first-release", "limit": 5},
                )
                assert workflow_search["kind"] == "workflow"
                assert any(
                    item["key"] == "normal-parent-first-release"
                    for item in workflow_search["items"]
                )

                role_search = await call_tool_structured(
                    session,
                    "search_definitions",
                    {"kind": "role", "allowed_node_kind": "worker", "limit": 20},
                )
                assert role_search["kind"] == "role"
                assert role_search["items"]
                assert all(
                    "worker" in (item["allowed_node_kinds"] or []) for item in role_search["items"]
                )

                workflow_detail = await call_tool_structured(
                    session,
                    "get_definition",
                    {"kind": "workflow", "key": "normal-parent-first-release"},
                )
                assert workflow_detail["key"] == "normal-parent-first-release"
                assert workflow_detail["content"]["id"] == "normal-parent-first-release"
                _assert_timestamp_has_timezone(str(workflow_detail["updated_at"]))

                workflow_versions = await call_tool_structured(
                    session,
                    "list_definition_versions",
                    {"kind": "workflow", "key": "normal-parent-first-release"},
                )
                assert workflow_versions["kind"] == "workflow"
                assert workflow_versions["key"] == "normal-parent-first-release"
                assert workflow_versions["current_revision_no"] >= 1
                assert workflow_versions["items"]
                _assert_timestamp_has_timezone(str(workflow_versions["items"][0]["updated_at"]))


def _write_role_definition(path: Path, description: str) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "kind": "role",
                "id": "operator-mcp-role",
                "title": "Operator MCP Role",
                "description": description,
                "allowed_node_kinds": ["worker"],
                "instruction": "Stay scoped to the uploaded role contract.",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_task_compose(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            task_compose_payload("normal-parent-first-release").model_dump(mode="json"),
            sort_keys=False,
        ),
        encoding="utf-8",
    )


async def _assert_uploaded_role_round_trip(session: Any, role_definition_path: Path) -> None:
    uploaded = await call_tool_structured(
        session,
        "upload_definition",
        {"definition_path": str(role_definition_path)},
    )
    assert uploaded["key"] == "operator-mcp-role"
    assert uploaded["revision_no"] == 1
    assert uploaded["content"]["id"] == "operator-mcp-role"
    _assert_timestamp_has_timezone(str(uploaded["updated_at"]))

    _write_role_definition(role_definition_path, "Role uploaded through operator MCP. revision 2.")
    uploaded_revision = await call_tool_structured(
        session,
        "upload_definition",
        {"definition_path": str(role_definition_path)},
    )
    assert uploaded_revision["revision_no"] == 2
    assert uploaded_revision["content"]["description"].endswith("revision 2.")

    current_role = await call_tool_structured(
        session,
        "get_definition",
        {"kind": "role", "key": "operator-mcp-role"},
    )
    assert current_role["revision_no"] == 2
    assert current_role["content"]["description"].endswith("revision 2.")

    role_versions = await call_tool_structured(
        session,
        "list_definition_versions",
        {"kind": "role", "key": "operator-mcp-role", "sort": "revision_no_desc"},
    )
    assert role_versions["current_revision_no"] == 2
    assert [item["revision_no"] for item in role_versions["items"][:2]] == [2, 1]


async def _assert_started_task(session: Any, task_compose_path: Path) -> None:
    started = await call_tool_structured(
        session,
        "start_task",
        {"task_compose_path": str(task_compose_path)},
    )
    assert started["task_id"]
    assert started["compiled_plan_id"] == f"compiled-plan.{started['task_id']}"
    assert started["active_flow_revision_id"] == f"flow-revision.flow.{started['task_id']}.01"
    assert started["flow_status"] == "running"
    manifest_path = Path(str(started["workflow_manifest_ref"]["path"]))
    assert manifest_path.name == "workflow-manifest.md"
    assert await AnyioPath(manifest_path).exists()

    runtime = await call_tool_structured(
        session,
        "get_runtime_task",
        {"task_id": started["task_id"]},
    )
    assert runtime["task_id"] == started["task_id"]
    assert runtime["workflow_key"] == "normal-parent-first-release"


async def test_operator_mcp_uploads_definitions_and_starts_tasks(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    role_definition_path = tmp_path / "operator-mcp-role.yaml"
    task_compose_path = tmp_path / "task-compose.yaml"
    _write_role_definition(role_definition_path, "Role uploaded through operator MCP.")
    _write_task_compose(task_compose_path)

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path):
            app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            async with mcp_client_session(app) as session:
                await _assert_uploaded_role_round_trip(session, role_definition_path)
                await _assert_started_task(session, task_compose_path)
