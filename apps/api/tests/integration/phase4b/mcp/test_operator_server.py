from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from app.db import DispatchTurnModel, FlowModel
from autoclaw.openclaw.node_server import NODE_TOOL_NAMES, create_node_mcp_app
from autoclaw.openclaw.operator_server import create_operator_mcp_app, create_operator_mcp_server
from sqlalchemy import select
from tests.integration.phase3.routes.observability_support import (
    current_dispatch_history_entry,
)
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_dispatch_support import seed_live_node_mcp_dispatch
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
from tests.integration.phase4b.support_state_shapes import (
    assert_continuity_state_shape,
    assert_delivery_state_shape,
    assert_provider_event_shape,
    assert_watchdog_state_shape,
    load_json_payload,
    load_provider_event_payloads,
)

_SHARED_CURRENT_DEFINITION_TOOLS = {"search_definitions", "get_definition"}
_PHASE5A_OPERATOR_ONLY_TOOLS = {
    "list_definition_versions",
    "upload_definition",
    "start_task",
}
_NODE_ONLY_TOOLS = set(NODE_TOOL_NAMES)
_PHASE4B_OPERATOR_RUNTIME_SUPPORT_TOOLS = {
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


def _assert_timestamp_has_timezone(value: str) -> None:
    assert value.endswith("Z") or "+" in value or value.rfind("-") > value.find("T"), value
    normalized = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
    assert datetime.fromisoformat(normalized).tzinfo is not None


def _assert_query_schema(tool_schema: dict[str, object]) -> None:
    properties = cast(dict[str, object], tool_schema.get("properties", {}))
    assert "query" in properties
    assert "q" not in properties


def _assert_phase4b_operator_tool_inventory(tools_result: Any) -> None:
    names = set(tool_names(tools_result))
    assert _PHASE4B_OPERATOR_RUNTIME_SUPPORT_TOOLS <= names
    assert names.isdisjoint(_NODE_ONLY_TOOLS - _SHARED_CURRENT_DEFINITION_TOOLS)
    _assert_query_schema(tool_input_schema(tools_result, "list_runtime_tasks"))
    _assert_query_schema(tool_input_schema(tools_result, "get_operator_trace"))


async def test_phase4b_operator_mcp_uses_query_arguments_in_tool_schemas() -> None:
    app = create_operator_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1")
    ).streamable_http_app()

    async with mcp_client_session(app) as session:
        tools_result = await session.list_tools()
        _assert_phase4b_operator_tool_inventory(tools_result)


async def test_phase4b_operator_mcp_exposes_runtime_operator_and_support_subset(
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
            _assert_phase4b_operator_tool_inventory(tools_result)

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


async def test_phase4b_operator_mcp_support_state_refs_freeze_exact_field_sets(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.operator-mcp-support-state"
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
            app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            async with mcp_client_session(app) as session:
                (
                    trace,
                    delivery_ref,
                    continuity_ref,
                    watchdog_ref,
                    provider_events_ref,
                ) = await _load_support_state_refs(session, task_id=task_id)
                await wait_for_runtime_effects(task_id=task_id)

            dispatch_history_entry = current_dispatch_history_entry(trace)
            assert dispatch_history_entry["node_key"] == "root"
            _assert_support_state_ref_filenames(
                delivery_ref=delivery_ref,
                continuity_ref=continuity_ref,
                watchdog_ref=watchdog_ref,
                provider_events_ref=provider_events_ref,
            )
            await wait_for_runtime_effects(task_id=task_id)
            _assert_support_state_ref_payloads(
                delivery_ref=delivery_ref,
                continuity_ref=continuity_ref,
                watchdog_ref=watchdog_ref,
                provider_events_ref=provider_events_ref,
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
                transport_security=default_transport_security(host="127.0.0.1")
            )

            async with mcp_client_session(operator_app) as operator_session:
                operator_tools = set(tool_names(await operator_session.list_tools()))

            async with mcp_client_session(node_app) as node_session:
                node_tools = set(tool_names(await node_session.list_tools()))

    assert _PHASE4B_OPERATOR_RUNTIME_SUPPORT_TOOLS <= operator_tools
    assert node_tools == set(NODE_TOOL_NAMES)
    assert operator_tools & node_tools == _SHARED_CURRENT_DEFINITION_TOOLS
    assert node_tools.isdisjoint(_PHASE5A_OPERATOR_ONLY_TOOLS)


async def _load_support_state_refs(
    session: Any,
    *,
    task_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
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
    return trace, delivery_ref, continuity_ref, watchdog_ref, provider_events_ref


def _assert_support_state_ref_filenames(
    *,
    delivery_ref: dict[str, Any],
    continuity_ref: dict[str, Any],
    watchdog_ref: dict[str, Any],
    provider_events_ref: dict[str, Any],
) -> None:
    assert Path(str(delivery_ref["path"])).name == "delivery-state.json"
    assert Path(str(continuity_ref["path"])).name == "continuity-state.json"
    assert Path(str(watchdog_ref["path"])).name == "watchdog-state.json"
    assert Path(str(provider_events_ref["path"])).name == "provider-events.ndjson"


def _assert_support_state_ref_payloads(
    *,
    delivery_ref: dict[str, Any],
    continuity_ref: dict[str, Any],
    watchdog_ref: dict[str, Any],
    provider_events_ref: dict[str, Any],
) -> None:
    delivery_path = Path(str(delivery_ref["path"]))
    continuity_path = Path(str(continuity_ref["path"]))
    watchdog_path = Path(str(watchdog_ref["path"]))
    provider_events_path = Path(str(provider_events_ref["path"]))
    delivery_payload = load_json_payload(delivery_path)
    continuity_payload = load_json_payload(continuity_path)
    watchdog_payload = load_json_payload(watchdog_path)
    provider_events = load_provider_event_payloads(provider_events_path)

    assert_delivery_state_shape(
        delivery_payload,
        dispatch_id_from_path=delivery_path.parent.name,
    )
    assert_continuity_state_shape(
        continuity_payload,
        dispatch_id_from_path=continuity_path.parent.name,
    )
    assert_watchdog_state_shape(
        watchdog_payload,
        dispatch_id_from_path=watchdog_path.parent.name,
    )
    assert provider_events
    for event_payload in provider_events:
        assert_provider_event_shape(
            event_payload,
            dispatch_id_from_path=provider_events_path.parent.name,
        )


async def test_phase4b_operator_mcp_cancel_wakes_shared_runtime_lifecycle(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.operator-mcp-cancel"
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
