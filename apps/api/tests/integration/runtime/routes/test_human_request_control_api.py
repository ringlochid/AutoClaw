from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from autoclaw.persistence import (
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitStateModel,
    PendingHumanRequestModel,
    PolicyRevisionModel,
    TaskEventModel,
)
from autoclaw.runtime.contracts import HumanRequestOpenRequest
from autoclaw.runtime.human_request.service import open_human_request
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    SeededRouteTask,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

_CONTROL_API_ACTOR_REF = "control_api"


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


def _input_request_payload() -> dict[str, Any]:
    return {
        "kind": "input",
        "title": "Provide launch details",
        "summary": "The node needs structured launch inputs before continuing.",
        "items": [
            {
                "item_id": "launch_details",
                "prompt": "Provide the launch name and retry limit.",
                "input_payload_schema": {
                    "type": "object",
                    "required": ["name", "retry_limit"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "retry_limit": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": False,
                },
            }
        ],
        "timeout": {"due_at": None, "default_behavior": None},
        "suggested_human_instruction": "Fill in the structured launch input.",
    }


def _answer_payload(
    *, item_id: str = "review_choice", option_id: str = "approve"
) -> dict[str, Any]:
    return {
        "item_responses": [
            {
                "item_id": item_id,
                "selected_option": option_id,
                "freeform_answer": None,
                "extra_notes": "Looks good.",
                "response_payload": None,
            }
        ]
    }


def _structured_input_answer_payload(
    response_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "item_responses": [
            {
                "item_id": "launch_details",
                "selected_option": None,
                "freeform_answer": None,
                "extra_notes": "Use these launch values.",
                "response_payload": response_payload
                if response_payload is not None
                else {"name": "alpha", "retry_limit": 2},
            }
        ]
    }


async def test_control_human_requests_read_exposes_open_request_without_resolution(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_read",
            task_root_name="task-root",
        )
        request_id = await open_review_human_request(context, task)

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/human-requests",
            headers=context.operator_headers,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == task.task_id
        assert len(payload["items"]) == 1
        readback = payload["items"][0]
        assert readback["resolution"] is None
        assert readback["request"]["request_id"] == request_id
        assert readback["request"]["task_id"] == task.task_id
        assert readback["request"]["status"] == "open"
        assert readback["request"]["kind"] == "review"
        assert readback["request"]["requester_node"] == "root"
        assert readback["request"]["items"][0]["item_id"] == "review_choice"
        assert readback["request"]["items"][0]["options"][0]["id"] == "approve"


async def test_control_human_request_resolve_persists_answer_and_clears_wait(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_resolve",
            task_root_name="task-root",
        )
        request_id = await open_review_human_request(context, task)

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )

        assert response.status_code == 200
        resolution = response.json()["resolution"]
        assert resolution["request_id"] == request_id
        assert resolution["task_id"] == task.task_id
        assert resolution["resolution_kind"] == "answered"
        assert resolution["resolved_by_actor_ref"] == _CONTROL_API_ACTOR_REF
        assert resolution["resolved_at"] is not None
        assert resolution["item_responses"] == _answer_payload()["item_responses"]
        await assert_answered_resolution_state(context, task, request_id)

        readback = await context.client.get(
            f"/control/tasks/{task.task_id}/human-requests",
            headers=context.operator_headers,
        )
        readback_json = readback.json()["items"][0]
        assert readback.status_code == 200
        assert readback_json["request"]["status"] == "resolved"
        assert readback_json["resolution"] == resolution


async def test_control_human_request_resolve_accepts_structured_input_payload(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_structured_input",
            task_root_name="task-root",
        )
        request_id = await open_input_human_request(context, task)
        answer_payload = _structured_input_answer_payload()

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=answer_payload,
        )

        assert response.status_code == 200
        resolution = response.json()["resolution"]
        assert resolution["request_id"] == request_id
        assert resolution["resolution_kind"] == "answered"
        assert resolution["item_responses"] == answer_payload["item_responses"]
        await assert_answered_resolution_state(
            context,
            task,
            request_id,
            expected_item_responses=answer_payload["item_responses"],
        )

        readback = await context.client.get(
            f"/control/tasks/{task.task_id}/human-requests",
            headers=context.operator_headers,
        )
        readback_json = readback.json()["items"][0]
        assert readback.status_code == 200
        assert readback_json["request"]["kind"] == "input"
        assert readback_json["request"]["status"] == "resolved"
        assert readback_json["resolution"] == resolution


