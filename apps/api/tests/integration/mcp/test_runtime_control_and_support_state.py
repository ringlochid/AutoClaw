from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.interfaces.mcp.operator.server import create_operator_mcp_app
from autoclaw.persistence import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    PendingHumanRequestModel,
    PolicyRevisionModel,
)
from autoclaw.runtime.command_run.service import start_command_run
from autoclaw.runtime.contracts import CommandRunStartRequest, HumanRequestOpenRequest
from autoclaw.runtime.human_request.service import open_human_request
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.operator_trace_readback import current_dispatch_history_entry
from tests.integration.mcp.support import (
    assert_tool_result_matches_output_schema,
    bootstrap_runtime_task,
    call_tool_result,
    call_tool_structured,
    default_transport_security,
    mcp_client_session,
    runtime_api_context,
    tool_failure,
)
from tests.integration.mcp.support_state_readback import (
    assert_support_state_ref_filenames,
    assert_support_state_ref_payloads,
    load_support_state_refs,
)


def _assert_timestamp_has_timezone(value: str) -> None:
    assert value.endswith("Z") or "+" in value or value.rfind("-") > value.find("T"), value
    normalized = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
    assert datetime.fromisoformat(normalized).tzinfo is not None


async def test_operator_mcp_continue_task_matches_pause_resume_runtime_control(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.operator-mcp-continue"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path):
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

    async def continue_resumed() -> bool:
        nonlocal resumed
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
        assert_tool_result_matches_output_schema(tools, "continue_task", continue_result)
        if continue_result.isError is False:
            resumed = cast(dict[str, Any], continue_result.structuredContent)
            return True
        continue_failure = tool_failure(continue_result)
        assert continue_failure["summary"] == (
            "current dispatch is still awaiting inactivity proof after abort"
        )
        return False

    await drive_runtime_until(
        continue_resumed,
        task_id=task_id,
        max_cycles=20,
    )
    assert resumed is not None
    assert resumed["status"] == "running"
    return resumed


async def test_operator_mcp_support_state_refs_freeze_exact_field_sets(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.operator-mcp-support-state"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path):
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
                ) = await load_support_state_refs(session, task_id=task_id)
                await drive_runtime_once(task_id=task_id)

            dispatch_history_entry = current_dispatch_history_entry(trace)
            assert dispatch_history_entry["node_key"] == "root"
            assert_support_state_ref_filenames(
                delivery_ref=delivery_ref,
                continuity_ref=continuity_ref,
                watchdog_ref=watchdog_ref,
                provider_events_ref=provider_events_ref,
            )
            await drive_runtime_once(task_id=task_id)
            assert_support_state_ref_payloads(
                delivery_ref=delivery_ref,
                continuity_ref=continuity_ref,
                watchdog_ref=watchdog_ref,
                provider_events_ref=provider_events_ref,
            )


async def test_operator_mcp_resolves_human_requests_and_controls_command_runs(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.operator-mcp-human-request-command-run"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )

            await _allow_human_request_kind(api, task_id=task_id, kind="review")
            request_id = await _open_review_human_request(api, task_id=task_id)
            await _assert_operator_mcp_resolves_review_request(
                app,
                task_id=task_id,
                request_id=request_id,
            )
            await drive_runtime_until(
                lambda: _current_open_dispatch_restored(api, task_id=task_id),
                task_id=task_id,
                max_cycles=20,
            )
            await _allow_command_run(api, task_id=task_id)
            command_run_id = await _start_focused_command_run(api, task_id=task_id)
            command_run_app = create_operator_mcp_app(
                transport_security=default_transport_security(host="127.0.0.1")
            )
            await _assert_operator_mcp_cancels_command_run(
                command_run_app,
                task_id=task_id,
                run_id=command_run_id,
            )
            await _assert_operator_mcp_control_persisted(
                api,
                request_id=request_id,
                run_id=command_run_id,
            )


async def _open_review_human_request(api: Any, *, task_id: str) -> str:
    async with api.session_factory() as session:
        state = await current_runtime_state(session, task_id)
        dispatch = await session.get(DispatchTurnModel, state.flow.current_open_dispatch_id)
        assert dispatch is not None
        opened = await open_human_request(
            session,
            task_id=task_id,
            request=HumanRequestOpenRequest.model_validate(
                {
                    "kind": "review",
                    "title": "Review the staged change",
                    "summary": "The node needs a human review before continuing.",
                    "items": [
                        {
                            "item_id": "review_choice",
                            "prompt": "Should the node continue?",
                            "options": [
                                {"id": "approve", "title": "Approve"},
                                {"id": "revise", "title": "Revise"},
                            ],
                            "recommended_option": "approve",
                        }
                    ],
                    "suggested_human_instruction": "Inspect the staged change first.",
                }
            ),
            state=state,
            dispatch=dispatch,
        )
        await session.commit()
        return opened.request_id


async def _assert_operator_mcp_resolves_review_request(
    app: Any,
    *,
    task_id: str,
    request_id: str,
) -> None:
    async with mcp_client_session(app) as mcp_session:
        human_requests = await call_tool_structured(
            mcp_session,
            "get_human_requests",
            {"task_id": task_id},
        )
        assert human_requests["items"][0]["request"]["request_id"] == request_id
        assert human_requests["items"][0]["resolution"] is None

        resolved = await call_tool_structured(
            mcp_session,
            "resolve_human_request",
            {
                "task_id": task_id,
                "request_id": request_id,
                "item_responses": [
                    {
                        "item_id": "review_choice",
                        "selected_option": "approve",
                        "freeform_answer": None,
                        "extra_notes": "Proceed.",
                        "response_payload": None,
                    }
                ],
            },
        )
        assert resolved["resolution"]["resolution_kind"] == "answered"

        resolved_requests = await call_tool_structured(
            mcp_session,
            "get_human_requests",
            {"task_id": task_id},
        )
        assert (
            resolved_requests["items"][0]["resolution"]["resolved_by_actor_ref"] == "operator_mcp"
        )


async def _start_focused_command_run(api: Any, *, task_id: str) -> str:
    async with api.session_factory() as session:
        state = await current_runtime_state(session, task_id)
        dispatch = await session.get(DispatchTurnModel, state.flow.current_open_dispatch_id)
        assert dispatch is not None
        command_run = await start_command_run(
            session,
            task_id=task_id,
            request=CommandRunStartRequest.model_validate(
                {
                    "command": "pytest apps/api/tests/unit/runtime -q",
                    "description": "Run focused runtime unit tests.",
                    "workdir": "apps/api",
                    "timeout_seconds": 900,
                }
            ),
            state=state,
            dispatch=dispatch,
        )
        await session.commit()
        return command_run.run_id


async def _assert_operator_mcp_cancels_command_run(
    app: Any,
    *,
    task_id: str,
    run_id: str,
) -> None:
    async with mcp_client_session(app) as mcp_session:
        command_runs = await call_tool_structured(
            mcp_session,
            "get_command_runs",
            {"task_id": task_id},
        )
        assert command_runs["items"][0]["run_id"] == run_id

        command_run_detail = await call_tool_structured(
            mcp_session,
            "get_command_run",
            {"task_id": task_id, "run_id": run_id},
        )
        assert command_run_detail["state"] == "pending_start"
        assert command_run_detail["terminal_result"] is None

        cancelled = await call_tool_structured(
            mcp_session,
            "cancel_command_run",
            {"task_id": task_id, "run_id": run_id},
        )
        assert cancelled["run"]["state"] == "cancellation_requested"

        cancelled_detail = await call_tool_structured(
            mcp_session,
            "get_command_run",
            {"task_id": task_id, "run_id": run_id},
        )
        assert cancelled_detail["state"] == "cancellation_requested"


async def _assert_operator_mcp_control_persisted(
    api: Any,
    *,
    request_id: str,
    run_id: str,
) -> None:
    async with api.session_factory() as session:
        pending_request = await session.get(PendingHumanRequestModel, request_id)
        persisted_command_run = await session.get(CommandRunModel, run_id)
        assert pending_request is not None
        assert pending_request.resolved_by_actor_ref == "operator_mcp"
        assert pending_request.resolved_by_surface == "operator_mcp"
        assert persisted_command_run is not None
        assert persisted_command_run.cancellation_requested_by_actor_ref == "operator_mcp"


async def _allow_human_request_kind(
    api: Any,
    *,
    task_id: str,
    kind: str,
) -> None:
    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        node = await session.scalar(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                FlowNodeModel.node_key == flow.current_node_key,
            )
        )
        assert node is not None
        assert node.policy_key is not None
        assert node.policy_revision_no is not None
        policy_revision = await session.scalar(
            select(PolicyRevisionModel).where(
                PolicyRevisionModel.policy_key == node.policy_key,
                PolicyRevisionModel.revision_no == node.policy_revision_no,
            )
        )
        assert policy_revision is not None
        content = dict(policy_revision.content_json)
        raw_capabilities = content.get("capabilities")
        capabilities = dict(raw_capabilities) if isinstance(raw_capabilities, dict) else {}
        capabilities["human_request"] = {"mode": "allow", "allowed_kinds": [kind]}
        capabilities.setdefault("command_run", "deny")
        content["capabilities"] = capabilities
        policy_revision.content_json = content
        await session.commit()


async def _allow_command_run(
    api: Any,
    *,
    task_id: str,
) -> None:
    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        node = await session.scalar(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                FlowNodeModel.node_key == flow.current_node_key,
            )
        )
        assert node is not None
        assert node.policy_key is not None
        assert node.policy_revision_no is not None
        policy_revision = await session.scalar(
            select(PolicyRevisionModel).where(
                PolicyRevisionModel.policy_key == node.policy_key,
                PolicyRevisionModel.revision_no == node.policy_revision_no,
            )
        )
        assert policy_revision is not None
        content = dict(policy_revision.content_json)
        raw_capabilities = content.get("capabilities")
        capabilities = dict(raw_capabilities) if isinstance(raw_capabilities, dict) else {}
        capabilities.setdefault("human_request", {"mode": "deny", "allowed_kinds": []})
        capabilities["command_run"] = "allow"
        content["capabilities"] = capabilities
        policy_revision.content_json = content
        await session.commit()


async def _current_open_dispatch_restored(
    api: Any,
    *,
    task_id: str,
) -> bool:
    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        return flow is not None and flow.current_open_dispatch_id is not None
