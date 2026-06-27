from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.config import get_settings
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

from .discovery import (
    CurrentCommandRun,
    list_current_command_runs,
    read_current_command_run_state,
)
from .logs import command_run_log_ref, write_command_run_log_line
from .paths import best_effort_command_log_path, resolve_command_run_paths
from .processes import (
    command_run_terminal_exit_code,
    command_run_terminal_summary,
    copy_process_output_to_log,
    process_group_is_running,
    signal_name_from_returncode,
    stop_process,
    stop_process_group,
)

LOGGER = logging.getLogger(__name__)
_RUNNER_BY_LOOP: dict[int, CommandRunRunnerState] = {}
_RUNNER_TICK_SECONDS = 0.1
_RECOVERY_FAILED_WITHOUT_PID_SUMMARY = (
    "command runner lost local process ownership before completion because no owned "
    "process pid was persisted"
)
_COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY = "command run cancelled before local process launch"
_TASK_CANCELLED_SUMMARY = "command run cancelled because the task was cancelled"
_PROCESS_START_GATE_EXIT_CODE = 111
_SHELL_EXECUTABLE = shutil.which("sh") or "/bin/sh"
_PROCESS_START_GATE_SCRIPT = (
    "import os, sys\n"
    "gate_fd = int(sys.argv[1])\n"
    "command = sys.argv[2]\n"
    "shell_executable = sys.argv[3]\n"
    "try:\n"
    "    if os.read(gate_fd, 1) != b'1':\n"
    f"        raise SystemExit({_PROCESS_START_GATE_EXIT_CODE})\n"
    "finally:\n"
    "    os.close(gate_fd)\n"
    "os.execl(shell_executable, 'sh', '-lc', command)\n"
)


@dataclass
class CommandRunExecution:
    task: asyncio.Task[None]
    process: asyncio.subprocess.Process | None = None


@dataclass(frozen=True)
class CommandRunLaunchContext:
    log_ref: str
    log_path: Path
    workdir: Path


@dataclass
class CommandRunRunnerState:
    session_factory: async_sessionmaker[AsyncSession]
    wakeup: asyncio.Event
    idle: asyncio.Event
    started: asyncio.Event
    reconcile_lock: asyncio.Lock
    should_stop: bool
    task: asyncio.Task[None] | None
    active_runs: dict[str, CommandRunExecution]


async def start_command_run_runner() -> None:
    state = _ensure_runner_started()
    await state.started.wait()


async def stop_command_run_runner() -> None:
    await stop_command_run_runner_state(_RUNNER_BY_LOOP.pop(_loop_id(), None))


async def stop_all_command_run_runners() -> None:
    states = tuple(_RUNNER_BY_LOOP.values())
    _RUNNER_BY_LOOP.clear()
    for state in states:
        await stop_command_run_runner_state(state)


async def stop_command_run_runner_state(state: CommandRunRunnerState | None) -> None:
    if state is None or state.task is None:
        return
    state.should_stop = True
    task = state.task
    current_loop = asyncio.get_running_loop()
    if task.get_loop() is not current_loop:
        if task.get_loop().is_closed() or task.done():
            return
        try:
            task.get_loop().call_soon_threadsafe(task.cancel)
        except RuntimeError:
            LOGGER.warning("failed to cancel command-run runner on a foreign event loop")
        return
    if task.done():
        await task
        return
    state.wakeup.set()
    await task
    active_tasks = [execution.task for execution in tuple(state.active_runs.values())]
    if active_tasks:
        await asyncio.gather(*active_tasks, return_exceptions=True)


def notify_command_run_runner() -> None:
    state = _ensure_runner_started()
    state.idle.clear()
    state.wakeup.set()


def notify_command_run_runner_if_started() -> None:
    state = _RUNNER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    state.idle.clear()
    state.wakeup.set()


async def wait_for_command_run_runner_idle(*, max_wait_seconds: float = 5.0) -> None:
    state = _RUNNER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    state.idle.clear()
    state.wakeup.set()
    try:
        await asyncio.wait_for(state.idle.wait(), timeout=max_wait_seconds)
    except TimeoutError:
        return


async def drive_command_run_runner_once() -> bool:
    state = _ensure_runner_started()
    async with state.reconcile_lock:
        return await _reconcile_command_runs(state)


