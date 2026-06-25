from __future__ import annotations

from pathlib import Path
from typing import Any

from autoclaw.interfaces.mcp.bindings import load_current_node_tool_context
from autoclaw.persistence import (
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitStateModel,
    NodeSessionModel,
    PendingHumanRequestModel,
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


def _review_request_payload() -> dict[str, Any]:
    return {
        "kind": "review",
        "title": "Review implementation patch",
        "summary": "The node needs a human review before continuing.",
        "items": [
            {
                "item_id": "review_choice",
                "prompt": "Should the node proceed with this patch?",
                "options": [
                    {"id": "approve", "title": "Approve"},
                    {"id": "revise", "title": "Revise"},
                ],
                "recommended_option": "approve",
            }
        ],
        "timeout": {"due_at": None, "default_behavior": None},
        "suggested_human_instruction": "Inspect the patch before answering.",
    }


async def test_allowed_human_request_open_persists_wait_and_event(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-human-request-open"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            await _allow_human_request_kind(api.session_factory, task_id=task_id, kind="review")
            context = await load_current_node_tool_context(task_id)
            binding = await load_node_tool_binding(api.session_factory, context=context)

            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                response = await call_tool_structured(
                    session,
                    "open_human_request",
                    node_tool_arguments(context, request=_review_request_payload()),
                )

            assert set(response) == {"request_id", "task_id", "status"}
            assert response["task_id"] == task_id
            assert response["status"] == "open"
            await _assert_open_human_request_state(
                api.session_factory,
                task_id=task_id,
                request_id=str(response["request_id"]),
                dispatch_id=binding.dispatch_id,
                node_session_id=binding.node_session_id,
            )


async def test_disallowed_human_request_open_has_no_side_effects(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-human-request-denied"
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
                    "open_human_request",
                    node_tool_arguments(context, request=_review_request_payload()),
                )

            failure = tool_failure(result)
            assert failure == {
                "ok": False,
                "code": "capability_rejected",
                "summary": (
                    "current node policy does not allow human_request.review from this node"
                ),
                "retryable": False,
                "field_path": None,
                "suggested_next_step": (
                    "choose_an_allowed_human_request_kind_or_record_checkpoint_or_close_boundary"
                ),
            }
            assert result.content[0].text == failure["summary"]
            await _assert_no_human_request_side_effects(
                api.session_factory,
                task_id=task_id,
                dispatch_id=binding.dispatch_id,
                node_session_id=binding.node_session_id,
            )


async def test_stale_human_request_open_uses_node_authority_without_side_effects(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.node-human-request-stale"
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
                    "open_human_request",
                    node_tool_arguments(context, request=_review_request_payload()),
                )

            failure = tool_failure(result)
            assert failure["code"] == "stale_dispatch"
            assert failure["summary"] == "stale node session key"
            assert failure["retryable"] is True
            await _assert_no_human_request_side_effects(
                api.session_factory,
                task_id=task_id,
                dispatch_id=binding.dispatch_id,
                node_session_id=binding.node_session_id,
                expected_session_status="revoked",
            )


async def _allow_human_request_kind(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    kind: str,
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
        capabilities = dict(content.get("capabilities") or {})
        capabilities["human_request"] = {"mode": "allow", "allowed_kinds": [kind]}
        capabilities.setdefault("command_run", "deny")
        content["capabilities"] = capabilities
        policy_revision.content_json = content
        await session.commit()


async def _assert_open_human_request_state(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    request_id: str,
    dispatch_id: str,
    node_session_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        node_session = await session.get(NodeSessionModel, node_session_id)
        pending_request = await session.get(PendingHumanRequestModel, request_id)
        assert flow is not None
        assert dispatch is not None
        assert node_session is not None
        assert pending_request is not None
        wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
        events = list(
            await session.scalars(
                select(TaskEventModel)
                .where(
                    TaskEventModel.task_id == task_id,
                    TaskEventModel.event_type == "human_request_opened",
                )
                .order_by(TaskEventModel.event_seq.asc())
            )
        )

        assert pending_request.task_id == task_id
        assert pending_request.kind == "review"
        assert pending_request.status == "open"
        assert pending_request.requester_node_key == dispatch.node_key
        assert pending_request.items_json[0]["item_id"] == "review_choice"
        assert pending_request.timeout_json == {"due_at": None, "default_behavior": None}
        assert wait_state is not None
        assert wait_state.waiting_cause == "waiting_for_human_request"
        assert wait_state.pending_human_request_id == request_id
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
        assert event.flow_revision_id == pending_request.flow_revision_id
        assert event.dispatch_id == dispatch_id
        assert event.attempt_id == pending_request.attempt_id
        assert event.node_key == pending_request.requester_node_key
        assert event.payload == {
            "request_id": request_id,
            "kind": "review",
            "status": "open",
        }


async def _assert_no_human_request_side_effects(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    dispatch_id: str,
    node_session_id: str,
    expected_session_status: str = "live",
) -> None:
    async with session_factory() as session:
        pending_count = await session.scalar(
            select(func.count(PendingHumanRequestModel.request_id)).where(
                PendingHumanRequestModel.task_id == task_id
            )
        )
        wait_count = await session.scalar(
            select(func.count(FlowWaitStateModel.flow_id)).where(
                FlowWaitStateModel.task_id == task_id
            )
        )
        event_count = await session.scalar(
            select(func.count(TaskEventModel.event_id)).where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == "human_request_opened",
            )
        )
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        node_session = await session.get(NodeSessionModel, node_session_id)
        assert flow is not None
        assert dispatch is not None
        assert node_session is not None
        assert pending_count == 0
        assert wait_count == 0
        assert event_count == 0
        assert flow.current_open_dispatch_id == dispatch_id
        assert dispatch.control_state == "live"
        assert dispatch.closed_at is None
        assert node_session.session_status == expected_session_status
