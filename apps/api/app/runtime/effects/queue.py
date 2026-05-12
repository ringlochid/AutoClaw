from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.runtime.common import utcnow
from app.db.models.runtime.effects import RuntimeEffectModel
from app.runtime.effects.keys import (
    RuntimeEffectKey,
    RuntimeEffectKind,
    artifact_current_pointer_effect_key,
    attempt_materialization_effect_key,
    dispatch_materialization_effect_key,
    effect_priority,
    file_copy_effect_key,
    manifest_materialization_effect_key,
    runtime_effect_dedupe_key,
    runtime_effect_id,
)

_QUEUE_KEY = "runtime_post_commit_effects"
_SEEN_KEY = "runtime_post_commit_seen_keys"


@dataclass(frozen=True)
class QueuedEffect:
    key: RuntimeEffectKey
    task_id: str | None
    effect_kind: RuntimeEffectKind
    payload: dict[str, object]
    priority: int


def coerce_source_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _queued_effects(session: AsyncSession) -> list[QueuedEffect]:
    return cast(list[QueuedEffect], session.info.setdefault(_QUEUE_KEY, []))


def _seen_keys(session: AsyncSession) -> set[RuntimeEffectKey]:
    return cast(set[RuntimeEffectKey], session.info.setdefault(_SEEN_KEY, set()))


def queue_post_commit_action(
    session: AsyncSession,
    *,
    key: RuntimeEffectKey,
    task_id: str | None,
    effect_kind: RuntimeEffectKind,
    payload: dict[str, object],
) -> None:
    seen_keys = _seen_keys(session)
    if key in seen_keys:
        return
    seen_keys.add(key)
    _queued_effects(session).append(
        QueuedEffect(
            key=key,
            task_id=task_id,
            effect_kind=effect_kind,
            payload=payload,
            priority=effect_priority(effect_kind),
        )
    )


def clear_post_commit_actions(session: AsyncSession) -> None:
    session.info.pop(_QUEUE_KEY, None)
    session.info.pop(_SEEN_KEY, None)


async def stage_post_commit_effects(session: AsyncSession) -> bool:
    queued = list(_queued_effects(session))
    clear_post_commit_actions(session)
    if not queued:
        return False
    for effect in queued:
        dedupe_key = runtime_effect_dedupe_key(effect.key)
        row = await session.scalar(
            select(RuntimeEffectModel).where(RuntimeEffectModel.dedupe_key == dedupe_key)
        )
        now = utcnow()
        if row is None:
            session.add(
                RuntimeEffectModel(
                    runtime_effect_id=runtime_effect_id(effect.key),
                    task_id=effect.task_id,
                    dedupe_key=dedupe_key,
                    effect_kind=effect.effect_kind,
                    payload_json=effect.payload,
                    priority=effect.priority,
                    requested_revision=1,
                    processed_revision=0,
                    attempt_count=0,
                    effect_state="pending",
                    available_at=now,
                    last_error=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            continue
        row.task_id = effect.task_id
        row.effect_kind = effect.effect_kind
        row.payload_json = effect.payload
        row.priority = effect.priority
        row.requested_revision += 1
        row.effect_state = "pending"
        row.available_at = now
        row.completed_at = None
        row.failed_at = None
        row.last_error = None
        row.updated_at = now
    return True


def queue_file_copy(
    session: AsyncSession,
    *,
    source_path: Path,
    destination: Path,
) -> None:
    queue_post_commit_action(
        session,
        key=file_copy_effect_key(destination),
        task_id=None,
        effect_kind="file_copy",
        payload={
            "source_path": str(coerce_source_path(source_path)),
            "destination_path": str(destination),
        },
    )


def queue_attempt_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> None:
    queue_post_commit_action(
        session,
        key=attempt_materialization_effect_key(task_id, attempt_id),
        task_id=task_id,
        effect_kind="attempt_materialization",
        payload={"task_id": task_id, "attempt_id": attempt_id},
    )


def queue_manifest_materialization(session: AsyncSession, *, task_id: str) -> None:
    queue_post_commit_action(
        session,
        key=manifest_materialization_effect_key(task_id),
        task_id=task_id,
        effect_kind="manifest_materialization",
        payload={"task_id": task_id},
    )


def queue_dispatch_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    queue_post_commit_action(
        session,
        key=dispatch_materialization_effect_key(task_id, dispatch_id),
        task_id=task_id,
        effect_kind="dispatch_materialization",
        payload={"task_id": task_id, "dispatch_id": dispatch_id},
    )


def queue_artifact_current_pointer_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> None:
    queue_post_commit_action(
        session,
        key=artifact_current_pointer_effect_key(task_id, owner_node_key, slot),
        task_id=task_id,
        effect_kind="artifact_current_pointer_materialization",
        payload={
            "task_id": task_id,
            "owner_node_key": owner_node_key,
            "slot": slot,
        },
    )


async def has_pending_runtime_effect(
    session: AsyncSession,
    *,
    key: RuntimeEffectKey,
) -> bool:
    return bool(
        await session.scalar(
            select(RuntimeEffectModel.runtime_effect_id).where(
                RuntimeEffectModel.dedupe_key == runtime_effect_dedupe_key(key),
                RuntimeEffectModel.requested_revision > RuntimeEffectModel.processed_revision,
            )
        )
    )


__all__ = [
    "QueuedEffect",
    "clear_post_commit_actions",
    "coerce_source_path",
    "has_pending_runtime_effect",
    "queue_artifact_current_pointer_materialization",
    "queue_attempt_materialization",
    "queue_dispatch_materialization",
    "queue_file_copy",
    "queue_manifest_materialization",
    "queue_post_commit_action",
    "stage_post_commit_effects",
]
