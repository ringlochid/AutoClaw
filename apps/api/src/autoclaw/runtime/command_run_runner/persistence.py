from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.persistence.models import FlowModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_run.service import (
    claim_command_run_for_local_start,
    record_command_run_owned_process_pid,
    record_command_run_progress,
    record_command_run_terminal_result,
)
from autoclaw.runtime.contracts import (
    CommandRunProgressUpdate,
    CommandRunState,
    CommandRunTerminalResultRead,
    FlowStatus,
)
from autoclaw.runtime.contracts.command_runs import CommandRunTerminalState
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.post_commit.operations import write_runtime_operation

from .discovery import CurrentCommandRun, read_current_command_run_state
from .logs import command_run_log_ref, write_command_run_log_line
from .paths import best_effort_command_log_path
from .processes import is_process_group_running, stop_process_group

LOGGER = logging.getLogger(__name__)
RECOVERY_FAILED_WITHOUT_PID_SUMMARY = (
    "command runner lost local process ownership before completion because no owned "
    "process pid was persisted"
)
COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY = "command run cancelled before local process launch"
TASK_CANCELLED_SUMMARY = "command run cancelled because the task was cancelled"


async def claim_command_run_for_runner_start(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    log_ref: str,
    occurred_at: datetime,
) -> bool:
    try:
        await write_runtime_operation(
            lambda active_session: claim_command_run_for_local_start(
                active_session,
                task_id=record.task_id,
                run_id=record.run_id,
                log_ref=log_ref,
                occurred_at=occurred_at,
            )
        )
        return True
    except RuntimeOperationError as exc:
        LOGGER.info(
            "stale command-run start claim ignored for run %s: %s",
            record.run_id,
            exc.summary,
        )
        return False


async def record_runner_owned_process_pid(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    owned_process_pid: int,
    occurred_at: datetime,
) -> bool:
    try:
        await write_runtime_operation(
            lambda active_session: record_command_run_owned_process_pid(
                active_session,
                task_id=record.task_id,
                run_id=record.run_id,
                owned_process_pid=owned_process_pid,
                occurred_at=occurred_at,
            )
        )
        return True
    except RuntimeOperationError as exc:
        LOGGER.info(
            "stale command-run owned pid ignored for run %s: %s",
            record.run_id,
            exc.summary,
        )
        return False


async def record_runner_command_run_progress(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    summary: str,
    log_ref: str,
    owned_process_pid: int | None,
    occurred_at: datetime,
) -> bool:
    current_state = await read_current_command_run_state(
        session_factory,
        task_id=record.task_id,
        run_id=record.run_id,
    )
    if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
        return False
    try:
        await write_runtime_operation(
            lambda active_session: record_command_run_progress(
                active_session,
                task_id=record.task_id,
                update=CommandRunProgressUpdate(
                    run_id=record.run_id,
                    summary=summary,
                    log_ref=log_ref,
                    owned_process_pid=owned_process_pid,
                    occurred_at=occurred_at,
                ),
            )
        )
        return True
    except RuntimeOperationError as exc:
        LOGGER.info(
            "stale command-run progress ignored for run %s: %s",
            record.run_id,
            exc.summary,
        )
        return False


async def recover_unowned_command_run(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
) -> None:
    log_ref = command_run_log_ref(record.run_id)
    log_path = await best_effort_command_log_path(
        session_factory,
        task_id=record.task_id,
        log_ref=log_ref,
    )
    if record.owned_process_pid is None:
        await _recover_unowned_command_run_without_pid(
            session_factory,
            record,
            log_ref=log_ref,
            log_path=log_path,
        )
        return

    summary = (
        await resolve_cancelled_command_run_summary(session_factory, task_id=record.task_id)
        if record.state == CommandRunState.CANCELLATION_REQUESTED.value
        else "command runner recovered lost local process ownership before completion"
    )
    signal_name = None
    if is_process_group_running(record.owned_process_pid):
        signal_name = await stop_process_group(record.owned_process_pid)
        await write_command_run_log_line(
            log_path,
            (
                "command runner recovered detached process ownership after local runner loss: "
                f"pid {record.owned_process_pid}"
            ),
        )
    await write_command_run_log_line(log_path, summary)
    await record_runner_command_run_terminal(
        session_factory,
        record,
        state=(
            CommandRunState.CANCELLED
            if record.state == CommandRunState.CANCELLATION_REQUESTED.value
            else CommandRunState.FAILED
        ),
        summary=summary,
        exit_code=None,
        signal_name=signal_name,
        log_ref=log_ref,
    )


async def resolve_cancelled_command_run_summary(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> str:
    async with session_factory() as session:
        flow_status = await session.scalar(
            select(FlowModel.status).where(FlowModel.task_id == task_id)
        )
    if flow_status == FlowStatus.CANCELLED.value:
        return TASK_CANCELLED_SUMMARY
    return "command run cancelled after accepted cancellation request"


async def record_runner_command_run_terminal(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    state: CommandRunTerminalState,
    summary: str,
    exit_code: int | None,
    signal_name: str | None,
    log_ref: str,
) -> bool:
    try:
        await write_runtime_operation(
            lambda active_session: record_command_run_terminal_result(
                active_session,
                task_id=record.task_id,
                result=CommandRunTerminalResultRead(
                    run_id=record.run_id,
                    state=state,
                    summary=summary,
                    exit_code=exit_code,
                    signal=signal_name,
                    log_ref=log_ref,
                    ended_at=utc_now(),
                ),
            )
        )
        return True
    except RuntimeOperationError as exc:
        LOGGER.info(
            "stale command-run terminal result ignored for run %s: %s",
            record.run_id,
            exc.summary,
        )
        return False


async def _recover_unowned_command_run_without_pid(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    log_ref: str,
    log_path: Path,
) -> None:
    if record.state == CommandRunState.CANCELLATION_REQUESTED.value:
        await write_command_run_log_line(log_path, COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY)
        await record_runner_command_run_terminal(
            session_factory,
            record,
            state=CommandRunState.CANCELLED,
            summary=COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY,
            exit_code=None,
            signal_name=None,
            log_ref=log_ref,
        )
        return

    LOGGER.warning(
        "command-run recovery failed run %s because no owned process pid was persisted",
        record.run_id,
    )
    await write_command_run_log_line(log_path, RECOVERY_FAILED_WITHOUT_PID_SUMMARY)
    await record_runner_command_run_terminal(
        session_factory,
        record,
        state=CommandRunState.FAILED,
        summary=RECOVERY_FAILED_WITHOUT_PID_SUMMARY,
        exit_code=None,
        signal_name=None,
        log_ref=log_ref,
    )


__all__ = [
    "COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY",
    "claim_command_run_for_runner_start",
    "record_runner_command_run_progress",
    "record_runner_command_run_terminal",
    "record_runner_owned_process_pid",
    "recover_unowned_command_run",
    "resolve_cancelled_command_run_summary",
]
