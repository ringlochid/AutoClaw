from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.effects.worker import commit_runtime_session, rollback_runtime_session

T = TypeVar("T")


async def run_runtime_write(
    session: AsyncSession,
    operation: Callable[[], Awaitable[T]],
) -> T:
    try:
        result = await operation()
        await commit_runtime_session(session)
        return result
    except Exception:
        await rollback_runtime_session(session)
        raise


__all__ = ["run_runtime_write"]
