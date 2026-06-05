from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.post_commit.worker import commit_runtime_session, rollback_runtime_session

T = TypeVar("T")


@dataclass(frozen=True)
class DeferredRuntimeWrite[T]:
    read_after_commit: Callable[[], Awaitable[T]]


async def commit_runtime_write(
    session: AsyncSession,
    operation: Callable[[], Awaitable[T | DeferredRuntimeWrite]],
) -> T:
    try:
        result = await operation()
        await commit_runtime_session(session)
        if isinstance(result, DeferredRuntimeWrite):
            return cast(T, await result.read_after_commit())
        return result
    except Exception:
        await rollback_runtime_session(session)
        raise


__all__ = ["DeferredRuntimeWrite", "commit_runtime_write"]