def _ensure_runner_started() -> CommandRunRunnerState:
    loop_id = _loop_id()
    state = _RUNNER_BY_LOOP.get(loop_id)
    if state is not None and state.task is not None and not state.task.done():
        return state

    from autoclaw.persistence.session import get_session_factory

    state = CommandRunRunnerState(
        session_factory=get_session_factory(),
        wakeup=asyncio.Event(),
        idle=asyncio.Event(),
        started=asyncio.Event(),
        reconcile_lock=asyncio.Lock(),
        should_stop=False,
        task=None,
        active_runs={},
    )
    state.task = asyncio.create_task(_run_command_run_runner(state), name="command-run-runner")
    _RUNNER_BY_LOOP[loop_id] = state
    return state


async def _run_command_run_runner(state: CommandRunRunnerState) -> None:
    try:
        state.started.set()
        state.idle.set()
        while not state.should_stop:
            try:
                await asyncio.wait_for(
                    state.wakeup.wait(),
                    timeout=_runner_tick_seconds(),
                )
            except TimeoutError:
                pass
            finally:
                state.wakeup.clear()
            if state.should_stop:
                break
            state.idle.clear()
            async with state.reconcile_lock:
                has_pending_work = await _reconcile_command_runs(state)
            if not has_pending_work:
                state.idle.set()
    except Exception:  # pragma: no cover - background safety net
        LOGGER.exception("command-run runner stopped unexpectedly")
    finally:
        state.should_stop = True
        state.started.set()
        await _stop_active_command_runs(state)
        state.idle.set()


def _runner_tick_seconds() -> float:
    return max(
        _RUNNER_TICK_SECONDS, float(get_settings().runtime.post_commit_reconcile_interval_seconds)
    )


async def _reconcile_command_runs(state: CommandRunRunnerState) -> bool:
    current_runs = await list_current_command_runs(state.session_factory)
    current_run_ids = {record.run_id for record in current_runs}
    for run_id, execution in tuple(state.active_runs.items()):
        if run_id not in current_run_ids:
            execution.task.cancel()

    for record in current_runs:
        if state.should_stop:
            break
        if record.run_id in state.active_runs:
            continue
        if record.state == CommandRunState.PENDING_START.value:
            _start_command_run_execution(state, record)
            continue
        if record.state == CommandRunState.CANCELLATION_REQUESTED.value:
            if record.owned_process_pid is None:
                log_ref = command_run_log_ref(record.run_id)
                log_path = await best_effort_command_log_path(
                    state.session_factory,
                    task_id=record.task_id,
                    log_ref=log_ref,
                )
                summary = "command run cancelled before local process launch"
                await write_command_run_log_line(log_path, summary)
                await _record_command_run_terminal(
                    state.session_factory,
                    record,
                    state=CommandRunState.CANCELLED,
                    summary=summary,
                    exit_code=None,
                    signal_name=None,
                    log_ref=log_ref,
                )
            else:
                await _recover_unowned_command_run(state.session_factory, record)
            continue
        if record.state == CommandRunState.RUNNING.value:
            await _recover_unowned_command_run(state.session_factory, record)
    return bool(current_runs or state.active_runs)


def _start_command_run_execution(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
) -> None:
    execution = CommandRunExecution(
        task=asyncio.create_task(
            _execute_command_run(state, record),
            name=f"command-run:{record.run_id}",
        ),
    )
    state.active_runs[record.run_id] = execution


async def _execute_command_run(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
) -> None:
    execution = state.active_runs[record.run_id]
    log_ref = command_run_log_ref(record.run_id)
    release_fd: int | None = None
    try:
        claim_started_at = utc_now()
        claimed = await _claim_command_run_for_local_start(
            state.session_factory,
            record,
            log_ref=log_ref,
            occurred_at=claim_started_at,
        )
        if not claimed:
            return
        launch_context = await _prepare_command_run_launch(
            state.session_factory,
            record,
            log_ref=log_ref,
        )
        if launch_context is None:
            return
        process, release_fd = await _start_command_run_process(record, launch_context)
        execution.process = process
        await _record_process_command_run_result(
            state,
            record,
            process,
            launch_context,
            release_fd=release_fd,
        )
        release_fd = None
    except asyncio.CancelledError:
        _close_process_start_gate(release_fd)
        if execution.process is not None:
            await stop_process(execution.process)
        raise
    except Exception as exc:
        LOGGER.exception("command-run runner failed for run %s", record.run_id)
        _close_process_start_gate(release_fd)
        if execution.process is not None:
            await stop_process(execution.process)
        log_path = await best_effort_command_log_path(
            state.session_factory,
            task_id=record.task_id,
            log_ref=log_ref,
        )
        await write_command_run_log_line(log_path, f"command runner error: {exc}")
        await _record_command_run_terminal(
            state.session_factory,
            record,
            state=CommandRunState.FAILED,
            summary=f"command runner failed before completion: {exc}",
            exit_code=None,
            signal_name=None,
            log_ref=log_ref,
        )
    finally:
        _close_process_start_gate(release_fd)
        state.active_runs.pop(record.run_id, None)
        state.wakeup.set()


