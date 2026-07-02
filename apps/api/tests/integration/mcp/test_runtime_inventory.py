from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from autoclaw.interfaces.mcp.node.server import NODE_TOOL_NAMES, create_node_mcp_app
from autoclaw.interfaces.mcp.operator.server import (
    create_operator_mcp_app,
    create_operator_mcp_server,
)
from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.runtime.post_commit import drive_runtime_until
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.mcp.node_dispatch_support import seed_live_node_mcp_dispatch
from tests.integration.mcp.support import (
    bootstrap_runtime_task,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    runtime_api_context,
    tool_description,
    tool_input_schema,
    tool_names,
)
from tests.integration.mcp.teaching_support import (
    assert_operator_tool_teaching,
)

_SHARED_CURRENT_DEFINITION_TOOLS = {"search_definitions", "get_definition"}
_OPERATOR_DEFINITION_EXTENSION_TOOLS = {
    "list_definition_versions",
    "upload_definition",
    "start_task",
}
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
_NODE_ONLY_TOOLS = set(NODE_TOOL_NAMES)
_OPERATOR_RUNTIME_SUPPORT_TOOLS = {
    "list_runtime_tasks",
    "get_runtime_task",
    "get_operator_snapshot",
    "get_operator_trace",
    "get_human_requests",
    "resolve_human_request",
    "get_command_runs",
    "get_command_run",
    "get_command_run_log",
    "cancel_command_run",
    "pause_task",
    "continue_task",
    "cancel_task",
    "get_delivery_state_ref",
    "get_continuity_state_ref",
    "get_watchdog_state_ref",
    "get_provider_events_ref",
}


def _assert_timestamp_has_timezone(value: str) -> None:
    assert value.endswith("Z") or "+" in value or value.rfind("-") > value.find("T"), value
    normalized = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
    assert datetime.fromisoformat(normalized).tzinfo is not None


def _assert_query_schema(tool_schema: dict[str, object]) -> None:
    properties = cast(dict[str, object], tool_schema.get("properties", {}))
    assert "query" in properties
    assert "q" not in properties


def _assert_operator_tool_inventory(tools_result: Any) -> None:
    names = set(tool_names(tools_result))
    assert _OPERATOR_RUNTIME_SUPPORT_TOOLS <= names
    assert _OPERATOR_DEFINITION_EXTENSION_TOOLS <= names
    assert names.isdisjoint(_REMOVED_OPERATOR_DRAFT_MUTATION_TOOLS)
    assert (names & _NODE_ONLY_TOOLS) == _SHARED_CURRENT_DEFINITION_TOOLS
    _assert_query_schema(tool_input_schema(tools_result, "list_runtime_tasks"))
    _assert_query_schema(tool_input_schema(tools_result, "get_operator_trace"))
    assert_operator_tool_teaching(tools_result)
    _assert_operator_runtime_teaching_contract(tools_result)


def _assert_operator_runtime_teaching_contract(tools_result: Any) -> None:
    list_runtime_tasks_description = tool_description(tools_result, "list_runtime_tasks")
    get_runtime_task_description = tool_description(tools_result, "get_runtime_task")
    get_operator_snapshot_description = tool_description(tools_result, "get_operator_snapshot")
    get_operator_trace_description = tool_description(tools_result, "get_operator_trace")
    continue_task_description = tool_description(tools_result, "continue_task")

    assert "Inspect before mutating runtime state." in list_runtime_tasks_description
    assert (
        "Use this first for status checks and before pause_task, continue_task, or cancel_task."
        in get_runtime_task_description
    )
    assert "Observe before mutating runtime state." in get_operator_snapshot_description
    assert "Observe before mutating runtime state." in get_operator_trace_description
    assert "Resume a paused task" in continue_task_description
    assert "Pause-resume only." in continue_task_description
    assert "Not the ordinary path for yielded child handoff" in continue_task_description
    assert "reopen the current task runtime" not in continue_task_description


async def test_operator_mcp_uses_query_arguments_in_tool_schemas() -> None:
    app = create_operator_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1")
    ).streamable_http_app()

    async with mcp_client_session(app) as session:
        tools_result = await session.list_tools()
        _assert_operator_tool_inventory(tools_result)


async def test_operator_mcp_exposes_runtime_operator_and_support_subset(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.operator-mcp"
    _config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    app = create_operator_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))

    with openclaw_gateway_test_server.configured_env():
        async with mcp_client_session(app) as session:
            tools_result = await session.list_tools()
            _assert_operator_tool_inventory(tools_result)

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

            snapshot = await call_tool_structured(
                session,
                "get_operator_snapshot",
                {"task_id": task_id},
            )
            assert snapshot["flow"]["task_id"] == task_id
            assert snapshot["current_paths"]

            delivery_ref = await call_tool_structured(
                session, "get_delivery_state_ref", {"task_id": task_id}
            )
            assert Path(str(delivery_ref["path"])).name == "delivery-state.json"

            paused = await call_tool_structured(
                session,
                "pause_task",
                {
                    "task_id": task_id,
                    "expected_active_flow_revision_id": cast(
                        str,
                        runtime["active_flow_revision_id"],
                    ),
                },
            )
            assert paused["flow"]["status"] == "paused"


async def test_operator_and_node_mcp_sessions_keep_live_inventories_separate() -> None:
    operator_app = create_operator_mcp_app(
        transport_security=default_transport_security(host="127.0.0.1")
    )
    node_app = create_node_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))

    async with mcp_client_session(operator_app) as operator_session:
        operator_tools = set(tool_names(await operator_session.list_tools()))

    async with mcp_client_session(node_app) as node_session:
        node_tools = set(tool_names(await node_session.list_tools()))

    assert _OPERATOR_RUNTIME_SUPPORT_TOOLS <= operator_tools
    assert node_tools == set(NODE_TOOL_NAMES)
    assert operator_tools & node_tools == _SHARED_CURRENT_DEFINITION_TOOLS
    assert node_tools.isdisjoint(_OPERATOR_DEFINITION_EXTENSION_TOOLS)


async def test_operator_mcp_cancel_wakes_shared_runtime_lifecycle(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.operator-mcp-cancel"
    config_path, task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_id,
                task_root=task_root,
                bootstrap_runtime=False,
            )
            app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                dispatch_id = flow.current_open_dispatch_id
                active_flow_revision_id = flow.active_flow_revision_id

            openclaw_gateway_test_server.clear_requests()

            async with mcp_client_session(app) as session:
                cancelled = await call_tool_structured(
                    session,
                    "cancel_task",
                    {
                        "task_id": task_id,
                        "expected_active_flow_revision_id": active_flow_revision_id,
                    },
                )
                assert cancelled["status"] == "cancelled"

            await drive_runtime_until(
                lambda: _cancelled_runtime_visible(
                    api.session_factory,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                ),
                task_id=task_id,
                max_cycles=20,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.status == "cancelled"
                assert flow.current_open_dispatch_id in {None, dispatch_id}
                assert dispatch.control_state in {"abort_requested", "fenced"}
                if dispatch.control_state == "fenced":
                    assert dispatch.fenced_at is not None
                else:
                    assert dispatch.abort_requested_at is not None

            assert any(
                request.method == "sessions.abort"
                for request in openclaw_gateway_test_server.requests
            )


async def _cancelled_runtime_visible(
    session_factory: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        return (
            flow is not None
            and dispatch is not None
            and flow.status == "cancelled"
            and dispatch.control_state in {"abort_requested", "fenced"}
        )
