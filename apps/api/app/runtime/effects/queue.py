from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.effects.keys import (
    RuntimeEffectKey,
    artifact_current_pointer_effect_key,
    attempt_materialization_effect_key,
    dispatch_materialization_effect_key,
    effect_priority,
    file_copy_effect_key,
    manifest_materialization_effect_key,
)

_STAGED_ACTIONS_KEY = "runtime_post_commit_actions"
_STAGED_ACTION_KEYS_KEY = "runtime_post_commit_seen_keys"

type PostCommitActionKind = Literal[
    "artifact_current_pointer_materialization",
    "attempt_materialization",
    "dispatch_materialization",
    "file_copy",
    "manifest_materialization",
]


@dataclass(frozen=True)
class PostCommitAction:
    key: RuntimeEffectKey
    task_id: str | None
    effect_kind: PostCommitActionKind
    payload: dict[str, object]
    priority: int


async def apply_post_commit_actions(
    session: AsyncSession,
    actions: list[PostCommitAction],
) -> None:
    if not actions:
        return
    from app.db.session import get_session_factory
    from app.runtime.projection.attempt_materialization import materialize_attempt_files
    from app.runtime.projection.dispatch.materialization import materialize_dispatch_files
    from app.runtime.projection.manifest.materialization import (
        materialize_artifact_current_pointer,
        materialize_manifest,
    )
    from app.runtime.task_root import copy_file_if_needed

    sorted_actions = sorted(actions, key=lambda item: (item.priority, item.task_id or "", item.key))
    for action in sorted_actions:
        if action.effect_kind != "file_copy":
            continue
        await asyncio.to_thread(
            copy_file_if_needed,
            source_path=Path(str(action.payload["source_path"])),
            destination=Path(str(action.payload["destination_path"])),
        )

    session_factory = get_session_factory()
    async with session_factory() as projection_session:
        for action in sorted_actions:
            if action.effect_kind == "file_copy" or action.task_id is None:
                continue
            if action.effect_kind == "manifest_materialization":
                await materialize_manifest(projection_session, action.task_id)
                continue
            if action.effect_kind == "dispatch_materialization":
                await materialize_dispatch_files(
                    projection_session,
                    action.task_id,
                    str(action.payload["dispatch_id"]),
                )
                continue
            if action.effect_kind == "artifact_current_pointer_materialization":
                await materialize_artifact_current_pointer(
                    projection_session,
                    action.task_id,
                    str(action.payload["owner_node_key"]),
                    str(action.payload["slot"]),
                )
                continue
            await materialize_attempt_files(
                projection_session,
                action.task_id,
                str(action.payload["attempt_id"]),
            )


def pop_post_commit_actions(session: AsyncSession) -> list[PostCommitAction]:
    actions = list(_staged_actions(session))
    clear_post_commit_actions(session)
    return actions


def clear_post_commit_actions(session: AsyncSession) -> None:
    session.info.pop(_STAGED_ACTIONS_KEY, None)
    session.info.pop(_STAGED_ACTION_KEYS_KEY, None)


def queue_file_copy(
    session: AsyncSession,
    *,
    source_path: Path,
    destination: Path,
) -> None:
    _stage_post_commit_action(
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
    _stage_post_commit_action(
        session,
        key=attempt_materialization_effect_key(task_id, attempt_id),
        task_id=task_id,
        effect_kind="attempt_materialization",
        payload={"task_id": task_id, "attempt_id": attempt_id},
    )


def queue_manifest_materialization(session: AsyncSession, *, task_id: str) -> None:
    _stage_post_commit_action(
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
    _stage_post_commit_action(
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
    _stage_post_commit_action(
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


def coerce_source_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _staged_actions(session: AsyncSession) -> list[PostCommitAction]:
    return cast(list[PostCommitAction], session.info.setdefault(_STAGED_ACTIONS_KEY, []))


def _staged_action_keys(session: AsyncSession) -> set[RuntimeEffectKey]:
    return cast(
        set[RuntimeEffectKey],
        session.info.setdefault(_STAGED_ACTION_KEYS_KEY, set()),
    )


def _stage_post_commit_action(
    session: AsyncSession,
    *,
    key: RuntimeEffectKey,
    task_id: str | None,
    effect_kind: PostCommitActionKind,
    payload: dict[str, object],
) -> None:
    seen_keys = _staged_action_keys(session)
    if key in seen_keys:
        return
    seen_keys.add(key)
    _staged_actions(session).append(
        PostCommitAction(
            key=key,
            task_id=task_id,
            effect_kind=effect_kind,
            payload=payload,
            priority=effect_priority(effect_kind),
        )
    )


__all__ = [
    "PostCommitAction",
    "apply_post_commit_actions",
    "clear_post_commit_actions",
    "coerce_source_path",
    "pop_post_commit_actions",
    "queue_artifact_current_pointer_materialization",
    "queue_attempt_materialization",
    "queue_dispatch_materialization",
    "queue_file_copy",
    "queue_manifest_materialization",
]
