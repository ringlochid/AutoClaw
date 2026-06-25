from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    CommandRunModel,
    DispatchTurnModel,
    FlowWaitStateModel,
)
from autoclaw.runtime.capabilities import (
    capability_rejection_for_command_run,
    resolve_effective_capabilities,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_run_continuation import (
    command_run_record_from_model,
    terminal_result_from_model,
)
from autoclaw.runtime.contracts import (
    COMMAND_RUN_TERMINAL_EVENT_TYPES,
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunCancelResponse,
    CommandRunListItem,
    CommandRunListResponse,
    CommandRunProgressUpdate,
    CommandRunRecord,
    CommandRunStartRequest,
    CommandRunStartResponse,
    CommandRunState,
    CommandRunTerminalResultRead,
    OperationFailureCode,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from autoclaw.runtime.dispatch.control import fence_foreground_dispatch
from autoclaw.runtime.errors import RuntimeOperationError, illegal_state_error
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.ids import command_run_id
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState
from autoclaw.runtime.task_events import append_task_event

_CONTROL_API_ACTOR_REF = "control_api"
_COMMAND_RUN_CONFLICT_NEXT_STEP = (
    "Reread the current command-run list for this task before retrying the command-run action."
)
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
    command_run = CommandRunModel(
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
    session.add(command_run)
    await session.flush((command_run,))

    session.add(
        FlowWaitStateModel(
            flow_id=state.flow.flow_id,
            task_id=task_id,
            waiting_cause=WaitingCause.WAITING_FOR_COMMAND_RUN.value,
            command_run_id=run_id,
            created_by_dispatch_id=dispatch.dispatch_id,
            created_at=created_at,
            updated_at=created_at,
        )
    )
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


async def list_command_runs(
    session: AsyncSession,
    *,
    task_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> CommandRunListResponse:
    await require_flow_for_task(session, task_id)
    page_limit = max(1, min(limit, 250))
    statement = (
        select(CommandRunModel)
        .where(CommandRunModel.task_id == task_id)
        .order_by(CommandRunModel.created_at.asc(), CommandRunModel.run_id.asc())
        .limit(page_limit + 1)
    )
    if cursor is not None:
        cursor_row = await _command_run_for_task(
            session,
            task_id=task_id,
            run_id=cursor,
        )
        if cursor_row is None:
            raise _command_run_conflict(f"command run cursor '{cursor}' is not current")
        statement = statement.where(
            or_(
                CommandRunModel.created_at > cursor_row.created_at,
                and_(
                    CommandRunModel.created_at == cursor_row.created_at,
                    CommandRunModel.run_id > cursor_row.run_id,
                ),
            )
        )

    rows = list(await session.scalars(statement))
    page_rows = rows[:page_limit]
    next_cursor = page_rows[-1].run_id if len(rows) > page_limit else None
    return CommandRunListResponse(
        task_id=task_id,
        items=tuple(_command_run_list_item_from_model(row) for row in page_rows),
        next_cursor=next_cursor,
    )


async def cancel_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunCancelResponse:
    flow = await require_flow_for_task(session, task_id)
    command_run = await _command_run_for_task(session, task_id=task_id, run_id=run_id)
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    _ensure_command_run_can_be_cancelled(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None

    cancelled_at = utc_now()
    command_run.state = CommandRunState.CANCELLATION_REQUESTED.value
    command_run.cancellation_requested_at = cancelled_at
    command_run.cancellation_requested_by_actor_ref = _CONTROL_API_ACTOR_REF
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
        actor_ref=_CONTROL_API_ACTOR_REF,
        payload={
            "run_id": run_id,
            "state": CommandRunState.CANCELLATION_REQUESTED.value,
            "occurred_at": cancelled_at.isoformat(),
            "summary": _COMMAND_RUN_CANCEL_REQUESTED_SUMMARY,
        },
    )
    await session.flush()
    return CommandRunCancelResponse(
        task_id=task_id,
        run=_command_run_list_item_from_model(command_run),
    )


async def record_command_run_progress(
    session: AsyncSession,
    *,
    task_id: str,
    update: CommandRunProgressUpdate,
) -> CommandRunRecord:
    flow = await require_flow_for_task(session, task_id)
    command_run = await _command_run_for_task(
        session,
        task_id=task_id,
        run_id=update.run_id,
    )
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    _ensure_command_run_can_record_progress(
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


async def record_command_run_terminal_result(
    session: AsyncSession,
    *,
    task_id: str,
    result: CommandRunTerminalResultRead,
) -> CommandRunRecord:
    flow = await require_flow_for_task(session, task_id)
    command_run = await _command_run_for_task(
        session,
        task_id=task_id,
        run_id=result.run_id,
    )
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    terminal_state = CommandRunState(result.state)
    if terminal_state not in TERMINAL_COMMAND_RUN_STATES:
        raise illegal_state_error(f"command run '{result.run_id}' did not reach a terminal state")
    _ensure_command_run_can_record_terminal_result(
        command_run=command_run,
        wait_state=wait_state,
        run_id=result.run_id,
    )
    assert command_run is not None
    assert wait_state is not None

    ended_at = result.ended_at
    command_run.state = terminal_state.value
    command_run.ended_at = ended_at
    command_run.terminal_summary = result.summary
    command_run.terminal_exit_code = result.exit_code
    command_run.terminal_signal = result.signal
    command_run.terminal_log_ref = result.log_ref
    command_run.latest_update = result.summary
    command_run.latest_log_ref = result.log_ref
    command_run.updated_at = ended_at
    await session.delete(wait_state)
    flow.updated_at = ended_at
    await append_task_event(
        session,
        task_id=task_id,
        event_type=COMMAND_RUN_TERMINAL_EVENT_TYPES[terminal_state],
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=ended_at,
        flow_revision_id=command_run.flow_revision_id,
        dispatch_id=command_run.dispatch_id,
        attempt_id=command_run.attempt_id,
        node_key=command_run.requester_node_key,
        payload={
            "run_id": result.run_id,
            "state": terminal_state.value,
            "summary": result.summary,
            "exit_code": result.exit_code,
            "signal": result.signal,
            "ended_at": ended_at.isoformat(),
            "log_ref": result.log_ref,
        },
    )
    await session.flush()
    return command_run_record_from_model(command_run)


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


async def _command_run_for_task(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunModel | None:
    return cast(
        CommandRunModel | None,
        await session.scalar(
            select(CommandRunModel).where(
                CommandRunModel.task_id == task_id,
                CommandRunModel.run_id == run_id,
            )
        ),
    )


def _ensure_command_run_can_be_cancelled(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    _ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state in {state.value for state in TERMINAL_COMMAND_RUN_STATES}:
        raise _command_run_conflict(f"command run '{run_id}' is already terminal")
    if command_run.state == CommandRunState.CANCELLATION_REQUESTED.value:
        raise _command_run_conflict(f"command run '{run_id}' already has cancellation requested")


def _ensure_command_run_can_record_progress(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    _ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state in {state.value for state in TERMINAL_COMMAND_RUN_STATES}:
        raise _command_run_conflict(f"command run '{run_id}' is already terminal")


def _ensure_command_run_can_record_terminal_result(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    _ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state in {state.value for state in TERMINAL_COMMAND_RUN_STATES}:
        raise _command_run_conflict(f"command run '{run_id}' is already terminal")


def _ensure_command_run_owns_active_wait(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    if command_run is None:
        raise _command_run_conflict(f"command run '{run_id}' is not current")
    if (
        wait_state is None
        or wait_state.waiting_cause != WaitingCause.WAITING_FOR_COMMAND_RUN.value
        or wait_state.command_run_id != command_run.run_id
    ):
        raise _command_run_conflict(
            f"command run '{run_id}' no longer owns the active command-run wait"
        )


def _command_run_conflict(summary: str) -> RuntimeOperationError:
    return RuntimeOperationError(
        code=OperationFailureCode.ILLEGAL_STATE,
        summary=summary,
        is_retryable=False,
        suggested_next_step=_COMMAND_RUN_CONFLICT_NEXT_STEP,
        status_code_override=409,
    )


def _command_run_list_item_from_model(row: CommandRunModel) -> CommandRunListItem:
    terminal_result = terminal_result_from_model(row)
    return CommandRunListItem(
        run_id=row.run_id,
        state=CommandRunState(row.state),
        command=row.command,
        description=row.description,
        workdir=row.workdir,
        created_at=coerce_datetime_to_utc(row.created_at),
        started_at=_optional_datetime(row.started_at),
        ended_at=_optional_datetime(row.ended_at),
        timeout_seconds=row.timeout_seconds,
        summary=terminal_result.summary if terminal_result is not None else row.latest_update,
        exit_code=terminal_result.exit_code if terminal_result is not None else None,
        signal=terminal_result.signal if terminal_result is not None else None,
        log_ref=terminal_result.log_ref if terminal_result is not None else row.latest_log_ref,
    )


def _optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return coerce_datetime_to_utc(value)


__all__ = [
    "cancel_command_run",
    "list_command_runs",
    "record_command_run_progress",
    "record_command_run_terminal_result",
    "start_command_run",
]
