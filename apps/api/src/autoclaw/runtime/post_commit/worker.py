from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.config import get_settings
from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.contracts import FlowStatus
from autoclaw.runtime.dispatch.openclaw.lifecycle import close_dispatch_runtime
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.post_commit.dispatch_progression import auto_open_next_running_dispatch
from autoclaw.runtime.post_commit.queue import clear_post_commit_actions, pop_post_commit_actions
from autoclaw.runtime.post_commit.task_reconcile import (
    load_current_dispatch,
    reconcile_current_dispatch,
    reconcile_lingering_boundary_dispatch,
)
from autoclaw.runtime.post_commit.task_reconcile_state import (
    runtime_predicate_value,
    task_pending_reconcile,
)

LOGGER = logging.getLogger(__name__)
_MANAGER_BY_LOOP: dict[int, RuntimeLifecycleManagerState] = {}
_MIN_POST_COMMIT_RECONCILE_INTERVAL_SECONDS = 0.01


@dataclass
class RuntimeLifecycleManagerState:
    session_factory: async_sessionmaker[AsyncSession]
    wakeup: asyncio.Event
    idle: asyncio.Event
    started: asyncio.Event
    cycle_completed: asyncio.Event
    reconcile_lock: asyncio.Lock
    should_stop: bool
    task: asyncio.Task[None] | None


async def wait_for_runtime_effects(
    *,
    task_id: str | None = None,
    max_wait_seconds: float = 5.0,
) -> None:
    state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        await start_runtime_effect_runner()
        state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    if task_id is None:
        await _wait_for_runtime_drain(state, deadline=deadline)
        return

    while True:
        if not await task_pending_reconcile(state.session_factory, task_id):
            return
        if not await _wait_for_task_reconcile_cycle(state, deadline=deadline):
            return


async def drive_runtime_until(
    predicate: Callable[[], bool | Awaitable[bool]],
    *,
    task_id: str | None = None,
    max_cycles: int = 20,
) -> None:
    if await runtime_predicate_value(predicate):
        return
    for _ in range(max_cycles):
        await drive_runtime_once(task_id=task_id)
        if await runtime_predicate_value(predicate):
            return
    raise AssertionError("runtime predicate did not become true within the allotted cycles")


async def commit_runtime_session(session: AsyncSession) -> None:
    staged_actions = pop_post_commit_actions(session)
    session.info.setdefault("_pre_popped_post_commit_actions", staged_actions)
    try:
        await session.commit()
    except Exception:
        clear_post_commit_actions(session)
        session.info.pop("_pre_popped_post_commit_actions", None)
        raise
    session.info.pop("_pre_popped_post_commit_actions", None)
    notify_runtime_effect_runner()
    from autoclaw.runtime.watchdog import notify_runtime_watchdog

    notify_runtime_watchdog()


async def rollback_runtime_session(session: AsyncSession) -> None:
    clear_post_commit_actions(session)
    await session.rollback()


async def drive_runtime_once(*, task_id: str | None = None) -> bool:
    state = _ensure_manager_started()
    async with state.reconcile_lock:
        if task_id is None:
            return await _reconcile_pending_runtime_truth(state.session_factory)
        return await _reconcile_task(state.session_factory, task_id)


async def start_runtime_effect_runner() -> None:
    state = _ensure_manager_started()
    await state.started.wait()


async def stop_runtime_effect_runner() -> None:
    await stop_runtime_lifecycle_manager_state(_MANAGER_BY_LOOP.pop(_loop_id(), None))


async def stop_all_runtime_effect_runners() -> None:
    states = tuple(_MANAGER_BY_LOOP.values())
    _MANAGER_BY_LOOP.clear()
    for state in states:
        await stop_runtime_lifecycle_manager_state(state)


async def stop_runtime_lifecycle_manager_state(
    state: RuntimeLifecycleManagerState | None,
) -> None:
    if state is None or state.task is None:
        return
    state.should_stop = True
    task = state.task
    current_loop = asyncio.get_running_loop()
    if task.get_loop() is not current_loop:
        if task.get_loop().is_closed() or task.done():
            return
        try:
            task.get_loop().call_soon_threadsafe(task.cancel)
        except RuntimeError:
            LOGGER.warning("failed to cancel runtime lifecycle manager on a foreign event loop")
        return
    if task.done():
        await task
        return
    state.wakeup.set()
    await task


def notify_runtime_effect_runner() -> None:
    state = _ensure_manager_started()
    state.idle.clear()
    state.wakeup.set()


async def _wait_for_runtime_drain(
    state: RuntimeLifecycleManagerState,
    *,
    deadline: float,
) -> bool:
    loop = asyncio.get_running_loop()
    state.idle.clear()
    notify_runtime_effect_runner()
    remaining = deadline - loop.time()
    if remaining <= 0:
        return False
    try:
        await asyncio.wait_for(state.idle.wait(), timeout=remaining)
    except TimeoutError:
        return False
    return True