async def _prepare_command_run_launch(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    log_ref: str,
) -> CommandRunLaunchContext | None:
    workdir, log_path = await resolve_command_run_paths(
        session_factory,
        task_id=record.task_id,
        workdir=record.workdir,
        log_ref=log_ref,
    )
    await write_command_run_log_line(log_path, f"$ {record.command}")
    if await asyncio.to_thread(workdir.is_dir):
        return CommandRunLaunchContext(log_ref=log_ref, log_path=log_path, workdir=workdir)

    await write_command_run_log_line(log_path, f"workdir does not exist: {workdir}")
    await _record_command_run_terminal(
        session_factory,
        record,
        state=CommandRunState.FAILED,
        summary=f"command failed to launch because workdir does not exist: {workdir}",
        exit_code=None,
        signal_name=None,
        log_ref=log_ref,
    )
    return None


async def _start_command_run_process(
    record: CurrentCommandRun,
    launch_context: CommandRunLaunchContext,
) -> tuple[asyncio.subprocess.Process, int]:
    read_fd, write_fd = os.pipe()
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            _PROCESS_START_GATE_SCRIPT,
            str(read_fd),
            record.command,
            _SHELL_EXECUTABLE,
            pass_fds=(read_fd,),
            close_fds=True,
            cwd=str(launch_context.workdir),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception:
        os.close(read_fd)
        os.close(write_fd)
        raise

    os.close(read_fd)
    return process, write_fd


async def _record_process_command_run_result(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    launch_context: CommandRunLaunchContext,
    *,
    release_fd: int | None,
) -> None:
    process_started_at = utc_now()
    current_state = await read_current_command_run_state(
        state.session_factory,
        task_id=record.task_id,
        run_id=record.run_id,
    )
    if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
        _close_process_start_gate(release_fd)
        signal_name = await stop_process(process)
        await _record_command_run_terminal(
            state.session_factory,
            record,
            state=CommandRunState.CANCELLED,
            summary=_COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY,
            exit_code=None,
            signal_name=signal_name,
            log_ref=launch_context.log_ref,
        )
        return
    if current_state is None:
        _close_process_start_gate(release_fd)
        await stop_process(process)
        raise asyncio.CancelledError

    owned_process_recorded = await _record_owned_process_pid(
        state.session_factory,
        record,
        owned_process_pid=process.pid,
        occurred_at=process_started_at,
    )
    if not owned_process_recorded:
        current_state = await read_current_command_run_state(
            state.session_factory,
            task_id=record.task_id,
            run_id=record.run_id,
        )
        _close_process_start_gate(release_fd)
        signal_name = await stop_process(process)
        if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
            await _record_command_run_terminal(
                state.session_factory,
                record,
                state=CommandRunState.CANCELLED,
                summary=_COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY,
                exit_code=None,
                signal_name=signal_name,
                log_ref=launch_context.log_ref,
            )
            return
        raise asyncio.CancelledError

    _release_process_start_gate(release_fd)
    process_deadline = (
        asyncio.get_running_loop().time() + record.timeout_seconds
        if record.timeout_seconds is not None
        else None
    )
    reader_task = asyncio.create_task(
        copy_process_output_to_log(process, launch_context.log_path),
        name=f"command-run-log:{record.run_id}",
    )
    progress_recorded = await _record_command_run_progress(
        state.session_factory,
        record,
        summary="command process started",
        log_ref=launch_context.log_ref,
        owned_process_pid=None,
        occurred_at=process_started_at,
    )
    terminal_state, signal_name = await _wait_for_process_terminal_state(
        state,
        record,
        process,
        deadline=process_deadline,
    )
    await reader_task
    if not progress_recorded and terminal_state not in {
        CommandRunState.CANCELLED,
        CommandRunState.TIMED_OUT,
    }:
        return

    returncode = process.returncode
    summary = (
        await _resolved_cancelled_summary(state.session_factory, task_id=record.task_id)
        if terminal_state == CommandRunState.CANCELLED
        else command_run_terminal_summary(
            terminal_state,
            returncode=returncode,
            signal_name=signal_name,
            timeout_seconds=record.timeout_seconds,
        )
    )
    await _record_command_run_terminal(
        state.session_factory,
        record,
        state=terminal_state,
        summary=summary,
        exit_code=command_run_terminal_exit_code(terminal_state, returncode),
        signal_name=signal_name,
        log_ref=launch_context.log_ref,
    )