async def test_control_human_request_resolve_rejects_schema_invalid_input_without_side_effects(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_invalid_input",
            task_root_name="task-root",
        )
        request_id = await open_input_human_request(context, task)

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_structured_input_answer_payload({"name": 17, "retry_limit": -1}),
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_request_shape"
        await assert_open_request_unchanged(context, task, request_id, wait_owner_id=request_id)


async def test_control_human_request_resolve_rejects_missing_request_without_side_effects(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_missing",
            task_root_name="task-root",
        )
        request_id = await open_review_human_request(context, task)

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/human-request.missing/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "illegal_state"
        await assert_open_request_unchanged(context, task, request_id, wait_owner_id=request_id)


async def test_control_human_request_resolve_rejects_non_current_request_without_side_effects(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_superseded",
            task_root_name="task-root",
        )
        request_id = await open_review_human_request(context, task)
        replacement_request_id = await replace_active_wait_owner(context, request_id)

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "illegal_state"
        await assert_open_request_unchanged(
            context,
            task,
            request_id,
            wait_owner_id=replacement_request_id,
        )


async def test_control_human_request_resolve_rejects_terminal_request_without_duplicate_event(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_terminal",
            task_root_name="task-root",
        )
        request_id = await open_review_human_request(context, task)
        resolved = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )
        assert resolved.status_code == 200

        duplicate = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(option_id="revise"),
        )

        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["code"] == "illegal_state"
        async with context.session_factory() as session:
            pending_request = await session.get(PendingHumanRequestModel, request_id)
            resolved_event_count = await resolved_event_count_for_task(session, task.task_id)
            assert pending_request is not None
            assert pending_request.status == "resolved"
            assert pending_request.item_responses_json == _answer_payload()["item_responses"]
            assert resolved_event_count == 1


async def test_control_human_request_resolve_rejects_unknown_item_or_option_without_side_effects(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_invalid_answer",
            task_root_name="task-root",
        )
        request_id = await open_review_human_request(context, task)

        unknown_item = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(item_id="missing_item"),
        )
        unknown_option = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(option_id="missing_option"),
        )

        assert unknown_item.status_code == 400
        assert unknown_item.json()["detail"]["code"] == "invalid_request_shape"
        assert unknown_option.status_code == 400
        assert unknown_option.json()["detail"]["code"] == "invalid_request_shape"
        await assert_open_request_unchanged(context, task, request_id, wait_owner_id=request_id)


