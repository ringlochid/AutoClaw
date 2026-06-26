from __future__ import annotations

import asyncio
import re
from pathlib import Path

MAX_COMMAND_RUN_LOG_BYTES = 1024 * 1024
COMMAND_RUN_LOG_CHUNK_BYTES = 8192

_LOG_REF_SAFE_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")
_LOG_TRUNCATION_NOTICE = b"\n[command log truncated; additional output omitted]\n"
_LOG_DATA_BYTES = MAX_COMMAND_RUN_LOG_BYTES - len(_LOG_TRUNCATION_NOTICE)


def command_run_log_ref(run_id: str) -> str:
    safe_run_id = _LOG_REF_SAFE_CHARS.sub("_", run_id).strip("._-") or "command-run"
    return f"outputs/command-runs/{safe_run_id}.log"


async def write_command_run_log_line(path: Path, line: str) -> None:
    await append_command_run_log_bytes(path, f"{line}\n".encode("utf-8", errors="replace"))


async def append_command_run_log_bytes(path: Path, chunk: bytes) -> None:
    if not chunk:
        return
    await asyncio.to_thread(_append_log_bytes_with_cap, path, chunk)


def _append_log_bytes_with_cap(path: Path, chunk: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_size = path.stat().st_size if path.exists() else 0
    if existing_size >= MAX_COMMAND_RUN_LOG_BYTES:
        return

    with path.open("ab") as handle:
        if existing_size < _LOG_DATA_BYTES:
            remaining_data_bytes = _LOG_DATA_BYTES - existing_size
            data_chunk = chunk[:remaining_data_bytes]
            handle.write(data_chunk)
            existing_size += len(data_chunk)
            if len(data_chunk) == len(chunk):
                return

        remaining_notice_bytes = MAX_COMMAND_RUN_LOG_BYTES - existing_size
        if remaining_notice_bytes > 0:
            handle.write(_LOG_TRUNCATION_NOTICE[:remaining_notice_bytes])


__all__ = [
    "COMMAND_RUN_LOG_CHUNK_BYTES",
    "MAX_COMMAND_RUN_LOG_BYTES",
    "append_command_run_log_bytes",
    "command_run_log_ref",
    "write_command_run_log_line",
]
