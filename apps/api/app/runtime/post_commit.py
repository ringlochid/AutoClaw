from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

_QUEUE_KEY = "runtime_post_commit_actions"
_SEEN_KEY = "runtime_post_commit_seen_keys"


@dataclass(frozen=True)
class _QueuedAction:
    key: tuple[str, ...]
    runner: Callable[[AsyncSession], Awaitable[None]]


def _queue(session: AsyncSession) -> list[_QueuedAction]:
    return cast(list[_QueuedAction], session.info.setdefault(_QUEUE_KEY, []))


def _seen_keys(session: AsyncSession) -> set[tuple[str, ...]]:
    return cast(set[tuple[str, ...]], session.info.setdefault(_SEEN_KEY, set()))


def queue_post_commit_action(
    session: AsyncSession,
    *,
    key: tuple[str, ...],
    runner: Callable[[AsyncSession], Awaitable[None]],
) -> None:
    seen_keys = _seen_keys(session)
    if key in seen_keys:
        return
    seen_keys.add(key)
    _queue(session).append(_QueuedAction(key=key, runner=runner))


def clear_post_commit_actions(session: AsyncSession) -> None:
    session.info.pop(_QUEUE_KEY, None)
    session.info.pop(_SEEN_KEY, None)


async def run_post_commit_actions(session: AsyncSession) -> None:
    while True:
        queued = list(_queue(session))
        if not queued:
            clear_post_commit_actions(session)
            return
        clear_post_commit_actions(session)
        for action in queued:
            await action.runner(session)


async def commit_runtime_session(session: AsyncSession) -> None:
    await session.commit()
    await run_post_commit_actions(session)


async def rollback_runtime_session(session: AsyncSession) -> None:
    clear_post_commit_actions(session)
    await session.rollback()
