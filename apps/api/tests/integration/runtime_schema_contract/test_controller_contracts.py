from __future__ import annotations

from datetime import UTC, datetime

import pytest
from autoclaw.runtime.contracts import (
    COMMAND_RUN_TERMINAL_EVENT_TYPES,
    BoundaryStateTransition,
    CapabilityRejectionError,
    CommandRunRecord,
    CommandRunStartResponse,
    CommandRunState,
    CommandRunTerminalResult,
    EffectiveCapabilitySet,
    HumanRequestOpenRequest,
    HumanRequestResolution,
    HumanRequestStatus,
    HumanRequestTimeout,
    OperationFailureCode,
    PendingHumanRequest,
    ProviderLaunchFailure,
    ProviderResolution,
    TaskEventListResponse,
    TaskEventRecord,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from pydantic import ValidationError


def test_provider_resolution_contracts_keep_logical_provider_names() -> None:
    resolution = ProviderResolution.model_validate(
        {
            "requested_provider": "codex",
            "resolved_provider": "openclaw",
        }
    )
    failure = ProviderLaunchFailure.model_validate(
        {
            "requested_provider": "codex",
            "attempted_provider": "openclaw",
            "stage": "connect",
            "message": "default provider failed before dispatch acceptance",
        }
    )

    assert resolution.model_dump(mode="json") == {
        "requested_provider": "codex",
        "resolved_provider": "openclaw",
    }
    assert failure.code == "provider_launch_failed"
    assert failure.stage == "connect"


def test_capability_contracts_expose_denied_defaults_and_structured_rejection() -> None:
    capability_set = EffectiveCapabilitySet.model_validate(
        {
            "execution_scope": "dispatch",
            "human_request": {"review": "allow"},
        }
    )
    rejection = CapabilityRejectionError(
        capability="human_request.review",
        message="current worker policy does not allow review requests from this node",
        next_legal_action="record_checkpoint_or_choose_another_allowed_boundary",
    )

    assert capability_set.human_request.direction == "deny"
    assert capability_set.human_request.review == "allow"
    assert capability_set.command_run == "deny"
    assert rejection.code == OperationFailureCode.CAPABILITY_REJECTED


def _human_review_request_payload(*, recommended_option: str = "approve") -> dict[str, object]:
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
                "recommended_option": recommended_option,
            }
        ],
        "timeout": {"due_at": None, "default_behavior": None},
        "suggested_human_instruction": "Inspect the patch before answering.",
    }


def test_human_request_contracts_accept_pending_item_and_resolution_shapes() -> None:
    now = datetime(2026, 6, 24, 17, 0, tzinfo=UTC)
    open_request = HumanRequestOpenRequest.model_validate(_human_review_request_payload())
    pending_request = PendingHumanRequest(
        request_id="human-request.1",
        task_id="task.1",
        title=open_request.title,
        summary=open_request.summary,
        kind=open_request.kind,
        requester_node="implement_slice",
        items=open_request.items,
        timeout=HumanRequestTimeout(),
        suggested_human_instruction=open_request.suggested_human_instruction,
        opened_at=now,
        status=HumanRequestStatus.OPEN,
    )
    resolution = HumanRequestResolution.model_validate(
        {
            "request_id": "human-request.1",
            "task_id": "task.1",
            "resolution_kind": "answered",
            "item_responses": [
                {
                    "item_id": "review_choice",
                    "selected_option": "approve",
                    "freeform_answer": None,
                    "extra_notes": "Looks good.",
                    "response_payload": None,
                }
            ],
            "resolved_at": now,
            "resolved_by_actor_ref": "operator.alice",
        }
    )

    assert pending_request.status == "open"
    assert resolution.resolution_kind == "answered"


def test_human_request_contracts_reject_unknown_recommended_option() -> None:
    with pytest.raises(ValidationError, match="recommended_option"):
        HumanRequestOpenRequest.model_validate(
            _human_review_request_payload(recommended_option="missing")
        )


def test_human_request_contracts_require_schema_for_input_items() -> None:
    with pytest.raises(ValidationError, match="input_payload_schema"):
        HumanRequestOpenRequest.model_validate(
            {
                "kind": "input",
                "title": "Need missing field",
                "summary": "The node needs structured input.",
                "items": [{"item_id": "field", "prompt": "Provide the field."}],
                "suggested_human_instruction": "Answer the structured input.",
            }
        )


