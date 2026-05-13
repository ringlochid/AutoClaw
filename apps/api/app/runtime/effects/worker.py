from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from time import monotonic
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.runtime.control.structural_manifest_sync as structural_manifest_sync
from app.db.models.runtime.common import utcnow
from app.db.models.runtime.effects import RuntimeEffectModel
from app.runtime.effects.keys import RuntimeEffectKind

_RUNNER_BY_LOOP: dict[int, RuntimeEffectRunnerState] = {}
_FAILED_RETRY_DELAY = timedelta(seconds=1)
_POLL_INTERVAL_SECONDS = 0.25


@dataclass(frozen=True)
class ClaimedEffect:
    runtime_effect_id: str
    requested_revision: int
    effect_kind: RuntimeEffectKind
    payload: dict[str, object]


@dataclass
class RuntimeEffectRunnerState:
    session_factory: async_sessionmaker[AsyncSession]
    wakeup: asyncio.Event
    idle: asyncio.Event
    started: asyncio.Event
    stop_requested: bool
    task: asyncio.Task[None] | None


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


async def _requeue_running_effects(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        running_effects = list(
            await session.scalars(
                select(RuntimeEffectModel).where(RuntimeEffectModel.effect_state == "running")
            )
        )
        if not running_effects:
            return
        now = utcnow()
        for effect in running_effects:
            effect.effect_state = "pending"
            effect.available_at = now
            effect.updated_at = now
        await session.commit()


async def _claim_next_effect(
    session_factory: async_sessionmaker[AsyncSession],
) -> ClaimedEffect | None:
    async with session_factory() as session:
        effect = await session.scalar(
            select(RuntimeEffectModel)
            .where(
                RuntimeEffectModel.requested_revision > RuntimeEffectModel.processed_revision,
                RuntimeEffectModel.effect_state != "running",
                RuntimeEffectModel.available_at <= utcnow(),
            )
            .order_by(
                RuntimeEffectModel.priority.asc(),
                RuntimeEffectModel.updated_at.asc(),
                RuntimeEffectModel.runtime_effect_id.asc(),
            )
        )
        if effect is None:
            return None
        effect.effect_state = "running"
        effect.started_at = utcnow()
        effect.attempt_count += 1
        effect.last_error = None
        effect.failed_at = None
        effect.updated_at = utcnow()
        claimed = ClaimedEffect(
            runtime_effect_id=effect.runtime_effect_id,
            requested_revision=effect.requested_revision,
            effect_kind=cast(RuntimeEffectKind, effect.effect_kind),
            payload=dict(effect.payload_json),
        )
        await session.commit()
        return claimed


async def _mark_effect_complete(
    session_factory: async_sessionmaker[AsyncSession],
    effect: ClaimedEffect,
) -> None:
    async with session_factory() as session:
        row = await session.get(RuntimeEffectModel, effect.runtime_effect_id)
        if row is None:
            return
        row.processed_revision = effect.requested_revision
        row.completed_at = utcnow()
        row.updated_at = utcnow()
        if row.requested_revision > row.processed_revision:
            row.effect_state = "pending"
            row.available_at = utcnow()
        else:
            row.effect_state = "completed"
        await session.commit()


async def _mark_effect_failed(
    session_factory: async_sessionmaker[AsyncSession],
    effect: ClaimedEffect,
    error: Exception,
) -> None:
    async with session_factory() as session:
        row = await session.get(RuntimeEffectModel, effect.runtime_effect_id)
        if row is None:
            return
        now = utcnow()
        row.effect_state = "failed"
        row.failed_at = now
        row.available_at = now + _FAILED_RETRY_DELAY
        row.last_error = str(error)
        row.updated_at = now
        await session.commit()


async def execute_runtime_effect(
    session_factory: async_sessionmaker[AsyncSession],
    effect: ClaimedEffect,
) -> None:
    if effect.effect_kind == "file_copy":
        from app.runtime.task_root import copy_file_if_needed

        await asyncio.to_thread(
            copy_file_if_needed,
            source_path=Path(str(effect.payload["source_path"])),
            destination=Path(str(effect.payload["destination_path"])),
        )
        return

    from app.runtime.projection.attempt_materialization import materialize_attempt_files
    from app.runtime.projection.dispatch.materialization import (
        materialize_dispatch_files,
    )
    from app.runtime.projection.manifest.materialization import (
        materialize_artifact_current_pointer,
        materialize_manifest,
    )

    async with session_factory() as session:
        if effect.effect_kind == "manifest_materialization":
            await materialize_manifest(session, str(effect.payload["task_id"]))
            return
        if effect.effect_kind == "dispatch_materialization":
            await materialize_dispatch_files(
                session,
                str(effect.payload["task_id"]),
                str(effect.payload["dispatch_id"]),
            )
            return
        if effect.effect_kind == "artifact_current_pointer_materialization":
            await materialize_artifact_current_pointer(
                session,
                str(effect.payload["task_id"]),
                str(effect.payload["owner_node_key"]),
                str(effect.payload["slot"]),
            )
            return
        await materialize_attempt_files(
            session,
            str(effect.payload["task_id"]),
            str(effect.payload["attempt_id"]),
        )


async def _drain_ready_effects(state: RuntimeEffectRunnerState) -> bool:
    processed_any = False
    while not state.stop_requested:
        effect = await _claim_next_effect(state.session_factory)
        if effect is None:
            return processed_any
        processed_any = True
        try:
            await execute_runtime_effect(state.session_factory, effect)
        except Exception as exc:  # pragma: no cover - exercised via retry lanes
            await _mark_effect_failed(state.session_factory, effect, exc)
        else:
            await _mark_effect_complete(state.session_factory, effect)
    return processed_any


async def _run_effect_runner(state: RuntimeEffectRunnerState) -> None:
    try:
        await _requeue_running_effects(state.session_factory)
        state.started.set()
        while not state.stop_requested:
            drained = await _drain_ready_effects(state)
            if drained:
                continue
            state.idle.set()
            try:
                await asyncio.wait_for(state.wakeup.wait(), timeout=_POLL_INTERVAL_SECONDS)
            except TimeoutError:
                pass
            finally:
                state.wakeup.clear()
                state.idle.clear()
    finally:
        state.started.set()
        state.idle.set()


def _ensure_runner_started() -> RuntimeEffectRunnerState:
    loop_id = _loop_id()
    state = _RUNNER_BY_LOOP.get(loop_id)
    if state is not None and state.task is not None and not state.task.done():
        return state

    from app.db.session import get_session_factory

    wakeup = asyncio.Event()
    idle = asyncio.Event()
    started = asyncio.Event()
    state = RuntimeEffectRunnerState(
        session_factory=get_session_factory(),
        wakeup=wakeup,
        idle=idle,
        started=started,
        stop_requested=False,
        task=None,
    )
    state.task = asyncio.create_task(_run_effect_runner(state), name="runtime-effect-runner")
    _RUNNER_BY_LOOP[loop_id] = state
    state.wakeup.set()
    return state


async def start_runtime_effect_runner() -> None:
    state = _ensure_runner_started()
    await state.started.wait()


async def stop_runtime_effect_runner() -> None:
    state = _RUNNER_BY_LOOP.pop(_loop_id(), None)
    if state is None or state.task is None:
        return
    state.stop_requested = True
    state.wakeup.set()
    await state.task


def notify_runtime_effect_runner() -> None:
    state = _ensure_runner_started()
    state.idle.clear()
    state.wakeup.set()


async def wait_for_runtime_effects(
    *,
    task_id: str | None = None,
    max_wait_seconds: float = 5.0,
) -> None:
    deadline = monotonic() + max_wait_seconds
    while monotonic() < deadline:
        from app.db.session import get_session_factory

        async with get_session_factory()() as session:
            query = select(RuntimeEffectModel.runtime_effect_id).where(
                RuntimeEffectModel.requested_revision > RuntimeEffectModel.processed_revision
            )
            if task_id is not None:
                query = query.where(RuntimeEffectModel.task_id == task_id)
            pending = await session.scalar(query.limit(1))
        if pending is None:
            state = _RUNNER_BY_LOOP.get(_loop_id())
            if state is None or state.idle.is_set():
                return
        notify_runtime_effect_runner()
        await asyncio.sleep(0.05)
    raise TimeoutError(f"runtime effects did not drain within {max_wait_seconds:.2f}s")


async def commit_runtime_session(session: AsyncSession) -> None:
    await structural_manifest_sync.materialize_registered_structural_manifests(session)
    await session.commit()
    structural_manifest_sync.clear_structural_manifest_sync(session)


async def rollback_runtime_session(session: AsyncSession) -> None:
    from app.runtime.effects.queue import clear_post_commit_actions

    structural_manifest_task_ids = structural_manifest_sync.clear_structural_manifest_sync(session)
    clear_post_commit_actions(session)
    await session.rollback()
    await structural_manifest_sync.restore_structural_manifests_after_rollback(
        session,
        task_ids=structural_manifest_task_ids,
    )


__all__ = [
    "ClaimedEffect",
    "RuntimeEffectRunnerState",
    "commit_runtime_session",
    "execute_runtime_effect",
    "notify_runtime_effect_runner",
    "rollback_runtime_session",
    "start_runtime_effect_runner",
    "stop_runtime_effect_runner",
    "wait_for_runtime_effects",
]
