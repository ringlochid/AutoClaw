from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import AttemptCheckpointModel, DispatchTurnModel
from app.runtime.contracts import (
    RuntimeContextRef,
    TaskRootPaths,
)
from app.runtime.projection.manifest.current_context_queries import (
    latest_dispatch_selected_checkpoint_attempt_id,
)
from app.runtime.projection.projection_mappers import runtime_context_ref_from_json
from app.runtime.task_root import checkpoint_json_path


def release_precondition_descendant_refs(
    dispatch: DispatchTurnModel | None,
) -> tuple[RuntimeContextRef, ...] | None:
    if dispatch is None:
        return None
    descendant_refs_json = dispatch.release_precondition_descendant_refs_json
    if descendant_refs_json is None:
        return None
    return tuple(runtime_context_ref_from_json(item) for item in descendant_refs_json)


async def dispatch_selected_checkpoint_path_at_cutoff(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel | None,
    paths: TaskRootPaths,
    recorded_at_cutoff: datetime | None,
    latest_checkpoint_path: Path | None,
) -> Path | None:
    if dispatch is None or dispatch.relevant_checkpoint_attempt_id is None:
        return None
    checkpoint = await latest_checkpoint_for_attempt_before_cutoff(
        session,
        attempt_id=dispatch.relevant_checkpoint_attempt_id,
        recorded_at_cutoff=recorded_at_cutoff,
    )
    if checkpoint is None:
        return None
    checkpoint_path = checkpoint_json_path(
        paths=paths,
        attempt_id=checkpoint.attempt_id,
    ).with_suffix(".md")
    if latest_checkpoint_path is not None and checkpoint_path == latest_checkpoint_path:
        return None
    return checkpoint_path


async def stable_selected_checkpoint_path_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    paths: TaskRootPaths,
    latest_checkpoint_path: Path | None,
) -> Path | None:
    selected_attempt_id = await latest_dispatch_selected_checkpoint_attempt_id(
        session,
        task_id=task_id,
        attempt_id=attempt_id,
    )
    if selected_attempt_id is None or selected_attempt_id == attempt_id:
        return None
    checkpoint = await latest_checkpoint_for_attempt_before_cutoff(
        session,
        attempt_id=selected_attempt_id,
        recorded_at_cutoff=None,
    )
    if checkpoint is None:
        return None
    checkpoint_path = checkpoint_json_path(
        paths=paths,
        attempt_id=checkpoint.attempt_id,
    ).with_suffix(".md")
    if latest_checkpoint_path is not None and checkpoint_path == latest_checkpoint_path:
        return None
    return checkpoint_path


async def latest_checkpoint_for_attempt_before_cutoff(
    session: AsyncSession,
    *,
    attempt_id: str,
    recorded_at_cutoff: datetime | None,
) -> AttemptCheckpointModel | None:
    if recorded_at_cutoff is None:
        return cast(
            AttemptCheckpointModel | None,
            await session.scalar(
                select(AttemptCheckpointModel)
                .options(raiseload("*"))
                .where(AttemptCheckpointModel.attempt_id == attempt_id)
                .order_by(AttemptCheckpointModel.recorded_at.desc())
            ),
        )
    return cast(
        AttemptCheckpointModel | None,
        await session.scalar(
            select(AttemptCheckpointModel)
            .options(raiseload("*"))
            .where(
                AttemptCheckpointModel.attempt_id == attempt_id,
                AttemptCheckpointModel.recorded_at <= recorded_at_cutoff,
            )
            .order_by(AttemptCheckpointModel.recorded_at.desc())
        ),
    )


def checkpoint_attempt_id_from_path(path: Path) -> str | None:
    if path.name not in {"latest-checkpoint.md", "latest-checkpoint.json"}:
        return None
    attempt_id = path.parent.name
    return attempt_id or None
