from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowWaitStateModel,
)
from autoclaw.runtime.capabilities import (
    capability_rejection_for_command_run,
    resolve_effective_capabilities,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_run.guards import (
    ensure_command_run_can_be_cancelled,
    ensure_command_run_can_be_claimed_for_local_start,
    ensure_command_run_can_record_owned_process_pid,
    ensure_command_run_can_record_progress,
    ensure_command_run_can_record_terminal_result,
)
from autoclaw.runtime.command_run.reads import (
    list_command_runs,
    load_command_run_for_task,
    read_command_run,
    read_command_run_log,
)
from autoclaw.runtime.command_run.records import (
    command_run_list_item_from_model,
    command_run_record_from_model,
)
from autoclaw.runtime.contracts import (
    COMMAND_RUN_TERMINAL_EVENT_TYPES,
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunCancelResponse,
    CommandRunProgressUpdate,
    CommandRunRecord,
    CommandRunStartRequest,
    CommandRunStartResponse,
    CommandRunState,
    CommandRunTerminalResultRead,
    FlowStatus,
    OperationFailureCode,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from autoclaw.runtime.dispatch.control import fence_foreground_dispatch
from autoclaw.runtime.errors import RuntimeOperationError, illegal_state_error
from autoclaw.runtime.ids import command_run_id
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState
from autoclaw.runtime.task_events import append_task_event
from autoclaw.runtime.workspace_leases import release_workspace_root_lease

_COMMAND_RUN_CANCEL_REQUESTED_SUMMARY = "command run cancellation requested"


async def start_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    request: CommandRunStartRequest,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
) -> CommandRunStartResponse:
    capabilities = await resolve_effective_capabilities(
        session,
        state=state,
        execution_scope="command_run_start",
    )
    rejection = capability_rejection_for_command_run(capabilities)
    if rejection is not None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CAPABILITY_REJECTED,
            summary=rejection.message,
            is_retryable=False,
            suggested_next_step=rejection.next_legal_action,
        )

    await _ensure_command_run_start_is_current(session, task_id=task_id, state=state)

    created_at = utc_now()
    run_id = await _next_command_run_id(session, task_id=task_id)
    command_run = _build_command_run_for_start(
        task_id=task_id,
        run_id=run_id,
        request=request,
        state=state,
        dispatch=dispatch,
        created_at=created_at,
    )
    session.add(command_run)
    await session.flush((command_run,))

    session.add(
        _build_command_run_wait_state(
            task_id=task_id, run_id=run_id, state=state, dispatch=dispatch, created_at=created_at
        )
    )
    await _append_command_run_started_event(
        session,
        task_id=task_id,
        run_id=run_id,
        request=request,
        state=state,
        dispatch=dispatch,
        created_at=created_at,
    )
    state.flow.updated_at = created_at
    await fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=state.flow,
        dispatch=dispatch,
        reason=f"command_run:{run_id}:started",
    )
    await session.flush()
    return CommandRunStartResponse(
        run_id=run_id,
        task_id=task_id,
        state=CommandRunState.PENDING_START,
    )


async def cancel_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    actor_ref: str | None = None,
) -> CommandRunCancelResponse:
    command_run = await request_command_run_cancellation(
        session,
        task_id=task_id,
        run_id=run_id,
        actor_ref=actor_ref,
    )
    return CommandRunCancelResponse(
        task_id=task_id,
        run=command_run_list_item_from_model(command_run),
    )


