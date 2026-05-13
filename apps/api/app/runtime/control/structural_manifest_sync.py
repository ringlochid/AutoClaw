from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.projection.manifest.materialization import materialize_manifest

_STRUCTURAL_MANIFEST_TASK_IDS_KEY = "structural_manifest_task_ids"


def _registered_task_ids(session: AsyncSession) -> set[str]:
    return cast(
        set[str],
        session.info.setdefault(_STRUCTURAL_MANIFEST_TASK_IDS_KEY, set()),
    )


def register_structural_manifest_sync(
    session: AsyncSession,
    *,
    task_id: str,
) -> None:
    _registered_task_ids(session).add(task_id)


async def materialize_registered_structural_manifests(session: AsyncSession) -> None:
    task_ids = tuple(sorted(_registered_task_ids(session)))
    if not task_ids:
        return
    await session.flush()
    for task_id in task_ids:
        await materialize_manifest(session, task_id)


def clear_structural_manifest_sync(session: AsyncSession) -> tuple[str, ...]:
    task_ids = cast(
        set[str],
        session.info.pop(_STRUCTURAL_MANIFEST_TASK_IDS_KEY, set()),
    )
    return tuple(sorted(task_ids))


async def restore_structural_manifests_after_rollback(
    session: AsyncSession,
    *,
    task_ids: tuple[str, ...],
) -> None:
    for task_id in task_ids:
        try:
            await materialize_manifest(session, task_id)
        except Exception:
            # The original failure still owns the response path. This restoration is
            # best-effort to keep the stable manifest aligned with rolled-back truth.
            continue


__all__ = [
    "clear_structural_manifest_sync",
    "materialize_registered_structural_manifests",
    "register_structural_manifest_sync",
    "restore_structural_manifests_after_rollback",
]
