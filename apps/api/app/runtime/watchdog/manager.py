from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.runtime.watchdog.service import reconcile_watchdog_truth

LOGGER = logging.getLogger(__name__)
_MANAGER_BY_LOOP: dict[int, _RuntimeWatchdogManagerState] = {}


@dataclass
class _RuntimeWatchdogManagerState:
    session_factory: async_sessionmaker[AsyncSession]
    wakeup: asyncio.Event
    idle: asyncio.Event
    started: asyncio.Event
    stop_requested: bool
    task: asyncio.Task[None] | None


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


def notify_runtime_watchdog() -> None:
    state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    state.idle.clear()
    state.wakeup.set()


async def start_runtime_watchdog() -> None:
    if not get_settings().runtime.watchdog_enabled:
        return
    loop_id = _loop_id()
    state = _MANAGER_BY_LOOP.get(loop_id)
    if state is not None and state.task is not None and not state.task.done():
        await state.started.wait()
        return
    from app.db.session import get_session_factory

    state = _RuntimeWatchdogManagerState(
        session_factory=get_session_factory(),
        wakeup=asyncio.Event(),
        idle=asyncio.Event(),
        started=asyncio.Event(),
        stop_requested=False,
        task=None,
    )
    state.task = asyncio.create_task(_run_runtime_watchdog(state), name="runtime-watchdog")
    _MANAGER_BY_LOOP[loop_id] = state
    state.wakeup.set()
    await state.started.wait()


async def stop_runtime_watchdog() -> None:
    state = _MANAGER_BY_LOOP.pop(_loop_id(), None)
    if state is None or state.task is None:
        return
    state.stop_requested = True
    state.wakeup.set()
    await state.task


async def wait_for_runtime_watchdog(*, max_wait_seconds: float = 5.0) -> None:
    state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    state.idle.clear()
    state.wakeup.set()
    try:
        await asyncio.wait_for(state.idle.wait(), timeout=max_wait_seconds)
    except TimeoutError:
        return


async def _run_runtime_watchdog(state: _RuntimeWatchdogManagerState) -> None:
    interval_seconds = max(0.25, float(get_settings().runtime.watchdog_interval_seconds))
    state.started.set()
    try:
        while not state.stop_requested:
            state.idle.clear()
            await reconcile_watchdog_truth(state.session_factory)
            state.idle.set()
            try:
                await asyncio.wait_for(state.wakeup.wait(), timeout=interval_seconds)
            except TimeoutError:
                pass
            finally:
                state.wakeup.clear()
    except Exception:  # pragma: no cover - background safety net
        LOGGER.exception("runtime watchdog stopped unexpectedly")
    finally:
        state.started.set()
        state.idle.set()


__all__ = [
    "notify_runtime_watchdog",
    "start_runtime_watchdog",
    "stop_runtime_watchdog",
    "wait_for_runtime_watchdog",
]
