from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from autoclaw.integrations.openclaw import runtime_io as openclaw_runtime_io

ResultT = TypeVar("ResultT")


async def read_openclaw_operation(
    operation: Callable[..., Awaitable[ResultT]],
) -> ResultT:
    return await openclaw_runtime_io.read_openclaw_operation(operation)


async def write_openclaw_operation(
    operation: Callable[..., Awaitable[ResultT]],
) -> ResultT:
    return await openclaw_runtime_io.write_openclaw_operation(operation)


async def write_openclaw_runtime_operation(
    operation: Callable[..., Awaitable[ResultT]],
) -> ResultT:
    return await openclaw_runtime_io.write_openclaw_runtime_operation(operation)


async def write_openclaw_runtime_operation_and_wait(
    operation: Callable[..., Awaitable[ResultT]],
    *,
    task_id_getter: Callable[[ResultT], str],
) -> ResultT:
    return await openclaw_runtime_io.write_openclaw_runtime_operation_and_wait(
        operation,
        task_id_getter=task_id_getter,
    )


__all__ = [
    "read_openclaw_operation",
    "write_openclaw_operation",
    "write_openclaw_runtime_operation",
    "write_openclaw_runtime_operation_and_wait",
]