async def request_command_run_cancellation(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    actor_ref: str | None = None,
    is_already_requested_allowed: bool = False,
) -> CommandRunModel:
    flow = await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(session, task_id=task_id, run_id=run_id)
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    ensure_command_run_can_be_cancelled(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
        is_already_requested_allowed=is_already_requested_allowed,
    )
    assert command_run is not None
    if command_run.state == CommandRunState.CANCELLATION_REQUESTED.value:
        return command_run

    cancelled_at = utc_now()
    command_run.state = CommandRunState.CANCELLATION_REQUESTED.value
    command_run.cancellation_requested_at = cancelled_at
    command_run.cancellation_requested_by_actor_ref = actor_ref
    command_run.latest_update = _COMMAND_RUN_CANCEL_REQUESTED_SUMMARY
    command_run.updated_at = cancelled_at
    flow.updated_at = cancelled_at
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.COMMAND_RUN_CANCEL_REQUESTED,
        event_source=TaskEventSource.CONTROL_API,
        occurred_at=cancelled_at,
        flow_revision_id=command_run.flow_revision_id,
        dispatch_id=command_run.dispatch_id,
        attempt_id=command_run.attempt_id,
        node_key=command_run.requester_node_key,
        actor_ref=actor_ref,
        payload={
            "run_id": run_id,
            "state": CommandRunState.CANCELLATION_REQUESTED.value,
            "occurred_at": cancelled_at.isoformat(),
            "summary": _COMMAND_RUN_CANCEL_REQUESTED_SUMMARY,
        },
    )
    await session.flush()
    return command_run


async def record_command_run_progress(
    session: AsyncSession,
    *,
    task_id: str,
    update: CommandRunProgressUpdate,
) -> CommandRunRecord:
    flow = await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(
        session,
        task_id=task_id,
        run_id=update.run_id,
    )
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    ensure_command_run_can_record_progress(
        command_run=command_run,
        wait_state=wait_state,
        run_id=update.run_id,
    )
    assert command_run is not None

    occurred_at = update.occurred_at
    if command_run.started_at is None:
        command_run.started_at = occurred_at
    if command_run.state == CommandRunState.PENDING_START.value:
        command_run.state = CommandRunState.RUNNING.value
    if update.owned_process_pid is not None:
        command_run.owned_process_pid = update.owned_process_pid
    command_run.latest_update = update.summary
    command_run.latest_log_ref = update.log_ref
    command_run.updated_at = occurred_at
    flow.updated_at = occurred_at
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.COMMAND_RUN_PROGRESSED,
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=occurred_at,
        flow_revision_id=command_run.flow_revision_id,
        dispatch_id=command_run.dispatch_id,
        attempt_id=command_run.attempt_id,
        node_key=command_run.requester_node_key,
        payload={
            "run_id": update.run_id,
            "summary": update.summary,
            "log_ref": update.log_ref,
            "occurred_at": occurred_at.isoformat(),
            "state": command_run.state,
        },
    )
    await session.flush()
    return command_run_record_from_model(command_run)


