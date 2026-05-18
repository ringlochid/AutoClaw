from __future__ import annotations

from typing import Any

from tests.integration.phase4b.mcp.support import tool_description, tool_read_only_hint

PHASE4B_OPERATOR_READ_ONLY_TOOLS = {
    "list_runtime_tasks",
    "get_runtime_task",
    "get_operator_snapshot",
    "get_operator_trace",
    "get_delivery_state_ref",
    "get_continuity_state_ref",
    "get_watchdog_state_ref",
    "get_provider_events_ref",
}
PHASE4B_OPERATOR_MUTATING_TOOLS = {"pause_task", "continue_task", "cancel_task"}
NODE_CURRENT_LOOKUP_TOOLS = {"search_definitions", "get_definition"}
NODE_MUTATING_TOOLS = {"record_checkpoint", "return_boundary", "call_parent_tool"}


def assert_phase4b_operator_tool_teaching(tools_result: Any) -> None:
    for tool_name in PHASE4B_OPERATOR_READ_ONLY_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Read-only:"), (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is True, tool_name
    for tool_name in PHASE4B_OPERATOR_MUTATING_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Mutating:"), (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is False, tool_name
    assert "Do not use for status checks." in tool_description(tools_result, "continue_task")
    for tool_name in {
        "get_delivery_state_ref",
        "get_continuity_state_ref",
        "get_watchdog_state_ref",
        "get_provider_events_ref",
    }:
        assert "support file ref/path" in tool_description(tools_result, tool_name)


def assert_node_tool_teaching(tools_result: Any) -> None:
    for tool_name in NODE_CURRENT_LOOKUP_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Read-only:"), (tool_name, description)
        assert "session_key and task_id" in description, (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is True, tool_name
    for tool_name in NODE_MUTATING_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Mutating:"), (tool_name, description)
        assert "session_key and task_id" in description, (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is False, tool_name
    assert "closes the current dispatch turn" in tool_description(tools_result, "return_boundary")
    assert "not an operator-control surface" in tool_description(tools_result, "call_parent_tool")


__all__ = [
    "NODE_CURRENT_LOOKUP_TOOLS",
    "NODE_MUTATING_TOOLS",
    "PHASE4B_OPERATOR_MUTATING_TOOLS",
    "PHASE4B_OPERATOR_READ_ONLY_TOOLS",
    "assert_node_tool_teaching",
    "assert_phase4b_operator_tool_teaching",
]
