from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.config import get_settings
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import CommandRunState
from autoclaw.runtime.contracts.command_runs import CommandRunTerminalState

from .discovery import (
    CurrentCommandRun,
    list_current_command_runs,
    read_current_command_run_state,
)
from .launch import (
    CommandRunLaunchContext,
    close_process_start_gate,
    prepare_command_run_launch,
    release_process_start_gate,
    start_command_run_process,
)
from .logs import command_run_log_ref, write_command_run_log_line
from .paths import best_effort_command_log_path
from .persistence import (
    COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY,
    claim_command_run_for_runner_start,
    record_runner_command_run_progress,
    record_runner_command_run_terminal,
    record_runner_owned_process_pid,
    recover_unowned_command_run,
    resolve_cancelled_command_run_summary,
)
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
                summary = COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY
                await write_command_run_log_line(log_path, summary)
                await record_runner_command_run_terminal(
                    state.session_factory,
                    record,
                    state=CommandRunState.CANCELLED,
                    summary=summary,
                    exit_code=None,
                    signal_name=None,
                    log_ref=log_ref,
                )
            else:
                await recover_unowned_command_run(state.session_factory, record)
            continue
        if record.state == CommandRunState.RUNNING.value:
            await recover_unowned_command_run(state.session_factory, record)
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
        claimed = await claim_command_run_for_runner_start(
            state.session_factory,
            record,
            log_ref=log_ref,
            occurred_at=claim_started_at,
        )
        if not claimed:
            return
        launch_context = await prepare_command_run_launch(
            state.session_factory,
            record,
            log_ref=log_ref,
        )
        if launch_context is None:
            return
        process, release_fd = await start_command_run_process(record, launch_context)
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
        close_process_start_gate(release_fd)
        if execution.process is not None:
            await stop_process(execution.process)
        raise
    except Exception as exc:
        LOGGER.exception("command-run runner failed for run %s", record.run_id)
        close_process_start_gate(release_fd)
        if execution.process is not None:
            await stop_process(execution.process)
        log_path = await best_effort_command_log_path(
            state.session_factory,
            task_id=record.task_id,
            log_ref=log_ref,
        )
        await write_command_run_log_line(log_path, f"command runner error: {exc}")
        await record_runner_command_run_terminal(
            state.session_factory,
            record,
            state=CommandRunState.FAILED,
            summary=f"command runner failed before completion: {exc}",
            exit_code=None,
            signal_name=None,
            log_ref=log_ref,
        )
    finally:
        close_process_start_gate(release_fd)
        state.active_runs.pop(record.run_id, None)
        state.wakeup.set()


async def _record_process_command_run_result(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    launch_context: CommandRunLaunchContext,
    *,
    release_fd: int | None,
) -> None:
    process_started_at = utc_now()
    if await _stop_process_if_launch_is_no_longer_current(
        state,
        record,
        process,
        launch_context,
        release_fd=release_fd,
    ):
        return

    if not await _record_process_ownership_or_stop(
        state,
        record,
        process,
        launch_context,
        release_fd=release_fd,
        process_started_at=process_started_at,
    ):
        return

    release_process_start_gate(release_fd)
    progress_recorded, terminal_state, signal_name = await _wait_for_recorded_process_completion(
        state,
        record,
        process,
        launch_context,
        process_started_at=process_started_at,
    )
    if not progress_recorded and terminal_state not in {
        CommandRunState.CANCELLED,
        CommandRunState.TIMED_OUT,
    }:
        return

    await _record_completed_process_terminal(
        state,
        record,
        process,
        launch_context,
        terminal_state=terminal_state,
        signal_name=signal_name,
    )


async def _stop_process_if_launch_is_no_longer_current(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    launch_context: CommandRunLaunchContext,
    *,
    release_fd: int | None,
) -> bool:
    current_state = await read_current_command_run_state(
        state.session_factory,
        task_id=record.task_id,
        run_id=record.run_id,
    )
    if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
        close_process_start_gate(release_fd)
        signal_name = await stop_process(process)
        await record_runner_command_run_terminal(
            state.session_factory,
            record,
            state=CommandRunState.CANCELLED,
            summary=COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY,
            exit_code=None,
            signal_name=signal_name,
            log_ref=launch_context.log_ref,
        )
        return True
    if current_state is None:
        close_process_start_gate(release_fd)
        await stop_process(process)
        raise asyncio.CancelledError
    return False


async def _record_process_ownership_or_stop(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    launch_context: CommandRunLaunchContext,
    *,
    release_fd: int | None,
    process_started_at: datetime,
) -> bool:
    owned_process_recorded = await record_runner_owned_process_pid(
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
        close_process_start_gate(release_fd)
        signal_name = await stop_process(process)
        if current_state == CommandRunState.CANCELLATION_REQUESTED.value:
            await record_runner_command_run_terminal(
                state.session_factory,
                record,
                state=CommandRunState.CANCELLED,
                summary=COMMAND_RUN_LOCAL_LAUNCH_CANCELLED_SUMMARY,
                exit_code=None,
                signal_name=signal_name,
                log_ref=launch_context.log_ref,
            )
            return False
        raise asyncio.CancelledError
    return True


async def _wait_for_recorded_process_completion(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    launch_context: CommandRunLaunchContext,
    *,
    process_started_at: datetime,
) -> tuple[bool, CommandRunTerminalState, str | None]:
    process_deadline = (
        asyncio.get_running_loop().time() + record.timeout_seconds
        if record.timeout_seconds is not None
        else None
    )
    reader_task = asyncio.create_task(
        copy_process_output_to_log(process, launch_context.log_path),
        name=f"command-run-log:{record.run_id}",
    )
    progress_recorded = await record_runner_command_run_progress(
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
    return progress_recorded, terminal_state, signal_name


async def _record_completed_process_terminal(
    state: CommandRunRunnerState,
    record: CurrentCommandRun,
    process: asyncio.subprocess.Process,
    launch_context: CommandRunLaunchContext,
    *,
    terminal_state: CommandRunTerminalState,
    signal_name: str | None,
) -> None:
    returncode = process.returncode
    summary = (
        await resolve_cancelled_command_run_summary(state.session_factory, task_id=record.task_id)
        if terminal_state == CommandRunState.CANCELLED
        else command_run_terminal_summary(
            terminal_state,
            returncode=returncode,
            signal_name=signal_name,
            timeout_seconds=record.timeout_seconds,
        )
    )
    await record_runner_command_run_terminal(
        state.session_factory,
        record,
        state=terminal_state,
        summary=summary,
        exit_code=command_run_terminal_exit_code(terminal_state, returncode),
        signal_name=signal_name,
        log_ref=launch_context.log_ref,
    )


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
