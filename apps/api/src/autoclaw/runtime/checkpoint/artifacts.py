from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, NamedTuple, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import ArtifactCurrentPointerModel, ArtifactPublicationModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import EvidenceKind, EvidenceRef, TaskRootPaths
from autoclaw.runtime.errors import (
    invalid_request_shape_error,
    semantic_missing_resource_error,
)
from autoclaw.runtime.ids import artifact_current_pointer_id, artifact_publication_id
from autoclaw.runtime.post_commit.queue import coerce_source_path
from autoclaw.runtime.projection import CurrentRuntimeState
from autoclaw.runtime.task_root import planned_transient_surface_path


class CheckpointArtifacts(NamedTuple):
    produced_refs: list[EvidenceRef]
    produced_file_copies: list[tuple[Path, Path]]
    transient_refs: tuple[EvidenceRef, ...]
    transient_file_copies: list[tuple[Path, Path]]


async def collect_checkpoint_artifacts(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    checkpoint_write: Any,
    paths: TaskRootPaths,
) -> CheckpointArtifacts:
    produced_refs, produced_file_copies = await _collect_produced_artifacts(
        session,
        task_id=task_id,
        state=state,
        checkpoint_write=checkpoint_write,
        paths=paths,
    )
    transient_refs = _build_transient_refs(
        checkpoint_write=checkpoint_write,
        paths=paths,
        owner_node_key=state.current_node.node_key,
    )
    transient_file_copies = await _collect_transient_file_copies(
        checkpoint_write=checkpoint_write,
        transient_refs=transient_refs,
    )
    return CheckpointArtifacts(
        produced_refs=produced_refs,
        produced_file_copies=produced_file_copies,
        transient_refs=transient_refs,
        transient_file_copies=transient_file_copies,
    )


