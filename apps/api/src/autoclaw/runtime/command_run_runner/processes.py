from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path

from autoclaw.runtime.command_run_runner.logs import (
    COMMAND_RUN_LOG_CHUNK_BYTES,
    append_command_run_log_bytes,
)
from autoclaw.runtime.contracts import CommandRunState

_PROCESS_STOP_GRACE_SECONDS = 1.0


async def copy_process_output_to_log(
    process: asyncio.subprocess.Process,
    log_path: Path,
) -> None:
    if process.stdout is None:
        return
    while True:
        chunk = await process.stdout.read(COMMAND_RUN_LOG_CHUNK_BYTES)
        if not chunk:
            return
        await append_command_run_log_bytes(log_path, chunk)


async def stop_process(process: asyncio.subprocess.Process) -> str | None:
    if process.returncode is not None:
        return signal_name_from_returncode(process.returncode)

    signal_name = _terminate_process_group(process)
    try:
        await asyncio.wait_for(process.wait(), timeout=_PROCESS_STOP_GRACE_SECONDS)
        return signal_name_from_returncode(process.returncode) or signal_name
    except TimeoutError:
        signal_name = _kill_process_group(process)
        await process.wait()
        return signal_name_from_returncode(process.returncode) or signal_name


def command_run_terminal_summary(
    terminal_state: CommandRunState,
    *,
    returncode: int | None,
    signal_name: str | None,
    timeout_seconds: int | None,
) -> str:
    if terminal_state == CommandRunState.SUCCEEDED:
        return "command succeeded with exit code 0"
    if terminal_state == CommandRunState.TIMED_OUT:
        timeout_text = (
            "declared timeout" if timeout_seconds is None else f"{timeout_seconds} seconds"
        )
        return f"command timed out after {timeout_text}"
    if terminal_state == CommandRunState.CANCELLED:
        return "command run cancelled after accepted cancellation request"
    if signal_name is not None:
        return f"command failed after signal {signal_name}"
    return f"command failed with exit code {returncode}"


def command_run_terminal_exit_code(
    terminal_state: CommandRunState,
    returncode: int | None,
) -> int | None:
    if terminal_state not in {CommandRunState.SUCCEEDED, CommandRunState.FAILED}:
        return None
    if returncode is None or returncode < 0:
        return None
    return returncode


def signal_name_from_returncode(returncode: int | None) -> str | None:
    if returncode is None or returncode >= 0:
        return None
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return f"signal {-returncode}"


def _terminate_process_group(process: asyncio.subprocess.Process) -> str:
    if hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            return "SIGTERM"
        except ProcessLookupError:
            return "SIGTERM"
    process.terminate()
    return "SIGTERM"


def _kill_process_group(process: asyncio.subprocess.Process) -> str:
    if hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return "SIGKILL"
        except ProcessLookupError:
            return "SIGKILL"
    process.kill()
    return "SIGKILL"


__all__ = [
    "command_run_terminal_exit_code",
    "command_run_terminal_summary",
    "copy_process_output_to_log",
    "signal_name_from_returncode",
    "stop_process",
]
