from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import DispatchTurnModel, FlowModel
from app.runtime.contracts import FlowStatus
from app.runtime.control.dispatch.control import (
    dispatch_deadline_expired,
    dispatch_waiting_for_inactivity,
    mark_dispatch_ambiguous,
)
from app.runtime.control.flow.queries import require_flow_for_task
from app.runtime.effects.cases import stage_dispatch_open_outputs
from app.runtime.effects.queue import clear_post_commit_actions, pop_post_commit_actions

LOGGER = logging.getLogger(__name__)
_MANAGER_BY_LOOP: dict[int, RuntimeLifecycleManagerState] = {}
_POLL_INTERVAL_SECONDS = 0.25


@dataclass
class RuntimeLifecycleManagerState:
    session_factory: async_sessionmaker[AsyncSession]
    wakeup: asyncio.Event
    idle: asyncio.Event
    started: asyncio.Event
    stop_requested: bool
    task: asyncio.Task[None] | None


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


def _ensure_manager_started() -> RuntimeLifecycleManagerState:
    loop_id = _loop_id()
    state = _MANAGER_BY_LOOP.get(loop_id)
    if state is not None and state.task is not None and not state.task.done():
        return state

    from app.db.session import get_session_factory

    wakeup = asyncio.Event()
    idle = asyncio.Event()
    started = asyncio.Event()
    state = RuntimeLifecycleManagerState(
        session_factory=get_session_factory(),
        wakeup=wakeup,
        idle=idle,
        started=started,
        stop_requested=False,
        task=None,
    )
    state.task = asyncio.create_task(
        _run_runtime_lifecycle_manager(state), name="runtime-lifecycle-manager"
    )
    _MANAGER_BY_LOOP[loop_id] = state
    state.wakeup.set()
    return state


def notify_runtime_effect_runner() -> None:
    state = _ensure_manager_started()
    state.idle.clear()
    state.wakeup.set()


async def start_runtime_effect_runner() -> None:
    state = _ensure_manager_started()
    await state.started.wait()


async def stop_runtime_effect_runner() -> None:
    state = _MANAGER_BY_LOOP.pop(_loop_id(), None)
    if state is None or state.task is None:
        return
    state.stop_requested = True
    state.wakeup.set()
    await state.task


async def wait_for_runtime_effects(
    *,
    task_id: str | None = None,
    max_wait_seconds: float = 5.0,
) -> None:
    state = _MANAGER_BY_LOOP.get(_loop_id())
    if state is None:
        return
    baseline = (
        None
        if task_id is None
        else await _task_lifecycle_snapshot(state.session_factory, task_id)
    )
    state.idle.clear()
    notify_runtime_effect_runner()
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while True:
        if state.idle.is_set():
            return
        if task_id is not None:
            current = await _task_lifecycle_snapshot(state.session_factory, task_id)
            if current != baseline:
                return
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return
        try:
            await asyncio.wait_for(
                state.idle.wait(),
                timeout=min(_POLL_INTERVAL_SECONDS, remaining),
            )
        except TimeoutError:
            if task_id is None:
                return


async def _run_runtime_lifecycle_manager(state: RuntimeLifecycleManagerState) -> None:
    try:
        state.started.set()
        while not state.stop_requested:
            pending = await _reconcile_pending_runtime_truth(state.session_factory)
            if not pending:
                state.idle.set()
            try:
                await asyncio.wait_for(
                    state.wakeup.wait(),
                    timeout=(_POLL_INTERVAL_SECONDS if pending else None),
                )
            except TimeoutError:
                pass
            finally:
                state.wakeup.clear()
                state.idle.clear()
    except Exception:  # pragma: no cover - background safety net
        LOGGER.exception("runtime lifecycle manager stopped unexpectedly")
    finally:
        state.started.set()
        state.idle.set()


async def _reconcile_pending_runtime_truth(
    session_factory: async_sessionmaker[AsyncSession],
) -> bool:
    async with session_factory() as session:
        task_ids = tuple(
            sorted(
                set(
                    await session.scalars(
                        select(FlowModel.task_id).where(
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
                    )
                )
            )
        )
    pending = False
    for task_id in task_ids:
        pending = await _reconcile_task(session_factory, task_id) or pending
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
            if flow.current_open_dispatch_id is not None:
                dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
                if dispatch is None:
                    LOGGER.warning(
                        "missing current dispatch %s for task %s during lifecycle reconciliation",
                        flow.current_open_dispatch_id,
                        task_id,
                    )
                    return False
                if dispatch.control_state == "fenced":
                    pending = False
                elif dispatch_deadline_expired(dispatch):
                    reason = dispatch.control_state_reason or "foreground_dispatch"
                    await mark_dispatch_ambiguous(
                        session,
                        dispatch=dispatch,
                        reason=f"{reason}:timed_out",
                    )
                    stage_dispatch_open_outputs(
                        session,
                        task_id=task_id,
                        dispatch_id=dispatch.dispatch_id,
                    )
                    changed = True
                elif (
                    dispatch_waiting_for_inactivity(dispatch)
                    or dispatch.control_state == "abort_requested"
                ):
                    pending = True
                elif dispatch.control_state == "ambiguous":
                    pending = False
            if changed:
                await commit_runtime_session(session)
            return pending
    except Exception:
        LOGGER.exception("foreground lifecycle reconciliation failed for task %s", task_id)
        return False


async def _task_lifecycle_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> tuple[str | None, str | None, str | None, bool, str | None, bool] | None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None or flow.current_open_dispatch_id is None:
            return None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        if dispatch is None:
            return None
        return (
            flow.current_open_dispatch_id,
            dispatch.control_state,
            dispatch.accepted_boundary,
            dispatch.fenced_at is not None,
            dispatch.delivery_status,
            dispatch_deadline_expired(dispatch),
        )


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


async def rollback_runtime_session(session: AsyncSession) -> None:
    clear_post_commit_actions(session)
    await session.rollback()


__all__ = [
    "RuntimeLifecycleManagerState",
    "commit_runtime_session",
    "notify_runtime_effect_runner",
    "rollback_runtime_session",
    "start_runtime_effect_runner",
    "stop_runtime_effect_runner",
    "wait_for_runtime_effects",
]
