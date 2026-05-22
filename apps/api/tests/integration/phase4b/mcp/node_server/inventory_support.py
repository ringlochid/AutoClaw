from __future__ import annotations

from typing import Any

from autoclaw.openclaw.bindings import NodeToolContext
from autoclaw.openclaw.node_server import NODE_TOOL_NAMES, create_node_mcp_app
from starlette.applications import Starlette
from tests.integration.phase4b.mcp.support import (
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    tool_input_schema,
    tool_names,
)
from tests.integration.phase4b.mcp.teaching_support import (
    NODE_CURRENT_LOOKUP_TOOLS,
    assert_node_tool_teaching,
)

OPERATOR_ONLY_TOOLS = {
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
OPERATOR_DEFINITION_ONLY_TOOLS = {"list_definition_versions", "upload_definition", "start_task"}


def node_mcp_app() -> Starlette:
    return create_node_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))


def assert_static_node_tools(tools_result: Any) -> None:
    names = set(tool_names(tools_result))
    assert set(NODE_TOOL_NAMES) == names
    assert NODE_CURRENT_LOOKUP_TOOLS <= names
    assert names.isdisjoint(OPERATOR_ONLY_TOOLS)
    assert names.isdisjoint(OPERATOR_DEFINITION_ONLY_TOOLS)
    for tool_name in NODE_TOOL_NAMES:
        schema = tool_input_schema(tools_result, tool_name)
        if tool_name == "call_parent_tool":
            assert schema["discriminator"]["propertyName"] == "tool_name"
            for variant_ref in schema["oneOf"]:
                variant = schema["$defs"][variant_ref["$ref"].removeprefix("#/$defs/")]
                properties = set(variant["properties"])
                assert {"task_id", "session_key", "expected_structural_revision_id"} <= properties
            continue
        properties = set(schema.get("properties", {}))
        assert {"task_id", "session_key"} <= properties
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
    assert_node_tool_teaching(tools_result)


async def read_current_role_from_bound_node(context: NodeToolContext) -> dict[str, Any]:
    async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
        assert_static_node_tools(await session.list_tools())
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
