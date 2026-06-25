from __future__ import annotations

from typing import Any

from tests.integration.mcp.support import tool_description, tool_read_only_hint

OPERATOR_READ_ONLY_TOOLS = {
    "list_runtime_tasks",
    "get_runtime_task",
    "get_operator_snapshot",
    "get_operator_trace",
    "get_delivery_state_ref",
    "get_continuity_state_ref",
    "get_watchdog_state_ref",
    "get_provider_events_ref",
}
OPERATOR_MUTATING_TOOLS = {"pause_task", "continue_task", "cancel_task"}
NODE_CURRENT_LOOKUP_TOOLS = {"search_definitions", "get_definition"}
NODE_MUTATING_TOOLS = {
    "record_checkpoint",
    "return_boundary",
    "open_human_request",
    "start_command_run",
    "assign_child",
    "add_child",
    "update_child",
    "remove_child",
    "release_green",
    "release_blocked",
}


def assert_operator_tool_teaching(tools_result: Any) -> None:
    for tool_name in OPERATOR_READ_ONLY_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Read-only:"), (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is True, tool_name
    assert "active flow revision" in tool_description(tools_result, "get_runtime_task")
    assert "current_paths" in tool_description(tools_result, "get_operator_snapshot")
    assert "chronology" in tool_description(tools_result, "get_operator_trace")
    for tool_name in OPERATOR_MUTATING_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Mutating:"), (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is False, tool_name
        assert "fresh expected_active_flow_revision_id" in description, (tool_name, description)
    assert "Do not use for status checks." in tool_description(tools_result, "continue_task")
    assert "Use only after inspecting current runtime state." in tool_description(
        tools_result, "continue_task"
    )
    for tool_name in {
        "get_delivery_state_ref",
        "get_continuity_state_ref",
        "get_watchdog_state_ref",
        "get_provider_events_ref",
    }:
        description = tool_description(tools_result, tool_name)
        assert "support-only reread surface" in description.lower()
        assert "support file ref/path" in description
        assert "controller/runtime truth wins" in description.lower()


def assert_node_tool_teaching(tools_result: Any) -> None:
    for tool_name in NODE_CURRENT_LOOKUP_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Read-only:"), (tool_name, description)
        assert "session_key and task_id" in description, (tool_name, description)
        assert "live structural-edit lane" in description, (tool_name, description)
        assert "Not for broad browsing or provenance." in description, (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is True, tool_name
    for tool_name in NODE_MUTATING_TOOLS:
        description = tool_description(tools_result, tool_name)
        assert description.startswith("Mutating:"), (tool_name, description)
        assert "session_key and task_id" in description, (tool_name, description)
        assert tool_read_only_hint(tools_result, tool_name) is False, tool_name
    assert "before a terminal boundary" in tool_description(tools_result, "record_checkpoint")
    assert "`yield` is non-terminal workflow progress" in tool_description(
        tools_result, "return_boundary"
    )
    assert (
        "close the current dispatch turn"
        in tool_description(tools_result, "return_boundary").lower()
    )
    open_human_request_description = tool_description(tools_result, "open_human_request")
    assert "waiting_for_human_request" in open_human_request_description
    assert "not a workflow boundary" in open_human_request_description
    assert "fail before pending request" in open_human_request_description
    start_command_run_description = tool_description(tools_result, "start_command_run")
    assert "waiting_for_command_run" in start_command_run_description
    assert "not a workflow boundary" in start_command_run_description
    assert "fail before command-run" in start_command_run_description
    for tool_name in {
        "assign_child",
        "add_child",
        "update_child",
        "remove_child",
        "release_green",
        "release_blocked",
    }:
        assert "current dispatch allows legal parent/root mutation" in tool_description(
            tools_result, tool_name
        )
    assert "not an operator-control surface" in tool_description(tools_result, "assign_child")
    assert "Reread the regenerated manifest" in tool_description(tools_result, "add_child")
    assert "Root-only." in tool_description(tools_result, "release_blocked")


__all__ = [
    "NODE_CURRENT_LOOKUP_TOOLS",
    "NODE_MUTATING_TOOLS",
    "OPERATOR_MUTATING_TOOLS",
    "OPERATOR_READ_ONLY_TOOLS",
    "assert_node_tool_teaching",
    "assert_operator_tool_teaching",
]