async def claim_command_run_for_local_start(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    log_ref: str,
    occurred_at: datetime,
) -> CommandRunRecord:
    flow = await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(session, task_id=task_id, run_id=run_id)
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    ensure_command_run_can_be_claimed_for_local_start(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None

    command_run.state = CommandRunState.RUNNING.value
    command_run.started_at = command_run.started_at or occurred_at
    command_run.latest_log_ref = log_ref
    command_run.updated_at = occurred_at
    flow.updated_at = occurred_at
    await session.flush()
    return command_run_record_from_model(command_run)


async def record_command_run_owned_process_pid(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    owned_process_pid: int,
    occurred_at: datetime,
) -> CommandRunRecord:
    flow = await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(session, task_id=task_id, run_id=run_id)
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    ensure_command_run_can_record_owned_process_pid(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None

    command_run.owned_process_pid = owned_process_pid
    command_run.started_at = command_run.started_at or occurred_at
    command_run.updated_at = occurred_at
    flow.updated_at = occurred_at
    await session.flush()
    return command_run_record_from_model(command_run)


async def record_command_run_terminal_result(
    session: AsyncSession,
    *,
    task_id: str,
    result: CommandRunTerminalResultRead,
    event_source: TaskEventSource = TaskEventSource.CONTROLLER,
    actor_ref: str | None = None,
) -> CommandRunRecord:
    flow = await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(
        session,
        task_id=task_id,
        run_id=result.run_id,
    )
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    terminal_state = CommandRunState(result.state)
    if terminal_state not in TERMINAL_COMMAND_RUN_STATES:
        raise illegal_state_error(f"command run '{result.run_id}' did not reach a terminal state")
    ensure_command_run_can_record_terminal_result(
        command_run=command_run,
        wait_state=wait_state,
        run_id=result.run_id,
    )
    assert command_run is not None
    assert wait_state is not None

    terminal_actor_ref = _apply_command_run_terminal_result(
        command_run,
        result=result,
        terminal_state=terminal_state,
        event_source=event_source,
        actor_ref=actor_ref,
    )
    await session.delete(wait_state)
    flow.updated_at = result.ended_at
    if _should_release_command_run_workspace(flow):
        await release_workspace_root_lease(session, task_id=task_id)
    await append_task_event(
        session,
        task_id=task_id,
        event_type=COMMAND_RUN_TERMINAL_EVENT_TYPES[terminal_state],
        event_source=event_source,
        occurred_at=result.ended_at,
        flow_revision_id=command_run.flow_revision_id,
        dispatch_id=command_run.dispatch_id,
        attempt_id=command_run.attempt_id,
        node_key=command_run.requester_node_key,
        actor_ref=terminal_actor_ref,
        payload=_build_command_run_terminal_event_payload(
            command_run,
            result=result,
            terminal_state=terminal_state,
            terminal_actor_ref=terminal_actor_ref,
        ),
    )
    await session.flush()
    return command_run_record_from_model(command_run)


def _apply_command_run_terminal_result(
    command_run: CommandRunModel,
    *,
    result: CommandRunTerminalResultRead,
    terminal_state: CommandRunState,
    event_source: TaskEventSource,
    actor_ref: str | None,
) -> str | None:
    terminal_actor_ref = actor_ref
    if terminal_state == CommandRunState.CANCELLED and terminal_actor_ref is None:
        terminal_actor_ref = command_run.cancellation_requested_by_actor_ref

    command_run.state = terminal_state.value
    command_run.owned_process_pid = None
    command_run.ended_at = result.ended_at
    command_run.terminal_summary = result.summary
    command_run.terminal_exit_code = result.exit_code
    command_run.terminal_signal = result.signal
    command_run.terminal_log_ref = result.log_ref
    command_run.terminal_event_source = event_source.value
    command_run.terminal_actor_ref = terminal_actor_ref
    command_run.latest_update = result.summary
    command_run.latest_log_ref = result.log_ref
    command_run.updated_at = result.ended_at
    if terminal_state == CommandRunState.CANCELLED:
        command_run.cancellation_requested_at = (
            command_run.cancellation_requested_at or result.ended_at
        )
        command_run.cancellation_requested_by_actor_ref = (
            command_run.cancellation_requested_by_actor_ref or terminal_actor_ref
        )
    return terminal_actor_ref


def _should_release_command_run_workspace(flow: FlowModel) -> bool:
    terminal_flow_states = {
        FlowStatus.SUCCEEDED.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
    }
    return flow.status in terminal_flow_states and flow.current_open_dispatch_id is None


def _build_command_run_terminal_event_payload(
    command_run: CommandRunModel,
    *,
    result: CommandRunTerminalResultRead,
    terminal_state: CommandRunState,
    terminal_actor_ref: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": result.run_id,
        "state": terminal_state.value,
        "summary": result.summary,
        "exit_code": result.exit_code,
        "signal": result.signal,
        "ended_at": result.ended_at.isoformat(),
        "log_ref": result.log_ref,
    }
    if terminal_state == CommandRunState.CANCELLED:
        initiated_by_actor_ref = (
            terminal_actor_ref or command_run.cancellation_requested_by_actor_ref
        )
        if initiated_by_actor_ref is not None:
            payload["initiated_by_actor_ref"] = initiated_by_actor_ref
    return payload


def _build_command_run_for_start(
    *,
    task_id: str,
    run_id: str,
    request: CommandRunStartRequest,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    created_at: datetime,
) -> CommandRunModel:
    return CommandRunModel(
        run_id=run_id,
        task_id=task_id,
        flow_id=state.flow.flow_id,
        flow_revision_id=state.flow_revision.flow_revision_id,
        flow_node_id=state.current_node.flow_node_id,
        assignment_id=state.current_assignment.assignment_id,
        attempt_id=state.current_attempt.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        requester_node_key=state.current_node.node_key,
        command=request.command,
        description=request.description,
        workdir=request.workdir,
        timeout_seconds=request.timeout_seconds,
        state=CommandRunState.PENDING_START.value,
        created_at=created_at,
        updated_at=created_at,
    )


def _build_command_run_wait_state(
    *,
    task_id: str,
    run_id: str,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    created_at: datetime,
) -> FlowWaitStateModel:
    return FlowWaitStateModel(
        flow_id=state.flow.flow_id,
        task_id=task_id,
        waiting_cause=WaitingCause.WAITING_FOR_COMMAND_RUN.value,
        command_run_id=run_id,
        created_by_dispatch_id=dispatch.dispatch_id,
        created_at=created_at,
        updated_at=created_at,
    )


async def _append_command_run_started_event(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    request: CommandRunStartRequest,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    created_at: datetime,
) -> None:
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.COMMAND_RUN_STARTED,
        event_source=TaskEventSource.NODE,
        occurred_at=created_at,
        flow_revision_id=state.flow_revision.flow_revision_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=state.current_attempt.attempt_id,
        node_key=state.current_node.node_key,
        payload={
            "run_id": run_id,
            "command": request.command,
            "description": request.description,
            "workdir": request.workdir,
            "state": CommandRunState.PENDING_START.value,
            "timeout_seconds": request.timeout_seconds,
        },
    )


async def _ensure_command_run_start_is_current(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
) -> None:
    existing_wait = await session.get(FlowWaitStateModel, state.flow.flow_id)
    if existing_wait is not None:
        raise illegal_state_error(
            f"task '{task_id}' is already waiting for {existing_wait.waiting_cause}"
        )

    existing_run = await session.scalar(
        select(CommandRunModel.run_id)
        .where(
            CommandRunModel.task_id == task_id,
            CommandRunModel.flow_id == state.flow.flow_id,
            CommandRunModel.flow_node_id == state.current_node.flow_node_id,
            CommandRunModel.assignment_id == state.current_assignment.assignment_id,
            CommandRunModel.attempt_id == state.current_attempt.attempt_id,
            CommandRunModel.state.not_in(
                tuple(state.value for state in TERMINAL_COMMAND_RUN_STATES)
            ),
        )
        .limit(1)
    )
    if existing_run is not None:
        raise illegal_state_error("current node execution already owns an active command run")


async def _next_command_run_id(session: AsyncSession, *, task_id: str) -> str:
    run_count = await session.scalar(
        select(func.count(CommandRunModel.run_id)).where(CommandRunModel.task_id == task_id)
    )
    return command_run_id(task_id, int(run_count or 0) + 1)


async def _require_flow_for_task(
    session: AsyncSession,
    task_id: str,
) -> FlowModel:
    from autoclaw.runtime.flow.queries import require_flow_for_task

    return await require_flow_for_task(session, task_id)


__all__ = [
    "cancel_command_run",
    "claim_command_run_for_local_start",
    "list_command_runs",
    "read_command_run",
    "read_command_run_log",
    "record_command_run_owned_process_pid",
    "record_command_run_progress",
    "record_command_run_terminal_result",
    "request_command_run_cancellation",
    "start_command_run",
]
