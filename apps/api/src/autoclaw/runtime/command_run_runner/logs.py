from __future__ import annotations

import asyncio
import re
from pathlib import Path

COMMAND_RUN_LOG_CHUNK_BYTES = 8192

_LOG_REF_SAFE_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")


def command_run_log_ref(run_id: str) -> str:
    safe_run_id = _LOG_REF_SAFE_CHARS.sub("_", run_id).strip("._-") or "command-run"
    return f"outputs/command-runs/{safe_run_id}.log"


async def write_command_run_log_line(path: Path, line: str) -> None:
    await append_command_run_log_bytes(path, f"{line}\n".encode("utf-8", errors="replace"))


async def append_command_run_log_bytes(path: Path, chunk: bytes) -> None:
    if not chunk:
        return
    await asyncio.to_thread(_append_log_bytes, path, chunk)


def _append_log_bytes(path: Path, chunk: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(chunk)


__all__ = [
    "COMMAND_RUN_LOG_CHUNK_BYTES",
    "append_command_run_log_bytes",
    "command_run_log_ref",
    "write_command_run_log_line",
]