async def test_control_human_requests_require_operator_auth_and_existing_task(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_auth",
            task_root_name="task-root",
        )

        unauthorized = await context.client.get(f"/control/tasks/{task.task_id}/human-requests")
        missing_read = await context.client.get(
            "/control/tasks/task_missing/human-requests",
            headers=context.operator_headers,
        )
        missing_resolve = await context.client.post(
            "/control/tasks/task_missing/human-requests/human-request.missing/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )

        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "illegal_caller"
        assert missing_read.status_code == 404
        assert missing_read.json()["detail"]["code"] == "missing_resource"
        assert missing_resolve.status_code == 404
        assert missing_resolve.json()["detail"]["code"] == "missing_resource"


async def open_review_human_request(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
) -> str:
    return await open_route_human_request(
        context,
        task,
        kind="review",
        request_payload=_review_request_payload(),
    )


async def open_input_human_request(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
) -> str:
    return await open_route_human_request(
        context,
        task,
        kind="input",
        request_payload=_input_request_payload(),
    )


async def open_route_human_request(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    kind: str,
    request_payload: dict[str, Any],
) -> str:
    await allow_human_request_kind(context.session_factory, task_id=task.task_id, kind=kind)
    async with context.session_factory() as session:
        state = await current_runtime_state(session, task.task_id)
        dispatch = await session.get(DispatchTurnModel, task.current_open_dispatch_id)
        assert dispatch is not None
        response = await open_human_request(
            session,
            task_id=task.task_id,
            request=HumanRequestOpenRequest.model_validate(request_payload),
            state=state,
            dispatch=dispatch,
        )
        await session.commit()
        return response.request_id


async def allow_human_request_kind(
    session_factory: async_sessionmaker[AsyncSession],
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
        raw_capabilities = content.get("capabilities")
        capabilities = dict(raw_capabilities) if isinstance(raw_capabilities, dict) else {}
        capabilities["human_request"] = {"mode": "allow", "allowed_kinds": [kind]}
        capabilities.setdefault("command_run", "deny")
        content["capabilities"] = capabilities
        policy_revision.content_json = content
        await session.commit()


async def replace_active_wait_owner(
    context: RuntimeRouteContext,
    request_id: str,
) -> str:
    async with context.session_factory() as session:
        pending_request = await session.get(PendingHumanRequestModel, request_id)
        assert pending_request is not None
        wait_state = await session.get(FlowWaitStateModel, pending_request.flow_id)
        assert wait_state is not None
        replacement_request_id = f"{request_id}.replacement"
        session.add(
            PendingHumanRequestModel(
                request_id=replacement_request_id,
                task_id=pending_request.task_id,
                flow_id=pending_request.flow_id,
                flow_revision_id=pending_request.flow_revision_id,
                flow_node_id=pending_request.flow_node_id,
                assignment_id=pending_request.assignment_id,
                attempt_id=pending_request.attempt_id,
                dispatch_id=pending_request.dispatch_id,
                requester_node_key=pending_request.requester_node_key,
                kind=pending_request.kind,
                title="Replacement review request",
                summary=pending_request.summary,
                items_json=deepcopy(pending_request.items_json),
                timeout_json=deepcopy(pending_request.timeout_json),
                suggested_human_instruction=pending_request.suggested_human_instruction,
                status="open",
                opened_at=pending_request.opened_at,
                updated_at=pending_request.updated_at,
            )
        )
        wait_state.pending_human_request_id = replacement_request_id
        await session.commit()
        return replacement_request_id


async def assert_answered_resolution_state(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    request_id: str,
    *,
    expected_item_responses: list[dict[str, Any]] | None = None,
) -> None:
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
        pending_request = await session.get(PendingHumanRequestModel, request_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)
        resolved_events = await resolved_events_for_task(session, task.task_id)
        expected_responses = (
            expected_item_responses
            if expected_item_responses is not None
            else _answer_payload()["item_responses"]
        )

        assert flow is not None
        assert pending_request is not None
        assert wait_state is None
        assert pending_request.status == "resolved"
        assert pending_request.resolution_kind == "answered"
        assert pending_request.item_responses_json == expected_responses
        assert pending_request.resolved_at is not None
        assert pending_request.resolved_by_actor_ref == _CONTROL_API_ACTOR_REF
        assert len(resolved_events) == 1
        event = resolved_events[0]
        assert event.event_source == "control_api"
        assert event.actor_ref == _CONTROL_API_ACTOR_REF
        assert event.flow_revision_id == pending_request.flow_revision_id
        assert event.dispatch_id == pending_request.dispatch_id
        assert event.attempt_id == pending_request.attempt_id
        assert event.node_key == pending_request.requester_node_key
        assert event.payload == {
            "request_id": request_id,
            "status": "resolved",
            "resolution_kind": "answered",
            "resolved_by_actor_ref": _CONTROL_API_ACTOR_REF,
        }


async def assert_open_request_unchanged(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    request_id: str,
    *,
    wait_owner_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
        pending_request = await session.get(PendingHumanRequestModel, request_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)
        resolved_event_count = await resolved_event_count_for_task(session, task.task_id)

        assert flow is not None
        assert pending_request is not None
        assert wait_state is not None
        assert pending_request.status == "open"
        assert pending_request.resolution_kind is None
        assert pending_request.item_responses_json is None
        assert pending_request.resolved_at is None
        assert pending_request.resolved_by_actor_ref is None
        assert wait_state.waiting_cause == "waiting_for_human_request"
        assert wait_state.pending_human_request_id == wait_owner_id
        assert resolved_event_count == 0


async def resolved_events_for_task(
    session: AsyncSession,
    task_id: str,
) -> list[TaskEventModel]:
    return list(
        await session.scalars(
            select(TaskEventModel)
            .where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == "human_request_resolved",
            )
            .order_by(TaskEventModel.event_seq.asc())
        )
    )


async def resolved_event_count_for_task(session: AsyncSession, task_id: str) -> int:
    return int(
        await session.scalar(
            select(func.count(TaskEventModel.event_id)).where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == "human_request_resolved",
            )
        )
        or 0
    )
