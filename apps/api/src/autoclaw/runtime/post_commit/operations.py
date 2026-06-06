from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.post_commit.worker import (
    commit_runtime_session,
    rollback_runtime_session,
    wait_for_runtime_effects,
)
from autoclaw.runtime.post_commit.writes import DeferredRuntimeWrite, commit_runtime_write

ResultT = TypeVar("ResultT")


async def read_session_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    session: AsyncSession | None = None,
) -> ResultT:
    return await _run_with_session(operation, session=session)


async def write_session_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    session: AsyncSession | None = None,
) -> ResultT:
    async def _write(active_session: AsyncSession) -> ResultT:
        try:
            result = await operation(active_session)
            await active_session.commit()
            return result
        except Exception:
            await active_session.rollback()
            raise

    return await _run_with_session(_write, session=session)


async def write_runtime_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT | DeferredRuntimeWrite[ResultT]]],
    *,
    session: AsyncSession | None = None,
) -> ResultT:
    async def _write(active_session: AsyncSession) -> ResultT:
        return await commit_runtime_write(
            active_session,
            lambda: operation(active_session),
        )

    return await _run_with_session(_write, session=session)


async def write_runtime_operation_and_wait(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    task_id_getter: Callable[[ResultT], str],
    session: AsyncSession | None = None,
) -> ResultT:
    async def _write(active_session: AsyncSession) -> ResultT:
        try:
            result = await operation(active_session)
            await commit_runtime_session(active_session)
            await wait_for_runtime_effects(task_id=task_id_getter(result))
            return result
        except Exception:
            await rollback_runtime_session(active_session)
            raise

    return await _run_with_session(_write, session=session)


async def _run_with_session(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    session: AsyncSession | None,
) -> ResultT:
    if session is not None:
        return await operation(session)

    from autoclaw.persistence.session import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as owned_session:
        return await operation(owned_session)


__all__ = [
    "read_session_operation",
    "write_runtime_operation",
    "write_runtime_operation_and_wait",
    "write_session_operation",
]
