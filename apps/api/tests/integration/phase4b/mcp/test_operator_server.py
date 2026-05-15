from __future__ import annotations

from pathlib import Path

from app.db import DispatchTurnModel, FlowModel
from autoclaw.openclaw.bindings import load_current_node_mcp_binding
from autoclaw.openclaw.node_server import NODE_TOOL_NAMES, create_node_mcp_app
from autoclaw.openclaw.operator_server import (
    OPERATOR_TOOL_NAMES,
    create_operator_mcp_app,
    create_operator_mcp_server,
)
from sqlalchemy import select
from tests.integration.phase3.routes.observability_support import (
    assert_continuity_payload,
    assert_delivery_payload,
    assert_provider_event_shape,
    assert_provider_event_text_fields,
    assert_watchdog_payload,
    load_provider_event_payloads,
)
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    phase3_runtime_api,
    tool_input_schema,
    tool_names,
    wait_for_runtime_effects,
)

_PHASE5A_ONLY_TOOLS = {
    "search_definitions",
    "get_definition",
    "list_definition_versions",
    "upload_definition",
    "start_task",
}
_NODE_ONLY_TOOLS = set(NODE_TOOL_NAMES)


async def test_phase4b_operator_mcp_uses_query_arguments_in_tool_schemas() -> None:
    app = create_operator_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1")
    ).streamable_http_app()

    async with mcp_client_session(app) as session:
        tools_result = await session.list_tools()
        list_schema = tool_input_schema(tools_result, "list_runtime_tasks")
        trace_schema = tool_input_schema(tools_result, "get_operator_trace")

        assert "query" in list_schema.get("properties", {})
        assert "q" not in list_schema.get("properties", {})
        assert "query" in trace_schema.get("properties", {})
        assert "q" not in trace_schema.get("properties", {})


async def test_phase4b_operator_mcp_exposes_only_runtime_operator_and_support_subset(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.operator-mcp"
    _config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    app = create_operator_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))

    with openclaw_gateway_test_server.configured_env():
        async with mcp_client_session(app) as session:
            tools_result = await session.list_tools()
            names = set(tool_names(tools_result))
            list_schema = tool_input_schema(tools_result, "list_runtime_tasks")
            trace_schema = tool_input_schema(tools_result, "get_operator_trace")

            assert set(OPERATOR_TOOL_NAMES) <= names
            assert names.isdisjoint(_NODE_ONLY_TOOLS)
            assert names.isdisjoint(_PHASE5A_ONLY_TOOLS)
            assert "query" in list_schema.get("properties", {})
            assert "q" not in list_schema.get("properties", {})
            assert "query" in trace_schema.get("properties", {})
            assert "q" not in trace_schema.get("properties", {})

            runtime = await call_tool_structured(
                session,
                "get_runtime_task",
                {"task_id": task_id},
            )
            assert runtime["task_id"] == task_id

            snapshot = await call_tool_structured(
                session,
                "get_operator_snapshot",
                {"task_id": task_id},
            )
            assert snapshot["flow"]["task_id"] == task_id
            assert snapshot["current_paths"]

            delivery_ref = await call_tool_structured(
                session,
                "get_delivery_state_ref",
                {"task_id": task_id},
            )
            assert Path(str(delivery_ref["path"])).name == "delivery-state.json"

            paused = await call_tool_structured(
                session,
                "pause_task",
                {
                    "task_id": task_id,
                    "expected_active_flow_revision_id": runtime["active_flow_revision_id"],
                },
            )
            assert paused["flow"]["status"] == "paused"


async def test_phase4b_operator_mcp_support_state_refs_freeze_exact_field_sets(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.operator-mcp-support-state"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path):
            app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            async with mcp_client_session(app) as session:
                trace = await call_tool_structured(
                    session,
                    "get_operator_trace",
                    {"task_id": task_id, "scope": "current"},
                )
                delivery_ref = await call_tool_structured(
                    session,
                    "get_delivery_state_ref",
                    {"task_id": task_id},
                )
                continuity_ref = await call_tool_structured(
                    session,
                    "get_continuity_state_ref",
                    {"task_id": task_id},
                )
                watchdog_ref = await call_tool_structured(
                    session,
                    "get_watchdog_state_ref",
                    {"task_id": task_id},
                )
                provider_events_ref = await call_tool_structured(
                    session,
                    "get_provider_events_ref",
                    {"task_id": task_id},
                )

            assert_delivery_payload(
                delivery_ref,
                trace,
                expected_node_key="root",
                expected_previous_dispatch_id=None,
            )
            assert_continuity_payload(
                continuity_ref,
                trace,
                expected_node_key="root",
            )
            assert_watchdog_payload(
                watchdog_ref,
                trace,
                expected_node_key="root",
                expected_previous_dispatch_id=None,
            )

            provider_events_path = Path(str(provider_events_ref["path"]))
            provider_event_payloads = load_provider_event_payloads(provider_events_path)
            assert len(provider_event_payloads) == 1
            provider_event_payload = provider_event_payloads[0]
            assert_provider_event_shape(
                provider_event_payload,
                dispatch_id_from_path=provider_events_path.parent.name,
            )
            assert_provider_event_text_fields(
                provider_event_payload,
                dispatch_id=provider_events_path.parent.name,
                attempt_id=str(trace["dispatch_history"][0]["attempt_id"]),
                node_key="root",
            )


async def test_phase4b_operator_and_node_mcp_sessions_keep_live_inventories_separate(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.live-mcp-inventories"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path):
            operator_app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            node_app = create_node_mcp_app(
                await load_current_node_mcp_binding(task_id),
                transport_security=default_transport_security(host="127.0.0.1"),
            )

            async with mcp_client_session(operator_app) as operator_session:
                operator_tools = set(tool_names(await operator_session.list_tools()))

            async with mcp_client_session(node_app) as node_session:
                node_tools = set(tool_names(await node_session.list_tools()))

    assert operator_tools == set(OPERATOR_TOOL_NAMES)
    assert node_tools == set(NODE_TOOL_NAMES)
    assert operator_tools.isdisjoint(node_tools)
    assert operator_tools.isdisjoint(_PHASE5A_ONLY_TOOLS)
    assert node_tools.isdisjoint(_PHASE5A_ONLY_TOOLS)


async def test_phase4b_operator_mcp_cancel_wakes_shared_runtime_lifecycle(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.operator-mcp-cancel"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
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

            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=5.0)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.status == "cancelled"
                assert flow.current_open_dispatch_id is None
                assert dispatch.control_state == "fenced"
                assert dispatch.fenced_at is not None

            assert any(
                request.method == "sessions.abort"
                for request in openclaw_gateway_test_server.requests
            )
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