def _close_process_start_gate(release_fd: int | None) -> None:
    if release_fd is None:
        return
    try:
        os.close(release_fd)
    except OSError:
        return


def _release_process_start_gate(release_fd: int | None) -> None:
    if release_fd is None:
        return
    try:
        os.write(release_fd, b"1")
    finally:
        _close_process_start_gate(release_fd)


async def _claim_command_run_for_local_start(
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


async def _record_owned_process_pid(
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


async def _resolved_cancelled_summary(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> str:
    async with session_factory() as session:
        flow_status = await session.scalar(
            select(FlowModel.status).where(FlowModel.task_id == task_id)
        )
    if flow_status == FlowStatus.CANCELLED.value:
        return _TASK_CANCELLED_SUMMARY
    return "command run cancelled after accepted cancellation request"


async def _wait_for_process_terminal_state(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    *,
    deadline: float | None,
) -> tuple[CommandRunTerminalState, str | None]:
    wait_task = asyncio.create_task(process.wait(), name=f"command-run-wait:{record.run_id}")
    while True:
        if wait_task.done() or process.returncode is not None:
            break
        if state.should_stop:
            signal_name = await stop_process(process)
            return CommandRunState.CANCELLED, signal_name
        current_state = await read_current_command_run_state(
            state.session_factory,
            task_id=record.task_id,
            run_id=record.run_id,
        )
        if current_state is None:
            await stop_process(process)
            raise asyncio.CancelledError
        if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
            signal_name = await stop_process(process)
            await wait_task
            return CommandRunState.CANCELLED, signal_name
        if deadline is not None and asyncio.get_running_loop().time() >= deadline:
            if process.returncode is not None:
                break
            signal_name = await stop_process(process)
            await wait_task
            return CommandRunState.TIMED_OUT, signal_name
        await asyncio.sleep(_RUNNER_TICK_SECONDS)

    await wait_task
    current_state = await read_current_command_run_state(
        state.session_factory,
        task_id=record.task_id,
        run_id=record.run_id,
    )
    if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
        return CommandRunState.CANCELLED, signal_name_from_returncode(process.returncode)
    if process.returncode == 0:
        return CommandRunState.SUCCEEDED, None
    return CommandRunState.FAILED, signal_name_from_returncode(process.returncode)


async def _record_command_run_progress(
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


async def _recover_unowned_command_run(
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
        if record.state == CommandRunState.CANCELLATION_REQUESTED.value:
            summary = "command run cancelled before local process launch"
            await write_command_run_log_line(log_path, summary)
            await _record_command_run_terminal(
                session_factory,
                record,
                state=CommandRunState.CANCELLED,
                summary=summary,
                exit_code=None,
                signal_name=None,
                log_ref=log_ref,
            )
            return

        LOGGER.warning(
            "command-run recovery failed run %s because no owned process pid was persisted",
            record.run_id,
        )
        await write_command_run_log_line(log_path, _RECOVERY_FAILED_WITHOUT_PID_SUMMARY)
        await _record_command_run_terminal(
            session_factory,
            record,
            state=CommandRunState.FAILED,
            summary=_RECOVERY_FAILED_WITHOUT_PID_SUMMARY,
            exit_code=None,
            signal_name=None,
            log_ref=log_ref,
        )
        return

    summary = (
        await _resolved_cancelled_summary(session_factory, task_id=record.task_id)
        if record.state == CommandRunState.CANCELLATION_REQUESTED.value
        else "command runner recovered lost local process ownership before completion"
    )
    signal_name = None
    if process_group_is_running(record.owned_process_pid):
        signal_name = await stop_process_group(record.owned_process_pid)
        await write_command_run_log_line(
            log_path,
            (
                "command runner recovered detached process ownership after local runner loss: "
                f"pid {record.owned_process_pid}"
            ),
        )
    await write_command_run_log_line(log_path, summary)
    await _record_command_run_terminal(
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


async def _record_command_run_terminal(
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


async def _stop_active_command_runs(state: CommandRunRunnerState) -> None:
    active_tasks = [execution.task for execution in tuple(state.active_runs.values())]
    for task in active_tasks:
        if not task.done():
            task.cancel()
    if active_tasks:
        await asyncio.gather(*active_tasks, return_exceptions=True)


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


__all__ = [
    "command_run_log_ref",
    "drive_command_run_runner_once",
    "notify_command_run_runner",
    "notify_command_run_runner_if_started",
    "start_command_run_runner",
    "stop_all_command_run_runners",
    "stop_command_run_runner",
    "wait_for_command_run_runner_idle",
]