def test_command_run_contracts_validate_terminal_state_shape() -> None:
    now = datetime(2026, 6, 24, 17, 0, tzinfo=UTC)
    response = CommandRunStartResponse(
        run_id="command-run.1",
        task_id="task.1",
        state=CommandRunState.RUNNING,
    )
    record = CommandRunRecord(
        run_id=response.run_id,
        task_id=response.task_id,
        dispatch_id="dispatch.1",
        command="pytest apps/api/tests/unit/definition_schemas -q",
        description="Run focused definition schema tests.",
        state=CommandRunState.SUCCEEDED,
        created_at=now,
        started_at=now,
        ended_at=now,
        terminal_result=CommandRunTerminalResult(
            summary="all focused definition schema tests passed",
            exit_code=0,
            signal=None,
            log_ref=None,
        ),
    )

    assert record.state == "succeeded"
    assert record.terminal_result is not None
    assert record.terminal_result.exit_code == 0

    with pytest.raises(ValidationError, match="terminal_result"):
        CommandRunRecord(
            run_id="command-run.2",
            task_id="task.1",
            dispatch_id="dispatch.1",
            command="pytest",
            description="Run tests.",
            state=CommandRunState.SUCCEEDED,
            created_at=now,
            ended_at=now,
        )

    with pytest.raises(ValidationError, match="terminal_result"):
        CommandRunRecord(
            run_id="command-run.3",
            task_id="task.1",
            dispatch_id="dispatch.1",
            command="pytest",
            description="Run tests.",
            state=CommandRunState.RUNNING,
            created_at=now,
            terminal_result=CommandRunTerminalResult(summary="still running"),
        )


def test_runtime_contracts_expose_waiting_and_event_vocabulary() -> None:
    assert [cause.value for cause in WaitingCause] == [
        "paused_by_operator",
        "waiting_for_human_request",
        "waiting_for_command_run",
        "waiting_for_internal_fencing",
        "waiting_for_adapter_reconnect",
    ]
    assert [transition.value for transition in BoundaryStateTransition] == [
        "operator_resume",
        "human_request_terminal",
        "command_run_terminal",
        "adapter_reconnected",
        "internal_fencing_cleared",
    ]
    assert [event_type.value for event_type in TaskEventType] == [
        "task_started",
        "dispatch_opened",
        "provider_resolution_recorded",
        "checkpoint_recorded",
        "boundary_accepted",
        "child_assignment_staged",
        "child_assignment_committed",
        "provider_event_normalized",
        "human_request_opened",
        "human_request_resolved",
        "human_request_timed_out",
        "human_request_cancelled",
        "command_run_started",
        "command_run_progressed",
        "command_run_cancel_requested",
        "command_run_succeeded",
        "command_run_failed",
        "command_run_timed_out",
        "command_run_cancelled",
        "task_paused",
        "task_resumed",
        "task_cancelled",
    ]
    assert COMMAND_RUN_TERMINAL_EVENT_TYPES == {
        CommandRunState.SUCCEEDED: TaskEventType.COMMAND_RUN_SUCCEEDED,
        CommandRunState.FAILED: TaskEventType.COMMAND_RUN_FAILED,
        CommandRunState.TIMED_OUT: TaskEventType.COMMAND_RUN_TIMED_OUT,
        CommandRunState.CANCELLED: TaskEventType.COMMAND_RUN_CANCELLED,
    }


def test_task_event_contracts_expose_replay_cursor_shape() -> None:
    now = datetime(2026, 6, 24, 17, 0, tzinfo=UTC)
    event = TaskEventRecord(
        event_id="event.1",
        event_seq=1,
        task_id="task.1",
        event_type=TaskEventType.HUMAN_REQUEST_OPENED,
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=now,
        flow_revision_id="flow-revision.1",
        dispatch_id="dispatch.1",
        attempt_id="attempt.1",
        node_key="implement_slice",
        actor_ref=None,
        payload={"request_id": "human-request.1"},
        prev_event_hash=None,
        event_hash="hash.1",
    )
    response = TaskEventListResponse(
        task_id="task.1",
        items=(event,),
        next_cursor="event.1",
        through_event_id="event.1",
    )

    assert response.items[0].event_type == "human_request_opened"
    assert response.items[0].payload == {"request_id": "human-request.1"}
    assert response.next_cursor == "event.1"