async def _wait_for_task_reconcile_cycle(
    state: RuntimeLifecycleManagerState,
    *,
    deadline: float,
) -> bool:
    loop = asyncio.get_running_loop()
    cycle_completed = state.cycle_completed
    state.idle.clear()
    notify_runtime_effect_runner()
    remaining = deadline - loop.time()
    if remaining <= 0:
        return False
    try:
        await asyncio.wait_for(cycle_completed.wait(), timeout=remaining)
    except TimeoutError:
        return False
    return True


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


def _ensure_manager_started() -> RuntimeLifecycleManagerState:
    loop_id = _loop_id()
    state = _MANAGER_BY_LOOP.get(loop_id)
    if state is not None and state.task is not None and not state.task.done():
        return state

    from autoclaw.persistence.session import get_session_factory

    wakeup = asyncio.Event()
    idle = asyncio.Event()
    started = asyncio.Event()
    cycle_completed = asyncio.Event()
    state = RuntimeLifecycleManagerState(
        session_factory=get_session_factory(),
        wakeup=wakeup,
        idle=idle,
        started=started,
        cycle_completed=cycle_completed,
        reconcile_lock=asyncio.Lock(),
        should_stop=False,
        task=None,
    )
    state.task = asyncio.create_task(
        _run_runtime_lifecycle_manager(state), name="runtime-lifecycle-manager"
    )
    _MANAGER_BY_LOOP[loop_id] = state
    return state


async def _run_runtime_lifecycle_manager(state: RuntimeLifecycleManagerState) -> None:
    try:
        state.started.set()
        pending = False
        reconcile_interval_seconds = _post_commit_reconcile_interval_seconds()
        state.idle.set()
        while not state.should_stop:
            try:
                if not state.wakeup.is_set():
                    await asyncio.wait_for(
                        state.wakeup.wait(),
                        timeout=(reconcile_interval_seconds if pending else None),
                    )
            except TimeoutError:
                pass
            finally:
                state.wakeup.clear()
            if state.should_stop:
                break
            state.idle.clear()
            async with state.reconcile_lock:
                pending = await _reconcile_pending_runtime_truth(state.session_factory)
            completed_cycle = state.cycle_completed
            state.cycle_completed = asyncio.Event()
            completed_cycle.set()
            if not pending:
                state.idle.set()
    except Exception:  # pragma: no cover - background safety net
        LOGGER.exception("runtime lifecycle manager stopped unexpectedly")
    finally:
        state.started.set()
        state.idle.set()
        state.cycle_completed.set()


def _post_commit_reconcile_interval_seconds() -> float:
    return max(
        _MIN_POST_COMMIT_RECONCILE_INTERVAL_SECONDS,
        float(get_settings().runtime.post_commit_reconcile_interval_seconds),
    )


async def _reconcile_pending_runtime_truth(
    session_factory: async_sessionmaker[AsyncSession],
) -> bool:
    async with session_factory() as session:
        stmt = (
            select(FlowModel.task_id)
            .where(
                or_(
                    FlowModel.current_open_dispatch_id.is_not(None),
                    FlowModel.status.in_(
                        (
                            FlowStatus.RUNNING.value,
                            FlowStatus.PAUSED.value,
                        )
                    ),
                )
            )
            .distinct()
            .order_by(FlowModel.task_id)
        )

        task_ids = (await session.scalars(stmt)).all()

    pending = False

    for task_id in task_ids:
        changed = await _reconcile_task(session_factory, task_id)
        pending = changed or pending

    return pending


async def _reconcile_task(
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> bool:
    try:
        async with session_factory() as session:
            flow = await require_flow_for_task(session, task_id)
            pending = False
            changed = False
            dispatch: DispatchTurnModel | None = None
            dispatch, repaired_current_dispatch = await load_current_dispatch(
                session,
                flow=flow,
                task_id=task_id,
            )
            changed = repaired_current_dispatch
            if flow.current_open_dispatch_id is not None and dispatch is None:
                return False
            pending, changed = await reconcile_lingering_boundary_dispatch(
                session,
                flow=flow,
                task_id=task_id,
                current_open_dispatch_id=flow.current_open_dispatch_id,
                has_pending_runtime_work=pending,
                has_changed_runtime_truth=changed,
            )
            pending, changed = await reconcile_current_dispatch(
                session,
                flow=flow,
                task_id=task_id,
                dispatch=dispatch,
                has_pending_runtime_work=pending,
                has_changed_runtime_truth=changed,
            )
            if await auto_open_next_running_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                previous_dispatch=dispatch,
            ):
                changed = True
            if changed:
                await commit_runtime_session(session)
                if dispatch is not None and dispatch.control_state in {"fenced", "ambiguous"}:
                    await close_dispatch_runtime(dispatch.dispatch_id)
            return pending
    except Exception:
        LOGGER.exception("foreground lifecycle reconciliation failed for task %s", task_id)
        return False


__all__ = [
    "RuntimeLifecycleManagerState",
    "commit_runtime_session",
    "drive_runtime_once",
    "drive_runtime_until",
    "notify_runtime_effect_runner",
    "rollback_runtime_session",
    "start_runtime_effect_runner",
    "stop_all_runtime_effect_runners",
    "stop_runtime_effect_runner",
    "wait_for_runtime_effects",
]