async def _artifact_version(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> int:
    return (
        int(
            await session.scalar(
                select(func.max(ArtifactPublicationModel.version)).where(
                    ArtifactPublicationModel.task_id == task_id,
                    ArtifactPublicationModel.owner_node_key == owner_node_key,
                    ArtifactPublicationModel.slot == slot,
                )
            )
            or 0
        )
        + 1
    )


def _produce_requirements_map(state: CurrentRuntimeState) -> dict[str, dict[str, object]]:
    return {
        str(requirement["slot"]): requirement
        for requirement in state.current_assignment.produces_json
    }


async def _collect_produced_artifacts(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    checkpoint_write: Any,
    paths: TaskRootPaths,
) -> tuple[list[EvidenceRef], list[tuple[Path, Path]]]:
    produced_refs: list[EvidenceRef] = []
    produced_file_copies: list[tuple[Path, Path]] = []
    claim_slots: set[str] = set()
    produce_requirements = _produce_requirements_map(state)
    for claim in checkpoint_write.produced_artifacts:
        if claim.slot in claim_slots:
            raise invalid_request_shape_error(
                f"duplicate produced artifact slot '{claim.slot}' in one checkpoint"
            )
        claim_slots.add(claim.slot)
        requirement = produce_requirements.get(claim.slot)
        if requirement is None:
            raise invalid_request_shape_error(
                f"produced artifact slot '{claim.slot}' is not declared for current assignment"
            )
        artifact_ref, file_copy = await _record_artifact_claim(
            session,
            task_id=task_id,
            state=state,
            claim=claim,
            requirement=requirement,
            paths=paths,
        )
        produced_refs.append(artifact_ref)
        produced_file_copies.append(file_copy)
    return produced_refs, produced_file_copies


async def _record_artifact_claim(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    claim: Any,
    requirement: dict[str, object],
    paths: TaskRootPaths,
) -> tuple[EvidenceRef, tuple[Path, Path]]:
    source_path = await _coerced_existing_path(claim.path, surface_name="produced artifact")
    version = await _artifact_version(
        session,
        task_id=task_id,
        owner_node_key=state.current_node.node_key,
        slot=claim.slot,
    )
    description = str(requirement["description"])
    destination = _artifact_destination(
        paths=paths,
        owner_node_key=state.current_node.node_key,
        slot=claim.slot,
        version=version,
        suffix=source_path.suffix,
    )
    previous_pointer = await _current_pointer(
        session,
        task_id=task_id,
        owner_node_key=state.current_node.node_key,
        slot=claim.slot,
    )
    _persist_artifact_publication(
        session,
        state=state,
        attempt_id=state.current_attempt.attempt_id,
        task_id=task_id,
        slot=claim.slot,
        version=version,
        path=destination,
        description=description,
        previous_pointer=previous_pointer,
    )
    _upsert_current_pointer(
        session,
        state=state,
        task_id=task_id,
        slot=claim.slot,
        version=version,
        path=destination,
        description=description,
        previous_pointer=previous_pointer,
    )
    return _artifact_ref(claim.slot, version, destination, description), (source_path, destination)


async def _coerced_existing_path(path: str | Path, *, surface_name: str) -> Path:
    candidate_path = path if isinstance(path, Path) else Path(path)
    source_path = await asyncio.to_thread(coerce_source_path, candidate_path)
    if not source_path.is_file():
        raise semantic_missing_resource_error(f"{surface_name} does not exist: {source_path}")
    return source_path


def _artifact_destination(
    *,
    paths: TaskRootPaths,
    owner_node_key: str,
    slot: str,
    version: int,
    suffix: str,
) -> Path:
    destination_dir = paths.artifacts_path / owner_node_key / slot
    return destination_dir / f"{slot}.v{version:02d}{suffix}"


async def _current_pointer(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> ArtifactCurrentPointerModel | None:
    return cast(
        ArtifactCurrentPointerModel | None,
        await session.scalar(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.owner_node_key == owner_node_key,
                ArtifactCurrentPointerModel.slot == slot,
            )
        ),
    )


def _persist_artifact_publication(
    session: AsyncSession,
    *,
    state: CurrentRuntimeState,
    attempt_id: str,
    task_id: str,
    slot: str,
    version: int,
    path: Path,
    description: str,
    previous_pointer: ArtifactCurrentPointerModel | None,
) -> None:
    session.add(
        ArtifactPublicationModel(
            artifact_publication_id=artifact_publication_id(attempt_id, slot, version),
            task_id=task_id,
            flow_node_id=state.current_assignment.flow_node_id,
            owner_node_key=state.current_node.node_key,
            slot=slot,
            version=version,
            path=str(path),
            description=description,
            assignment_key=state.current_assignment.assignment_key,
            attempt_id=attempt_id,
            supersedes_version=(
                previous_pointer.current_version if previous_pointer is not None else None
            ),
            supersedes_path=previous_pointer.current_path if previous_pointer is not None else None,
        )
    )


def _upsert_current_pointer(
    session: AsyncSession,
    *,
    state: CurrentRuntimeState,
    task_id: str,
    slot: str,
    version: int,
    path: Path,
    description: str,
    previous_pointer: ArtifactCurrentPointerModel | None,
) -> None:
    published_at = utc_now()
    if previous_pointer is None:
        session.add(
            ArtifactCurrentPointerModel(
                artifact_current_pointer_id=artifact_current_pointer_id(
                    task_id,
                    state.current_node.node_key,
                    slot,
                ),
                task_id=task_id,
                flow_node_id=state.current_assignment.flow_node_id,
                owner_node_key=state.current_node.node_key,
                slot=slot,
                current_version=version,
                current_path=str(path),
                description=description,
                assignment_key=state.current_assignment.assignment_key,
                attempt_id=state.current_attempt.attempt_id,
                published_at=published_at,
                supersedes_path=None,
            )
        )
        return
    previous_current_path = previous_pointer.current_path
    previous_pointer.flow_node_id = state.current_assignment.flow_node_id
    previous_pointer.current_version = version
    previous_pointer.current_path = str(path)
    previous_pointer.description = description
    previous_pointer.assignment_key = state.current_assignment.assignment_key
    previous_pointer.attempt_id = state.current_attempt.attempt_id
    previous_pointer.published_at = published_at
    previous_pointer.supersedes_path = previous_current_path


def _artifact_ref(slot: str, version: int, path: Path, description: str) -> EvidenceRef:
    return EvidenceRef(
        kind=EvidenceKind.ARTIFACT,
        slot=slot,
        version=version,
        path=path,
        description=description,
    )


def _build_transient_refs(
    *,
    checkpoint_write: Any,
    paths: TaskRootPaths,
    owner_node_key: str,
) -> tuple[EvidenceRef, ...]:
    return tuple(
        EvidenceRef(
            kind=EvidenceKind.TRANSIENT,
            path=planned_transient_surface_path(
                paths=paths,
                source_path=surface.path,
                owner_node_key=owner_node_key,
            ),
            description=surface.description,
        )
        for surface in checkpoint_write.transient_surfaces
    )


async def _collect_transient_file_copies(
    *,
    checkpoint_write: Any,
    transient_refs: tuple[EvidenceRef, ...],
) -> list[tuple[Path, Path]]:
    transient_file_copies: list[tuple[Path, Path]] = []
    for surface, transient_ref in zip(
        checkpoint_write.transient_surfaces,
        transient_refs,
        strict=True,
    ):
        transient_source = await _coerced_existing_path(
            surface.path,
            surface_name="transient surface",
        )
        transient_file_copies.append((transient_source, transient_ref.path))
    return transient_file_copies


__all__ = ["CheckpointArtifacts", "collect_checkpoint_artifacts"]
