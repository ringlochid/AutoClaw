from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import DispatchTurnModel, FlowModel
from app.runtime.contracts import FlowStatus
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch import control as dispatch_control
from app.runtime.control.dispatch import gateway as dispatch_gateway
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
    state.idle.clear()
    notify_runtime_effect_runner()
    if task_id is not None and not await _task_pending_reconcile(state.session_factory, task_id):
        return
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while True:
        if task_id is None and state.idle.is_set():
            return
        if task_id is not None and not await _task_pending_reconcile(
            state.session_factory, task_id
        ):
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
                if dispatch.control_state in {"fenced", "ambiguous"}:
                    pending = False
                elif dispatch_control.dispatch_deadline_expired(dispatch):
                    await _mark_gateway_wait_ambiguous(session, task_id=task_id, dispatch=dispatch)
                    changed = True
                elif dispatch_control.dispatch_inactivity_proven(dispatch) and (
                    dispatch_control.dispatch_waiting_for_inactivity(dispatch)
                    or dispatch.control_state == "abort_requested"
                ):
                    await dispatch_control.fence_foreground_dispatch(
                        session,
                        task_id=task_id,
                        flow=flow,
                        dispatch=dispatch,
                    )
                    changed = True
                elif _dispatch_requires_lifecycle_reconcile(dispatch):
                    task_pending, task_changed = await _reconcile_gateway_dispatch(
                        session,
                        task_id=task_id,
                        flow=flow,
                        dispatch=dispatch,
                    )
                    pending = task_pending
                    changed = changed or task_changed
            if changed:
                await commit_runtime_session(session)
            return pending
    except Exception:
        LOGGER.exception("foreground lifecycle reconciliation failed for task %s", task_id)
        return False


async def _task_pending_reconcile(
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None or flow.current_open_dispatch_id is None:
            return False
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        return dispatch is not None and _dispatch_requires_lifecycle_reconcile(dispatch)


def _dispatch_requires_lifecycle_reconcile(dispatch: DispatchTurnModel) -> bool:
    return dispatch.control_state not in {"fenced", "ambiguous"} and (
        dispatch_control.dispatch_deadline_expired(dispatch)
        or dispatch_control.dispatch_waiting_for_inactivity(dispatch)
        or dispatch.control_state == "abort_requested"
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
    from app.runtime.watchdog import notify_runtime_watchdog

    notify_runtime_watchdog()


async def rollback_runtime_session(session: AsyncSession) -> None:
    clear_post_commit_actions(session)
    await session.rollback()


async def _reconcile_gateway_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> tuple[bool, bool]:
    changed = False
    if dispatch.control_state == "abort_requested":
        try:
            changed = (
                await dispatch_gateway.abort_gateway_dispatch(session, dispatch=dispatch) or changed
            )
        except Exception as exc:
            changed = await _record_gateway_operation_failure(
                session,
                task_id=task_id,
                dispatch=dispatch,
                operation="sessions.abort",
                error=exc,
            )
            return True, changed
    if dispatch.gateway_run_id is None:
        return True, changed
    try:
        wait_result = await dispatch_gateway.wait_for_gateway_dispatch(
            dispatch=dispatch,
            timeout_ms=_gateway_wait_timeout_ms(dispatch),
        )
    except Exception as exc:
        changed = await _record_gateway_operation_failure(
            session,
            task_id=task_id,
            dispatch=dispatch,
            operation="agent.wait",
            error=exc,
        )
        return True, changed
    if wait_result.status.value == "timeout":
        if dispatch_control.dispatch_deadline_expired(dispatch):
            await _mark_gateway_wait_ambiguous(session, task_id=task_id, dispatch=dispatch)
            return False, True
        return True, changed
    await dispatch_gateway.record_gateway_wait_terminal(
        session, dispatch=dispatch, wait_result=wait_result
    )
    await dispatch_control.fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    )
    return False, True


async def _mark_gateway_wait_ambiguous(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    reason = dispatch.control_state_reason or "foreground_dispatch"
    await dispatch_gateway.record_gateway_wait_timeout(
        session,
        dispatch=dispatch,
        detail=f"{reason}:timed_out",
    )
    await dispatch_control.mark_dispatch_ambiguous(
        session,
        dispatch=dispatch,
        reason=f"{reason}:timed_out",
    )
    stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)


async def _record_gateway_operation_failure(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    operation: str,
    error: Exception,
) -> bool:
    changed = await dispatch_gateway.record_gateway_transport_failure(
        session,
        dispatch=dispatch,
        operation=operation,
        error=error,
    )
    if changed:
        stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)
    return changed


def _gateway_wait_timeout_ms(dispatch: DispatchTurnModel) -> int:
    deadline = dispatch.control_deadline_at
    if deadline is None:
        return int(_POLL_INTERVAL_SECONDS * 1000)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    remaining_ms = max(1, int((deadline - utc_now()).total_seconds() * 1000))
    return min(int(_POLL_INTERVAL_SECONDS * 1000), remaining_ms)


__all__ = [
    "RuntimeLifecycleManagerState",
    "commit_runtime_session",
    "notify_runtime_effect_runner",
    "rollback_runtime_session",
    "start_runtime_effect_runner",
    "stop_runtime_effect_runner",
    "wait_for_runtime_effects",
]
