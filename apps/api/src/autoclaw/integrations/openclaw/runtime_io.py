from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from autoclaw.persistence.session import get_session_factory
from autoclaw.runtime.post_commit import (
    commit_runtime_session,
    commit_runtime_write,
    rollback_runtime_session,
    wait_for_runtime_effects,
)

ResultT = TypeVar("ResultT")


async def read_openclaw_operation(
    operation: Callable[..., Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await operation(session)


async def write_openclaw_operation(
    operation: Callable[..., Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def write_openclaw_runtime_operation(
    operation: Callable[..., Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await commit_runtime_write(
            session,
            lambda: operation(session),
        )


async def write_openclaw_runtime_operation_and_wait(
    operation: Callable[..., Awaitable[ResultT]],
    *,
    task_id_getter: Callable[[ResultT], str],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await commit_runtime_session(session)
            await wait_for_runtime_effects(task_id=task_id_getter(result))
            return result
        except Exception:
            await rollback_runtime_session(session)
            raise


__all__ = [
    "read_openclaw_operation",
    "write_openclaw_operation",
    "write_openclaw_runtime_operation",
    "write_openclaw_runtime_operation_and_wait",
]
