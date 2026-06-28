from __future__ import annotations

from datetime import datetime

from autoclaw.persistence import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowWaitStateModel,
    PendingHumanRequestModel,
)
from autoclaw.runtime.contracts import (
    CommandRunState,
    HumanRequestKind,
    HumanRequestResolutionKind,
    HumanRequestResolutionSurface,
    HumanRequestStatus,
    TaskEventSource,
    WaitingCause,
)
from sqlalchemy.ext.asyncio import AsyncSession

EXTERNAL_WAIT_BOUNDARY_CASES = (
    "open_human_request",
    "terminal_human_request",
    "running_command_run",
    "terminal_command_run",
)


def add_external_wait_source(
    session: AsyncSession,
    *,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    external_wait_case: str,
    observed_at: datetime,
) -> None:
    if external_wait_case == "open_human_request":
        human_request = _human_request_source_for_dispatch(
            dispatch,
            status=HumanRequestStatus.OPEN,
            observed_at=observed_at,
        )
        session.add(human_request)
        session.add(
            _wait_state_for_external_wait(
                flow=flow,
                dispatch=dispatch,
                waiting_cause=WaitingCause.WAITING_FOR_HUMAN_REQUEST,
                observed_at=observed_at,
                source_id=human_request.request_id,
            )
        )
        return
    if external_wait_case == "terminal_human_request":
        session.add(
            _human_request_source_for_dispatch(
                dispatch,
                status=HumanRequestStatus.RESOLVED,
                observed_at=observed_at,
            )
        )
        return
    if external_wait_case == "running_command_run":
        command_run = _command_run_source_for_dispatch(
            dispatch,
            state=CommandRunState.RUNNING,
            observed_at=observed_at,
        )
        session.add(command_run)
        session.add(
            _wait_state_for_external_wait(
                flow=flow,
                dispatch=dispatch,
                waiting_cause=WaitingCause.WAITING_FOR_COMMAND_RUN,
                observed_at=observed_at,
                source_id=command_run.run_id,
            )
        )
        return
    if external_wait_case == "terminal_command_run":
        session.add(
            _command_run_source_for_dispatch(
                dispatch,
                state=CommandRunState.SUCCEEDED,
                observed_at=observed_at,
            )
        )
        return
    raise AssertionError(f"unsupported external wait case {external_wait_case}")


def _human_request_source_for_dispatch(
    dispatch: DispatchTurnModel,
    *,
    status: HumanRequestStatus,
    observed_at: datetime,
) -> PendingHumanRequestModel:
    assert dispatch.task_id is not None
    assert dispatch.flow_id is not None
    assert dispatch.flow_revision_id is not None
    assert dispatch.flow_node_id is not None
    assert dispatch.assignment_id is not None
    assert dispatch.attempt_id is not None
    is_open = status == HumanRequestStatus.OPEN
    return PendingHumanRequestModel(
        request_id=f"human-request.{dispatch.dispatch_id}.0001",
        task_id=dispatch.task_id,
        flow_id=dispatch.flow_id,
        flow_revision_id=dispatch.flow_revision_id,
        flow_node_id=dispatch.flow_node_id,
        assignment_id=dispatch.assignment_id,
        attempt_id=dispatch.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        requester_node_key=dispatch.node_key,
        kind=HumanRequestKind.DIRECTION.value,
        title="Choose next step",
        summary="External wait watchdog test.",
        items_json=[
            {
                "item_id": "next_step",
                "prompt": "Proceed?",
                "options": [{"id": "proceed", "title": "Proceed"}],
                "recommended_option": "proceed",
                "input_payload_schema": None,
            }
        ],
        timeout_json={"due_at": None, "default_behavior": None},
        suggested_human_instruction="Choose proceed.",
        status=status.value,
        resolution_kind=None if is_open else HumanRequestResolutionKind.ANSWERED.value,
        item_responses_json=None
        if is_open
        else [
            {
                "item_id": "next_step",
                "selected_option": "proceed",
                "freeform_answer": None,
                "extra_notes": None,
                "response_payload": None,
            }
        ],
        resolved_at=None if is_open else observed_at,
        resolved_by_actor_ref=None if is_open else "test",
        resolved_by_surface=None if is_open else HumanRequestResolutionSurface.OPERATOR_MCP.value,
        resolution_policy_basis=None if is_open else "test",
        opened_at=dispatch.rendered_at,
        updated_at=observed_at,
    )


def _command_run_source_for_dispatch(
    dispatch: DispatchTurnModel,
    *,
    state: CommandRunState,
    observed_at: datetime,
) -> CommandRunModel:
    assert dispatch.task_id is not None
    assert dispatch.flow_id is not None
    assert dispatch.flow_revision_id is not None
    assert dispatch.flow_node_id is not None
    assert dispatch.assignment_id is not None
    assert dispatch.attempt_id is not None
    is_terminal = state in {
        CommandRunState.SUCCEEDED,
        CommandRunState.FAILED,
        CommandRunState.TIMED_OUT,
        CommandRunState.CANCELLED,
    }
    return CommandRunModel(
        run_id=f"command-run.{dispatch.dispatch_id}.0001",
        task_id=dispatch.task_id,
        flow_id=dispatch.flow_id,
        flow_revision_id=dispatch.flow_revision_id,
        flow_node_id=dispatch.flow_node_id,
        assignment_id=dispatch.assignment_id,
        attempt_id=dispatch.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        requester_node_key=dispatch.node_key,
        command="bash -lc 'true'",
        description="External wait watchdog test.",
        workdir=None,
        timeout_seconds=300,
        state=state.value,
        terminal_summary="Command succeeded." if is_terminal else None,
        terminal_exit_code=0 if state == CommandRunState.SUCCEEDED else None,
        terminal_event_source=TaskEventSource.CONTROLLER.value if is_terminal else None,
        created_at=dispatch.rendered_at,
        started_at=dispatch.rendered_at,
        ended_at=observed_at if is_terminal else None,
        updated_at=observed_at,
    )


def _wait_state_for_external_wait(
    *,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    waiting_cause: WaitingCause,
    observed_at: datetime,
    source_id: str,
) -> FlowWaitStateModel:
    return FlowWaitStateModel(
        flow_id=flow.flow_id,
        task_id=flow.task_id,
        waiting_cause=waiting_cause.value,
        pending_human_request_id=source_id
        if waiting_cause == WaitingCause.WAITING_FOR_HUMAN_REQUEST
        else None,
        command_run_id=source_id if waiting_cause == WaitingCause.WAITING_FOR_COMMAND_RUN else None,
        created_by_dispatch_id=dispatch.dispatch_id,
        created_at=observed_at,
        updated_at=observed_at,
    )


__all__ = ["EXTERNAL_WAIT_BOUNDARY_CASES", "add_external_wait_source"]
