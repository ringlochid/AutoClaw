from __future__ import annotations

import asyncio
from datetime import datetime
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
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.human_request.service import open_human_request
from autoclaw.runtime.post_commit import drive_runtime_until
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    SeededRouteTask,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

_CONTROL_API_ACTOR_REF = "control_api"
_CONTROLLER_ACTOR_REF = "controller"


def _review_request_payload(
    *,
    due_at: str | None = None,
    default_behavior: str | None = None,
) -> dict[str, Any]:
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
        "timeout": {"due_at": due_at, "default_behavior": default_behavior},
        "suggested_human_instruction": "Inspect the patch before answering.",
    }


def _answer_payload() -> dict[str, Any]:
    return {
        "item_responses": [
            {
                "item_id": "review_choice",
                "selected_option": "approve",
                "freeform_answer": None,
                "extra_notes": "Looks good.",
                "response_payload": None,
            }
        ]
    }


async def test_resolved_human_request_continues_task_and_backfills_real_events(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_continue",
            task_root_name="task-root",
        )
        request_dispatch_id = task.current_open_dispatch_id
        request_id = await open_review_human_request(context, task)

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )

        assert response.status_code == 200
        continued_dispatch_id, prompt_path = await assert_human_request_terminal_continues_task(
            context,
            task,
            request_dispatch_id=request_dispatch_id,
        )
        prompt_text = prompt_path.read_text(encoding="utf-8")
        assert continued_dispatch_id != request_dispatch_id
        assert "## Human Request Continuation Context" in prompt_text
        assert f"- request_id: {request_id}" in prompt_text
        assert "- resolution_kind: answered" in prompt_text
        assert "- resolved_by_actor_ref: control_api" in prompt_text
        assert "selected_option: approve" in prompt_text
        assert "extra_notes: Looks good." in prompt_text

        events_response = await context.client.get(
            f"/control/tasks/{task.task_id}/events",
            headers=context.operator_headers,
        )
        assert events_response.status_code == 200
        human_request_events = [
            event
            for event in events_response.json()["items"]
            if event["event_type"] in {"human_request_opened", "human_request_resolved"}
        ]
        assert [event["event_type"] for event in human_request_events] == [
            "human_request_opened",
            "human_request_resolved",
        ]
        assert human_request_events[0]["event_source"] == "node"
        assert human_request_events[0]["payload"] == {
            "request_id": request_id,
            "kind": "review",
            "status": "open",
        }
        assert human_request_events[1]["event_source"] == "control_api"
        assert human_request_events[1]["actor_ref"] == _CONTROL_API_ACTOR_REF
        assert human_request_events[1]["payload"] == {
            "request_id": request_id,
            "status": "resolved",
            "resolution_kind": "answered",
            "resolved_by_actor_ref": _CONTROL_API_ACTOR_REF,
        }


async def test_timed_out_human_request_continues_task_and_surfaces_timeout_context(
    tmp_path: Path,
) -> None:
    timeout_due_at = datetime.fromisoformat("2026-06-01T00:00:00+00:00")
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_timeout",
            task_root_name="timeout-task-root",
        )
        request_dispatch_id = task.current_open_dispatch_id
        request_id = await open_review_human_request(
            context,
            task,
            request_payload=_review_request_payload(
                due_at="2026-06-01T00:00:00+00:00",
                default_behavior="proceed with the recommended review option",
            ),
        )

        continued_dispatch_id, prompt_path = await assert_human_request_terminal_continues_task(
            context,
            task,
            request_dispatch_id=request_dispatch_id,
        )
        prompt_text = prompt_path.read_text(encoding="utf-8")
        assert continued_dispatch_id != request_dispatch_id
        assert f"- request_id: {request_id}" in prompt_text
        assert "- resolution_kind: timed_out" in prompt_text
        assert "- timeout_default_behavior: proceed with the recommended review option" in (
            prompt_text
        )
        assert "- resolved_by_actor_ref: controller" in prompt_text

        async with context.session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
            pending_request = await session.get(PendingHumanRequestModel, request_id)
            wait_state = await current_wait_state(session, task.task_id)
            timeout_events = await human_request_events(
                session, task.task_id, "human_request_timed_out"
            )
            assert flow is not None
            assert pending_request is not None
            assert pending_request.status == "timed_out"
            assert pending_request.resolution_kind == "timed_out"
            assert pending_request.resolved_by_actor_ref == _CONTROLLER_ACTOR_REF
            assert pending_request.resolved_at is not None
            assert coerce_datetime_to_utc(pending_request.resolved_at) > timeout_due_at
            assert coerce_datetime_to_utc(flow.updated_at) > timeout_due_at
            assert wait_state is None
            assert len(timeout_events) == 1
            timeout_event = timeout_events[0]
            assert timeout_event.event_source == "controller"
            assert timeout_event.actor_ref == _CONTROLLER_ACTOR_REF
            assert coerce_datetime_to_utc(timeout_event.occurred_at) > timeout_due_at
            assert timeout_event.payload == {
                "request_id": request_id,
                "status": "timed_out",
                "resolution_kind": "timed_out",
                "resolved_by_actor_ref": _CONTROLLER_ACTOR_REF,
            }


