from __future__ import annotations

from datetime import UTC, datetime

from autoclaw.persistence.models import CommandRunModel
from autoclaw.runtime.contracts import (
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunRecord,
    CommandRunState,
    CommandRunTerminalResult,
)
from autoclaw.runtime.errors import illegal_state_error


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
        terminal_result=terminal_result_from_model(row),
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


def _optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _coerce_datetime_to_utc(value)


def _coerce_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["command_run_record_from_model", "terminal_result_from_model"]
