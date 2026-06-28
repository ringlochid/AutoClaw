from __future__ import annotations

import asyncio
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.runtime.contracts import CommandRunState

from .discovery import CurrentCommandRun
from .logs import write_command_run_log_line
from .paths import resolve_command_run_paths
from .persistence import record_runner_command_run_terminal

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


@dataclass(frozen=True)
class CommandRunLaunchContext:
    log_ref: str
    log_path: Path
    workdir: Path


async def prepare_command_run_launch(
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
    await record_runner_command_run_terminal(
        session_factory,
        record,
        state=CommandRunState.FAILED,
        summary=f"command failed to launch because workdir does not exist: {workdir}",
        exit_code=None,
        signal_name=None,
        log_ref=log_ref,
    )
    return None


async def start_command_run_process(
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


def release_process_start_gate(release_fd: int | None) -> None:
    if release_fd is None:
        return
    try:
        os.write(release_fd, b"1")
    finally:
        close_process_start_gate(release_fd)


def close_process_start_gate(release_fd: int | None) -> None:
    if release_fd is None:
        return
    try:
        os.close(release_fd)
    except OSError:
        return


__all__ = [
    "CommandRunLaunchContext",
    "close_process_start_gate",
    "prepare_command_run_launch",
    "release_process_start_gate",
    "start_command_run_process",
]
