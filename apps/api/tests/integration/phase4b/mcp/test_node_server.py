from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from app.runtime.effects import wait_for_runtime_effects
from autoclaw.openclaw.bindings import NodeMcpBinding, load_current_node_mcp_binding
from autoclaw.openclaw.node_server import (
    NODE_TOOL_NAMES,
    create_node_mcp_app,
    create_node_mcp_server,
)
from starlette.applications import Starlette
from tests.integration.phase3.runtime_support import (
    OPERATOR_HEADERS,
    prepare_runtime_db,
    runtime_read_json,
    write_workspace_file,
)
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.support import (
    assert_same_dispatch_node_mcp_binding_state,
    bootstrap_runtime_task,
    call_node_assign_child,
    call_node_boundary,
    call_tool_result,
    call_tool_structured,
    continue_to_current_dispatch,
    default_transport_security,
    dispatch_support_path,
    mcp_client_session,
    phase3_runtime_api,
    revoke_same_dispatch_node_mcp_binding,
    seed_live_node_mcp_dispatch,
    tool_input_schema,
    tool_names,
    wait_for_support_state_json,
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
_PHASE5A_ONLY_TOOLS = {
    "search_definitions",
    "get_definition",
    "list_definition_versions",
    "upload_definition",
    "start_task",
}


async def test_phase4b_node_mcp_call_parent_tool_keeps_top_level_revision_argument() -> None:
    app = create_node_mcp_server(
        binding=NodeMcpBinding(
            task_id="task.phase4b.schema-only",
            dispatch_id="dispatch.phase4b.schema-only",
            node_session_id="node-session.dispatch.phase4b.schema-only",
            callback_session_key="callback-session-key",
        ),
        transport_security=default_transport_security(host="127.0.0.1"),
    ).streamable_http_app()

    async with mcp_client_session(app) as session:
        tools_result = await session.list_tools()
        schema = tool_input_schema(tools_result, "call_parent_tool")
        properties = schema.get("properties", {})

        assert "expected_structural_revision_id" in properties
        assert "task_id" not in properties
        assert "session_key" not in properties
        assert "callback_session_key" not in properties


def _node_mcp_app(binding: NodeMcpBinding) -> Starlette:
    return create_node_mcp_app(
        binding,
        transport_security=default_transport_security(host="127.0.0.1"),
    )


def _assert_dispatch_bound_node_tools(tools_result: Any) -> None:
    names = set(tool_names(tools_result))
    assert set(NODE_TOOL_NAMES) == names
    assert names.isdisjoint(_OPERATOR_ONLY_TOOLS)
    assert names.isdisjoint(_PHASE5A_ONLY_TOOLS)
    for tool_name in NODE_TOOL_NAMES:
        schema = tool_input_schema(tools_result, tool_name)
        properties = set(schema.get("properties", {}))
        assert "task_id" not in properties
        assert "session_key" not in properties
        assert "callback_session_key" not in properties
        if tool_name == "call_parent_tool":
            assert "expected_structural_revision_id" in properties


async def _assign_child_and_yield_current_node(
    task_id: str,
    *,
    child_node_key: str,
    summary: str,
    instruction: str,
    active_flow_revision_id: str,
    assert_tool_contract: bool = False,
) -> NodeMcpBinding:
    binding = await load_current_node_mcp_binding(task_id)
    async with mcp_client_session(_node_mcp_app(binding)) as session:
        if assert_tool_contract:
            _assert_dispatch_bound_node_tools(await session.list_tools())
        assigned = await call_node_assign_child(
            session,
            child_node_key=child_node_key,
            summary=summary,
            instruction=instruction,
            active_flow_revision_id=active_flow_revision_id,
        )
        assert assigned["tool_name"] == "assign_child"
        assert assigned["target_node_key"] == child_node_key
        yielded = await call_node_boundary(session, "yield")
        assert yielded["accepted_boundary"] == "yield"
    return binding


async def _complete_worker_dispatch(
    *,
    task_id: str,
    task_root: Path,
    worker_binding: NodeMcpBinding,
    worker_runtime: dict[str, Any],
) -> dict[str, Any]:
    patch_file = write_workspace_file(
        task_root,
        "workspace/findings_report.md",
        "investigation findings",
    )
    delivery_state_path = dispatch_support_path(
        task_root,
        worker_binding.dispatch_id,
        "delivery-state.json",
    )
    initial_delivery_state = json.loads(delivery_state_path.read_text(encoding="utf-8"))
    assert initial_delivery_state["last_controller_terminal_at"] is None

    async with mcp_client_session(_node_mcp_app(worker_binding)) as worker_session:
        checkpoint = await call_tool_structured(
            worker_session,
            "record_checkpoint",
            {
                "checkpoint": {
                    "checkpoint_kind": "terminal",
                    "outcome": "green",
                    "handoff": {
                        "summary": "worker completed the investigation step",
                        "next_step": "parent should schedule the next child",
                    },
                    "produced_artifacts": [
                        {"slot": "findings_report", "path": str(patch_file)},
                    ],
                }
            },
        )
        assert checkpoint["attempt_id"] == worker_runtime["active_attempt_id"]
        assert checkpoint["checkpoint_id"]
        checkpoint_delivery_state = await wait_for_support_state_json(
            delivery_state_path,
            task_id=task_id,
            predicate=lambda payload: payload["last_controller_terminal_at"] is not None,
        )
        assert checkpoint_delivery_state["dispatch_id"] == worker_binding.dispatch_id
        assert checkpoint_delivery_state["attempt_id"] == worker_runtime["active_attempt_id"]
        assert checkpoint_delivery_state["controller_observation_state"] == "live"
        closed = await call_node_boundary(worker_session, "green")
        assert closed["accepted_boundary"] == "green"
    return checkpoint


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
            runtime = await runtime_read_json(api.client, task_id)
            await _assign_child_and_yield_current_node(
                task_id,
                child_node_key="implementation_subtree",
                summary="phase4b operator/node separation",
                instruction="open the parent subtree",
                active_flow_revision_id=cast(str, runtime["active_flow_revision_id"]),
                assert_tool_contract=True,
            )
            continued = await continue_to_current_dispatch(config_path, task_id)
            await _assign_child_and_yield_current_node(
                task_id,
                child_node_key="investigate_issue",
                summary="phase4b worker investigation handoff",
                instruction="produce the first investigation artifact",
                active_flow_revision_id=cast(str, continued["active_flow_revision_id"]),
            )
            worker_runtime = await continue_to_current_dispatch(config_path, task_id)
            worker_binding = await load_current_node_mcp_binding(task_id)
            checkpoint = await _complete_worker_dispatch(
                task_id=task_id,
                task_root=task_root,
                worker_binding=worker_binding,
                worker_runtime=worker_runtime,
            )

            await wait_for_runtime_effects(task_id=task_id)
            trace = await api.client.get(
                f"/operator/tasks/{task_id}/trace",
                headers=OPERATOR_HEADERS,
                params={"scope": "whole"},
            )
            assert trace.status_code == 200
            trace_json = trace.json()
            assert (
                trace_json["checkpoint_history"][0]["checkpoint_id"] == checkpoint["checkpoint_id"]
            )
            assert trace_json["boundary_history"][0]["boundary"] == "green"

            await continue_to_current_dispatch(config_path, task_id)
            next_binding = await load_current_node_mcp_binding(task_id)
            assert next_binding.dispatch_id != worker_binding.dispatch_id

            async with mcp_client_session(_node_mcp_app(worker_binding)) as stale_worker_session:
                stale_result = await call_tool_result(
                    stale_worker_session,
                    "return_boundary",
                    {"boundary": "yield"},
                )
                assert stale_result.isError is True


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
            binding = await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_id,
                task_root=task_root,
            )
            await revoke_same_dispatch_node_mcp_binding(
                api.session_factory,
                task_id=task_id,
                binding=binding,
                flow_status=flow_status,
                control_state=control_state,
                control_state_reason=control_state_reason,
            )
            await assert_same_dispatch_node_mcp_binding_state(
                api.session_factory,
                task_id=task_id,
                binding=binding,
                flow_status=flow_status,
                control_state=control_state,
            )
            async with mcp_client_session(_node_mcp_app(binding)) as session:
                stale_result = await call_tool_result(
                    session,
                    "return_boundary",
                    {"boundary": "yield"},
                )
                assert stale_result.isError is True