async def test_cancel_task_closes_open_human_request_as_cancelled(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_human_request_cancelled",
            task_root_name="cancelled-task-root",
        )
        request_id = await open_review_human_request(context, task)

        cancel_response = await context.client.post(
            f"/runtime/tasks/{task.task_id}/cancel",
            headers=context.operator_headers,
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"
        async with context.session_factory() as session:
            pending_request = await session.get(PendingHumanRequestModel, request_id)
            wait_state = await current_wait_state(session, task.task_id)
            cancelled_events = await human_request_events(
                session,
                task.task_id,
                "human_request_cancelled",
            )
            assert pending_request is not None
            assert pending_request.status == "cancelled"
            assert pending_request.resolution_kind == "cancelled"
            assert pending_request.resolved_by_actor_ref == _CONTROL_API_ACTOR_REF
            assert wait_state is None
            assert len(cancelled_events) == 1
            cancelled_event = cancelled_events[0]
            assert cancelled_event.event_source == "control_api"
            assert cancelled_event.actor_ref == _CONTROL_API_ACTOR_REF
            assert cancelled_event.payload == {
                "request_id": request_id,
                "status": "cancelled",
                "resolution_kind": "cancelled",
                "resolved_by_actor_ref": _CONTROL_API_ACTOR_REF,
            }

        stale_response = await context.client.post(
            f"/control/tasks/{task.task_id}/human-requests/{request_id}/resolve",
            headers=context.operator_headers,
            json=_answer_payload(),
        )
        assert stale_response.status_code == 409
        assert stale_response.json()["detail"]["code"] == "illegal_state"


async def open_review_human_request(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    request_payload: dict[str, Any] | None = None,
) -> str:
    await allow_human_request_kind(context.session_factory, task_id=task.task_id, kind="review")
    async with context.session_factory() as session:
        state = await current_runtime_state(session, task.task_id)
        dispatch = await session.get(DispatchTurnModel, task.current_open_dispatch_id)
        assert dispatch is not None
        response = await open_human_request(
            session,
            task_id=task.task_id,
            request=HumanRequestOpenRequest.model_validate(
                request_payload if request_payload is not None else _review_request_payload()
            ),
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


async def assert_human_request_terminal_continues_task(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    request_dispatch_id: str,
) -> tuple[str, Path]:
    continued_dispatch_id: str | None = None
    prompt_path: Path | None = None

    async def task_continued() -> bool:
        nonlocal continued_dispatch_id, prompt_path
        async with context.session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
            assert flow is not None
            dispatch_id = flow.current_open_dispatch_id
            if dispatch_id is None or dispatch_id == request_dispatch_id:
                return False
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert dispatch is not None
            if dispatch.previous_dispatch_id != request_dispatch_id:
                return False
            if dispatch.accepted_boundary is not None or dispatch.prompt_path is None:
                return False
            candidate_prompt_path = Path(dispatch.prompt_path)
            if not await asyncio.to_thread(candidate_prompt_path.is_file):
                return False
            continued_dispatch_id = dispatch.dispatch_id
            prompt_path = candidate_prompt_path
            return True

    await drive_runtime_until(task_continued, task_id=task.task_id, max_cycles=60)
    assert continued_dispatch_id is not None
    assert prompt_path is not None
    return continued_dispatch_id, prompt_path


async def current_wait_state(session: AsyncSession, task_id: str) -> FlowWaitStateModel | None:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None:
        return None
    return await session.get(FlowWaitStateModel, flow.flow_id)


async def human_request_events(
    session: AsyncSession,
    task_id: str,
    event_type: str,
) -> list[TaskEventModel]:
    return list(
        await session.scalars(
            select(TaskEventModel)
            .where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == event_type,
            )
            .order_by(TaskEventModel.event_seq.asc())
        )
    )
