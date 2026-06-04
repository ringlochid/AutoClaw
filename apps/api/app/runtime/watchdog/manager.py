from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
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
    reconcile_lock: asyncio.Lock
    stop_requested: bool
    task: asyncio.Task[None] | None


async def drive_watchdog_until(
    predicate: Callable[[], bool | Awaitable[bool]],
    *,
    max_cycles: int = 20,
) -> None:
    if await _watchdog_predicate_value(predicate):
        return
    for _ in range(max_cycles):
        await drive_watchdog_once()
        if await _watchdog_predicate_value(predicate):
            return
    raise AssertionError("watchdog predicate did not become true within the allotted cycles")


async def drive_watchdog_once() -> bool:
    state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        await start_runtime_watchdog()
        state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        return False
    async with state.reconcile_lock:
        return await reconcile_watchdog_truth(state.session_factory)


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


async def stop_all_runtime_watchdogs() -> None:
    states = tuple(_MANAGER_BY_LOOP.values())
    _MANAGER_BY_LOOP.clear()
    for state in states:
        await _stop_runtime_watchdog_state(state)


async def stop_runtime_watchdog() -> None:
    await _stop_runtime_watchdog_state(_MANAGER_BY_LOOP.pop(_loop_id(), None))


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
        reconcile_lock=asyncio.Lock(),
        stop_requested=False,
        task=None,
    )
    state.task = asyncio.create_task(_run_runtime_watchdog(state), name="runtime-watchdog")
    _MANAGER_BY_LOOP[loop_id] = state
    state.wakeup.set()
    await state.started.wait()


def notify_runtime_watchdog() -> None:
    state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    state.idle.clear()
    state.wakeup.set()


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


async def _stop_runtime_watchdog_state(state: _RuntimeWatchdogManagerState | None) -> None:
    if state is None or state.task is None:
        return
    state.stop_requested = True
    task = state.task
    current_loop = asyncio.get_running_loop()
    if task.get_loop() is not current_loop:
        if task.get_loop().is_closed() or task.done():
            return
        try:
            task.get_loop().call_soon_threadsafe(task.cancel)
        except RuntimeError:
            LOGGER.warning("failed to cancel runtime watchdog on a foreign event loop")
        return
    if task.done():
        await task
        return
    state.wakeup.set()
    await task


async def _run_runtime_watchdog(state: _RuntimeWatchdogManagerState) -> None:
    interval_seconds = max(0.25, float(get_settings().runtime.watchdog_interval_seconds))
    state.started.set()
    try:
        while not state.stop_requested:
            state.idle.clear()
            async with state.reconcile_lock:
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


async def _watchdog_predicate_value(
    predicate: Callable[[], bool | Awaitable[bool]],
) -> bool:
    value = predicate()
    if isinstance(value, bool):
        return value
    return bool(await value)


__all__ = [
    "drive_watchdog_once",
    "drive_watchdog_until",
    "notify_runtime_watchdog",
    "start_runtime_watchdog",
    "stop_all_runtime_watchdogs",
    "stop_runtime_watchdog",
    "wait_for_runtime_watchdog",
]
