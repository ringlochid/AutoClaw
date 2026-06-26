from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.config import get_settings
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_runs import (
    record_command_run_progress,
    record_command_run_terminal_result,
)
from autoclaw.runtime.contracts import (
    CommandRunProgressUpdate,
    CommandRunState,
    CommandRunTerminalResultRead,
)
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
    signal_name_from_returncode,
    stop_process,
)

LOGGER = logging.getLogger(__name__)
_RUNNER_BY_LOOP: dict[int, CommandRunRunnerState] = {}
_RUNNER_TICK_SECONDS = 0.1
_UNOWNED_RUNNING_GRACE_SECONDS = 30.0


@dataclass
class CommandRunExecution:
    task: asyncio.Task[None]
    process: asyncio.subprocess.Process | None = None


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
    unowned_running_since_by_run_id: dict[str, float]


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
    notify_command_run_runner()
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
        unowned_running_since_by_run_id={},
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
    for run_id in tuple(state.unowned_running_since_by_run_id):
        if run_id not in current_run_ids or run_id in state.active_runs:
            state.unowned_running_since_by_run_id.pop(run_id, None)

    for record in current_runs:
        if state.should_stop:
            break
        if record.run_id in state.active_runs:
            state.unowned_running_since_by_run_id.pop(record.run_id, None)
            continue
        if record.state == CommandRunState.PENDING_START.value:
            state.unowned_running_since_by_run_id.pop(record.run_id, None)
            _start_command_run_execution(state, record)
            continue
        if record.state == CommandRunState.CANCELLATION_REQUESTED.value:
            state.unowned_running_since_by_run_id.pop(record.run_id, None)
            await _record_terminal_without_process(
                state.session_factory,
                record,
                state=CommandRunState.CANCELLED,
                summary="command run cancelled before local process launch",
                signal_name=None,
            )
            continue
        if record.state == CommandRunState.RUNNING.value and _unowned_running_record_is_stale(
            state,
            record.run_id,
        ):
            await _record_terminal_without_process(
                state.session_factory,
                record,
                state=CommandRunState.FAILED,
                summary="command runner lost local process ownership before completion",
                signal_name=None,
            )
    return bool(current_runs or state.active_runs)


def _unowned_running_record_is_stale(
    state: CommandRunRunnerState,
    run_id: str,
) -> bool:
    loop_time = asyncio.get_running_loop().time()
    first_seen = state.unowned_running_since_by_run_id.setdefault(run_id, loop_time)
    return loop_time - first_seen >= _UNOWNED_RUNNING_GRACE_SECONDS


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
    try:
        workdir, log_path = await resolve_command_run_paths(
            state.session_factory,
            task_id=record.task_id,
            workdir=record.workdir,
            log_ref=log_ref,
        )
        await write_command_run_log_line(log_path, f"$ {record.command}")
        if not await asyncio.to_thread(workdir.is_dir):
            await write_command_run_log_line(log_path, f"workdir does not exist: {workdir}")
            await _record_command_run_terminal(
                state.session_factory,
                record,
                state=CommandRunState.FAILED,
                summary=f"command failed to launch because workdir does not exist: {workdir}",
                exit_code=None,
                signal_name=None,
                log_ref=log_ref,
            )
            return

        process = await asyncio.create_subprocess_shell(
            record.command,
            cwd=str(workdir),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        execution.process = process
        process_started_at = utc_now()
        process_deadline = (
            asyncio.get_running_loop().time() + record.timeout_seconds
            if record.timeout_seconds is not None
            else None
        )
        reader_task = asyncio.create_task(
            copy_process_output_to_log(process, log_path),
            name=f"command-run-log:{record.run_id}",
        )
        progress_task = asyncio.create_task(
            _record_command_run_progress(
                state.session_factory,
                record,
                summary="command process started",
                log_ref=log_ref,
                occurred_at=process_started_at,
            ),
            name=f"command-run-progress:{record.run_id}",
        )
        terminal_state, signal_name = await _wait_for_process_terminal_state(
            state,
            record,
            process,
            deadline=process_deadline,
        )
        await reader_task
        progress_recorded = await progress_task
        if not progress_recorded and terminal_state not in {
            CommandRunState.CANCELLED,
            CommandRunState.TIMED_OUT,
        }:
            return
        returncode = process.returncode
        summary = command_run_terminal_summary(
            terminal_state,
            returncode=returncode,
            signal_name=signal_name,
            timeout_seconds=record.timeout_seconds,
        )
        await _record_command_run_terminal(
            state.session_factory,
            record,
            state=terminal_state,
            summary=summary,
            exit_code=command_run_terminal_exit_code(terminal_state, returncode),
            signal_name=signal_name,
            log_ref=log_ref,
        )
    except asyncio.CancelledError:
        if execution.process is not None:
            await stop_process(execution.process)
        raise
    except Exception as exc:
        LOGGER.exception("command-run runner failed for run %s", record.run_id)
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
            summary=f"command runner failed before completion: {_bounded_summary(str(exc))}",
            exit_code=None,
            signal_name=None,
            log_ref=log_ref,
        )
    finally:
        state.active_runs.pop(record.run_id, None)
        state.wakeup.set()


async def _wait_for_process_terminal_state(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    *,
    deadline: float | None,
) -> tuple[CommandRunState, str | None]:
    wait_task = asyncio.create_task(process.wait(), name=f"command-run-wait:{record.run_id}")
    while True:
        if deadline is not None and asyncio.get_running_loop().time() >= deadline:
            signal_name = await stop_process(process)
            await wait_task
            return CommandRunState.TIMED_OUT, signal_name
        if wait_task.done():
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


async def _record_terminal_without_process(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    state: CommandRunState,
    summary: str,
    signal_name: str | None,
) -> None:
    log_ref = command_run_log_ref(record.run_id)
    log_path = await best_effort_command_log_path(
        session_factory,
        task_id=record.task_id,
        log_ref=log_ref,
    )
    await write_command_run_log_line(log_path, summary)
    await _record_command_run_terminal(
        session_factory,
        record,
        state=state,
        summary=summary,
        exit_code=None,
        signal_name=signal_name,
        log_ref=log_ref,
    )


async def _record_command_run_terminal(
    session_factory: async_sessionmaker[AsyncSession],
    record: CurrentCommandRun,
    *,
    state: CommandRunState,
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
                    summary=_bounded_summary(summary),
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
    if active_tasks:
        await asyncio.gather(*active_tasks, return_exceptions=True)


def _bounded_summary(summary: str) -> str:
    normalized = " ".join(summary.split())
    if len(normalized) <= 240:
        return normalized
    return normalized[:237].rstrip() + "..."


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
