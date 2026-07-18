from __future__ import annotations

from datetime import datetime
from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.contracts import (
    CommandRunCancelResponse,
    CommandRunListResponse,
    CommandRunLogReadResponse,
    CommandRunProgressUpdate,
    CommandRunRecord,
    CommandRunStartRequest,
    CommandRunStartResponse,
    CommandRunTerminalResultRead,
    TaskEventSource,
)
from autoclaw.runtime.errors import illegal_state_error


async def start_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    request: CommandRunStartRequest,
) -> CommandRunStartResponse:
    _command_run_surface_unavailable()


async def list_command_runs(
    session: AsyncSession,
    *,
    task_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> CommandRunListResponse:
    _command_run_surface_unavailable()


async def read_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunRecord:
    _command_run_surface_unavailable()


async def read_command_run_log(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunLogReadResponse:
    _command_run_surface_unavailable()


async def cancel_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    actor_ref: str | None = None,
) -> CommandRunCancelResponse:
    _command_run_surface_unavailable()


async def request_command_run_cancellation(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    actor_ref: str | None = None,
    is_already_requested_allowed: bool = False,
) -> CommandRunRecord:
    _command_run_surface_unavailable()


async def record_command_run_progress(
    session: AsyncSession,
    *,
    task_id: str,
    update: CommandRunProgressUpdate,
) -> CommandRunRecord:
    _command_run_surface_unavailable()


async def claim_command_run_for_local_start(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    log_ref: str,
    occurred_at: datetime,
) -> CommandRunRecord:
    _command_run_surface_unavailable()


async def record_command_run_owned_process_pid(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
    owned_process_pid: int,
    occurred_at: datetime,
) -> CommandRunRecord:
    _command_run_surface_unavailable()


async def record_command_run_terminal_result(
    session: AsyncSession,
    *,
    task_id: str,
    result: CommandRunTerminalResultRead,
    event_source: TaskEventSource = TaskEventSource.CONTROLLER,
    actor_ref: str | None = None,
) -> CommandRunRecord:
    _command_run_surface_unavailable()


def _command_run_surface_unavailable() -> NoReturn:
    raise illegal_state_error(
        "command-run execution and readback are not available in this build",
        suggested_next_step=(
            "Do not retry this request; use only the controller capabilities exposed "
            "by this installation."
        ),
    )


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
