from __future__ import annotations

from pathlib import Path

from autoclaw.interfaces.mcp.bindings import load_current_node_tool_context
from autoclaw.persistence import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitStateModel,
    NodeSessionModel,
    PolicyRevisionModel,
    TaskEventModel,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import prepare_runtime_db
from tests.integration.mcp.node_dispatch_support import (
    load_node_tool_binding,
    revoke_same_dispatch_node_session,
    seed_live_node_mcp_dispatch,
)
from tests.integration.mcp.node_server.inventory_support import node_mcp_app
from tests.integration.mcp.support import (
    bootstrap_runtime_task,
    call_tool_result,
    call_tool_structured,
    mcp_client_session,
    node_tool_arguments,
    runtime_api_context,
    tool_failure,
)


def _command_run_start_payload() -> dict[str, object]:
    return {
        "command": "pytest apps/api/tests/unit/runtime -q",
        "description": "Run focused runtime unit tests.",
        "workdir": "apps/api",
        "timeout_seconds": 900,
    }


async def test_allowed_command_run_start_persists_wait_and_event(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-command-run-start"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            await _allow_command_run(api.session_factory, task_id=task_id)
            context = await load_current_node_tool_context(task_id)
            binding = await load_node_tool_binding(api.session_factory, context=context)

            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                response = await call_tool_structured(
                    session,
                    "start_command_run",
                    node_tool_arguments(context, request=_command_run_start_payload()),
                )

            assert set(response) == {"run_id", "task_id", "state"}
            assert response["task_id"] == task_id
            assert response["state"] == "pending_start"
            await _assert_started_command_run_state(
                api.session_factory,
                task_id=task_id,
                run_id=str(response["run_id"]),
                dispatch_id=binding.dispatch_id,
                node_session_id=binding.node_session_id,
            )


async def test_disallowed_command_run_start_has_no_side_effects(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-command-run-denied"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            context = await load_current_node_tool_context(task_id)
            binding = await load_node_tool_binding(api.session_factory, context=context)

            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                result = await call_tool_result(
                    session,
                    "start_command_run",
                    node_tool_arguments(context, request=_command_run_start_payload()),
                )

            failure = tool_failure(result)
            assert failure == {
                "ok": False,
                "code": "capability_rejected",
                "summary": (
                    "current node policy does not allow controller-managed command_run "
                    "from this node"
                ),
                "retryable": False,
                "field_path": None,
                "suggested_next_step": (
                    "run_short_command_inline_or_record_checkpoint_or_close_boundary"
                ),
            }
            assert result.content[0].text == failure["summary"]
            await _assert_no_command_run_side_effects(
                api.session_factory,
                task_id=task_id,
                dispatch_id=binding.dispatch_id,
                node_session_id=binding.node_session_id,
            )


async def test_stale_command_run_start_uses_node_authority_without_side_effects(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-command-run-stale"
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            context = await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_id,
                task_root=task_root,
            )
            binding = await load_node_tool_binding(api.session_factory, context=context)
            await revoke_same_dispatch_node_session(
                api.session_factory,
                task_id=task_id,
                context=context,
                flow_status="running",
                control_state="live",
                control_state_reason="manual_revoke",
            )

            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                result = await call_tool_result(
                    session,
                    "start_command_run",
                    node_tool_arguments(context, request=_command_run_start_payload()),
                )

            failure = tool_failure(result)
            assert failure["code"] == "stale_dispatch"
            assert failure["summary"] == "stale node session key"
            assert failure["retryable"] is True
            await _assert_no_command_run_side_effects(
                api.session_factory,
                task_id=task_id,
                dispatch_id=binding.dispatch_id,
                node_session_id=binding.node_session_id,
                expected_session_status="revoked",
            )


async def _allow_command_run(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
) -> None:
    async with session_factory() as session:
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


async def _assert_started_command_run_state(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    run_id: str,
    dispatch_id: str,
    node_session_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        node_session = await session.get(NodeSessionModel, node_session_id)
        command_run = await session.get(CommandRunModel, run_id)
        assert flow is not None
        assert dispatch is not None
        assert node_session is not None
        assert command_run is not None
        wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
        events = list(
            await session.scalars(
                select(TaskEventModel)
                .where(
                    TaskEventModel.task_id == task_id,
                    TaskEventModel.event_type == "command_run_started",
                )
                .order_by(TaskEventModel.event_seq.asc())
            )
        )

        assert command_run.task_id == task_id
        assert command_run.command == _command_run_start_payload()["command"]
        assert command_run.description == _command_run_start_payload()["description"]
        assert command_run.workdir == "apps/api"
        assert command_run.timeout_seconds == 900
        assert command_run.state == "pending_start"
        assert command_run.requester_node_key == dispatch.node_key
        assert wait_state is not None
        assert wait_state.waiting_cause == "waiting_for_command_run"
        assert wait_state.command_run_id == run_id
        assert wait_state.created_by_dispatch_id == dispatch_id
        assert flow.status == "running"
        assert flow.current_open_dispatch_id is None
        assert dispatch.control_state == "fenced"
        assert dispatch.accepted_boundary is None
        assert dispatch.closed_by_boundary is None
        assert dispatch.closed_at is not None
        assert node_session.session_status == "fenced"
        assert node_session.closed_at is not None
        assert len(events) == 1
        event = events[0]
        assert event.event_source == "node"
        assert event.flow_revision_id == command_run.flow_revision_id
        assert event.dispatch_id == dispatch_id
        assert event.attempt_id == command_run.attempt_id
        assert event.node_key == command_run.requester_node_key
        assert event.payload == {
            "run_id": run_id,
            "command": _command_run_start_payload()["command"],
            "description": _command_run_start_payload()["description"],
            "workdir": "apps/api",
            "state": "pending_start",
            "timeout_seconds": 900,
        }


async def _assert_no_command_run_side_effects(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    dispatch_id: str,
    node_session_id: str,
    expected_session_status: str = "live",
) -> None:
    async with session_factory() as session:
        run_count = await session.scalar(
            select(func.count(CommandRunModel.run_id)).where(CommandRunModel.task_id == task_id)
        )
        wait_count = await session.scalar(
            select(func.count(FlowWaitStateModel.flow_id)).where(
                FlowWaitStateModel.task_id == task_id
            )
        )
        event_count = await session.scalar(
            select(func.count(TaskEventModel.event_id)).where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == "command_run_started",
            )
        )
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        node_session = await session.get(NodeSessionModel, node_session_id)
        assert flow is not None
        assert dispatch is not None
        assert node_session is not None
        assert run_count == 0
        assert wait_count == 0
        assert event_count == 0
        assert flow.current_open_dispatch_id == dispatch_id
        assert dispatch.control_state == "live"
        assert dispatch.closed_at is None
        assert node_session.session_status == expected_session_status
