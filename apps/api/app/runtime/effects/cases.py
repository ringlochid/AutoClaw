from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.contracts import EvidenceRef
from app.runtime.effects.queue import (
    queue_artifact_current_pointer_materialization,
    queue_attempt_materialization,
    queue_dispatch_materialization,
    queue_file_copy,
    queue_manifest_materialization,
)


def stage_launch_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    dispatch_id: str,
) -> None:
    queue_manifest_materialization(session, task_id=task_id)
    queue_attempt_materialization(session, task_id=task_id, attempt_id=attempt_id)
    queue_dispatch_materialization(session, task_id=task_id, dispatch_id=dispatch_id)


def stage_dispatch_open_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    queue_dispatch_materialization(session, task_id=task_id, dispatch_id=dispatch_id)


def stage_operator_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    queue_dispatch_materialization(session, task_id=task_id, dispatch_id=dispatch_id)


def stage_structural_outputs(session: AsyncSession, *, task_id: str) -> None:
    queue_manifest_materialization(session, task_id=task_id)


def stage_assign_child_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    transient_file_copies: list[tuple[Path, Path]] | tuple[tuple[Path, Path], ...] = (),
) -> None:
    for source_path, destination in transient_file_copies:
        queue_file_copy(
            session,
            source_path=source_path,
            destination=destination,
        )
    queue_attempt_materialization(session, task_id=task_id, attempt_id=attempt_id)
    queue_manifest_materialization(session, task_id=task_id)


def stage_boundary_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    attempt_ids: tuple[str, ...] = (),
) -> None:
    for attempt_id in attempt_ids:
        queue_attempt_materialization(session, task_id=task_id, attempt_id=attempt_id)
    queue_manifest_materialization(session, task_id=task_id)
    queue_dispatch_materialization(session, task_id=task_id, dispatch_id=dispatch_id)


def stage_checkpoint_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    owner_node_key: str,
    attempt_id: str,
    produced_refs: list[EvidenceRef],
    produced_file_copies: list[tuple[Path, Path]],
    transient_file_copies: list[tuple[Path, Path]],
) -> None:
    for source_path, destination in produced_file_copies:
        queue_file_copy(
            session,
            source_path=source_path,
            destination=destination,
        )
    for source_path, destination in transient_file_copies:
        queue_file_copy(
            session,
            source_path=source_path,
            destination=destination,
        )
    queue_attempt_materialization(session, task_id=task_id, attempt_id=attempt_id)
    queue_manifest_materialization(session, task_id=task_id)
    for ref in produced_refs:
        if ref.slot is not None:
            queue_artifact_current_pointer_materialization(
                session,
                task_id=task_id,
                owner_node_key=owner_node_key,
                slot=ref.slot,
            )
    queue_dispatch_materialization(session, task_id=task_id, dispatch_id=dispatch_id)


__all__ = [
    "stage_assign_child_outputs",
    "stage_boundary_outputs",
    "stage_checkpoint_outputs",
    "stage_dispatch_open_outputs",
    "stage_launch_outputs",
    "stage_operator_outputs",
    "stage_structural_outputs",
]
