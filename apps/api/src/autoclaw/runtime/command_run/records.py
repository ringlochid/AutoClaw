from __future__ import annotations

from datetime import UTC, datetime

from autoclaw.persistence.models import CommandRunModel
from autoclaw.runtime.contracts import (
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunListItem,
    CommandRunRecord,
    CommandRunState,
    CommandRunTerminalResult,
    TaskEventSource,
)
from autoclaw.runtime.errors import illegal_state_error

_TASK_CANCELLED_SUMMARY = "command run cancelled because the task was cancelled"


def command_run_record_from_model(row: CommandRunModel) -> CommandRunRecord:
    return CommandRunRecord(
        run_id=row.run_id,
        task_id=row.task_id,
        dispatch_id=row.dispatch_id,
        attempt_id=row.attempt_id,
        command=row.command,
        description=row.description,
        workdir=row.workdir,
        state=CommandRunState(row.state),
        created_at=_coerce_datetime_to_utc(row.created_at),
        started_at=_optional_datetime(row.started_at),
        ended_at=_optional_datetime(row.ended_at),
        timeout_seconds=row.timeout_seconds,
        latest_update=row.latest_update,
        latest_log_ref=row.latest_log_ref,
        cancellation_requested_at=_optional_datetime(row.cancellation_requested_at),
        cancellation_requested_by_actor_ref=row.cancellation_requested_by_actor_ref,
        terminal_result=terminal_result_from_model(row),
        terminal_event_source=_terminal_event_source(row),
        terminal_actor_ref=row.terminal_actor_ref,
    )


def command_run_list_item_from_model(row: CommandRunModel) -> CommandRunListItem:
    terminal_result = terminal_result_from_model(row)
    return CommandRunListItem(
        run_id=row.run_id,
        state=CommandRunState(row.state),
        command=row.command,
        description=row.description,
        workdir=row.workdir,
        created_at=_coerce_datetime_to_utc(row.created_at),
        started_at=_optional_datetime(row.started_at),
        ended_at=_optional_datetime(row.ended_at),
        timeout_seconds=row.timeout_seconds,
        summary=terminal_result.summary if terminal_result is not None else row.latest_update,
        exit_code=terminal_result.exit_code if terminal_result is not None else None,
        signal=terminal_result.signal if terminal_result is not None else None,
        log_ref=terminal_result.log_ref if terminal_result is not None else row.latest_log_ref,
    )


def terminal_result_from_model(row: CommandRunModel) -> CommandRunTerminalResult | None:
    if CommandRunState(row.state) not in TERMINAL_COMMAND_RUN_STATES:
        return None
    if row.terminal_summary is None or row.ended_at is None:
        raise illegal_state_error(f"terminal command run '{row.run_id}' is missing result truth")
    return CommandRunTerminalResult(
        summary=row.terminal_summary,
        exit_code=row.terminal_exit_code,
        signal=row.terminal_signal,
        log_ref=row.terminal_log_ref,
    )


def _terminal_event_source(row: CommandRunModel) -> TaskEventSource | None:
    if row.terminal_event_source is None:
        state = CommandRunState(row.state)
        if state not in TERMINAL_COMMAND_RUN_STATES:
            return None
        if state == CommandRunState.CANCELLED:
            if (
                row.terminal_actor_ref == TaskEventSource.CONTROL_API.value
                or row.cancellation_requested_by_actor_ref is not None
            ):
                return TaskEventSource.CONTROL_API
            if row.terminal_summary == _TASK_CANCELLED_SUMMARY:
                return TaskEventSource.CONTROL_API
        return TaskEventSource.CONTROLLER
    return TaskEventSource(row.terminal_event_source)


def _optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _coerce_datetime_to_utc(value)


def _coerce_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "command_run_list_item_from_model",
    "command_run_record_from_model",
    "terminal_result_from_model",
]
