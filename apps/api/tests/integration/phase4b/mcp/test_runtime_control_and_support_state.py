from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.interfaces.mcp.operator.server import create_operator_mcp_app
from autoclaw.runtime.post_commit import drive_runtime_once
from tests.integration.phase3.routes.observability_support import (
    current_dispatch_history_entry,
)
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.support import (
    assert_tool_result_matches_output_schema,
    bootstrap_runtime_task,
    call_tool_result,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    phase3_runtime_api,
    tool_failure,
)
from tests.integration.phase4b.support_state_shapes import (
    assert_continuity_state_shape,
    assert_delivery_state_shape,
    assert_provider_event_shape,
    assert_watchdog_state_shape,
    load_json_payload,
    load_provider_event_payloads,
)


def _assert_timestamp_has_timezone(value: str) -> None:
    assert value.endswith("Z") or "+" in value or value.rfind("-") > value.find("T"), value
    normalized = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
    assert datetime.fromisoformat(normalized).tzinfo is not None


async def test_phase4b_operator_mcp_continue_task_matches_pause_resume_runtime_control(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase4b.operator-mcp-continue"
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
                tools = await session.list_tools()
                runtime = await call_tool_structured(
                    session,
                    "get_runtime_task",
                    {"task_id": task_id},
                )
                await _assert_running_continue_rejected(
                    session,
                    tools=tools,
                    runtime=runtime,
                    task_id=task_id,
                )
                paused = await _pause_task(session, runtime=runtime, task_id=task_id)
                await _assert_paused_continue_waits_for_inactivity(
                    session,
                    tools=tools,
                    paused=paused,
                    task_id=task_id,
                )
                openclaw_gateway_test_server.set_default_method_payload(
                    "agent.wait",
                    agent_wait_fixture(status="ok"),
                )
                resumed = await _continue_until_resumed(
                    session,
                    tools=tools,
                    paused=paused,
                    task_id=task_id,
                )
                _assert_timestamp_has_timezone(str(resumed["updated_at"]))
                cancelled = await call_tool_structured(
                    session,
                    "cancel_task",
                    {
                        "task_id": task_id,
                        "expected_active_flow_revision_id": cast(
                            str,
                            resumed["active_flow_revision_id"],
                        ),
                    },
                )
                assert cancelled["status"] == "cancelled"
                await drive_runtime_once(task_id=task_id)


async def _assert_running_continue_rejected(
    session: Any,
    *,
    tools: Any,
    runtime: dict[str, Any],
    task_id: str,
) -> None:
    running_continue = await call_tool_result(
        session,
        "continue_task",
        {
            "task_id": task_id,
            "expected_active_flow_revision_id": cast(
                str,
                runtime["active_flow_revision_id"],
            ),
        },
    )
    running_failure = tool_failure(running_continue)
    assert_tool_result_matches_output_schema(tools, "continue_task", running_continue)
    assert running_failure["code"] == "illegal_state"
    assert running_failure["summary"] == "continue is legal only for paused flows"
    assert running_failure["suggested_next_step"] == (
        "Reread the current runtime status before retrying. Ordinary child handoff, "
        "parent wake, and retry progression now happen automatically once the prior "
        "dispatch is proven inactive; use continue only to resume a paused flow."
    )


async def _pause_task(
    session: Any,
    *,
    runtime: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
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
    return paused


async def _assert_paused_continue_waits_for_inactivity(
    session: Any,
    *,
    tools: Any,
    paused: dict[str, Any],
    task_id: str,
) -> None:
    paused_continue = await call_tool_result(
        session,
        "continue_task",
        {
            "task_id": task_id,
            "expected_active_flow_revision_id": cast(
                str,
                paused["flow"]["active_flow_revision_id"],
            ),
        },
    )
    paused_failure = tool_failure(paused_continue)
    assert_tool_result_matches_output_schema(tools, "continue_task", paused_continue)
    assert paused_failure["summary"] == (
        "current dispatch is still awaiting inactivity proof after abort"
    )


async def _continue_until_resumed(
    session: Any,
    *,
    tools: Any,
    paused: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
    resumed: dict[str, Any] | None = None
    for _ in range(20):
        await drive_runtime_once(task_id=task_id)
        continue_result = await call_tool_result(
            session,
            "continue_task",
            {
                "task_id": task_id,
                "expected_active_flow_revision_id": cast(
                    str,
                    paused["flow"]["active_flow_revision_id"],
                ),
            },
        )
        if continue_result.isError is False:
            resumed = cast(dict[str, Any], continue_result.structuredContent)
            break
        continue_failure = tool_failure(continue_result)
        assert_tool_result_matches_output_schema(tools, "continue_task", continue_result)
        assert continue_failure["summary"] == (
            "current dispatch is still awaiting inactivity proof after abort"
        )
    assert resumed is not None
    assert resumed["status"] == "running"
    return resumed


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
                (
                    trace,
                    delivery_ref,
                    continuity_ref,
                    watchdog_ref,
                    provider_events_ref,
                ) = await _load_support_state_refs(session, task_id=task_id)
                await drive_runtime_once(task_id=task_id)

            dispatch_history_entry = current_dispatch_history_entry(trace)
            assert dispatch_history_entry["node_key"] == "root"
            _assert_support_state_ref_filenames(
                delivery_ref=delivery_ref,
                continuity_ref=continuity_ref,
                watchdog_ref=watchdog_ref,
                provider_events_ref=provider_events_ref,
            )
            await drive_runtime_once(task_id=task_id)
            _assert_support_state_ref_payloads(
                delivery_ref=delivery_ref,
                continuity_ref=continuity_ref,
                watchdog_ref=watchdog_ref,
                provider_events_ref=provider_events_ref,
            )


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
