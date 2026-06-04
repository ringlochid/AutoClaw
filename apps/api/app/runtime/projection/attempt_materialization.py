from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    AttemptProducedRefModel,
)
from app.runtime.contracts import AssignmentProjection, CheckpointProjection, TaskRootPaths
from app.runtime.control.failures import illegal_state_error, missing_resource_error
from app.runtime.projection.projection_mappers import (
    assignment_projection_from_model,
    checkpoint_projection_from_model,
)
from app.runtime.task_root import (
    artifact_index_json_path,
    load_task_root_paths,
    localize_assignment_projection,
    localize_checkpoint_projection,
    transient_index_json_path,
    write_assignment_projection,
    write_checkpoint_projection,
    write_json_file,
)


async def materialize_attempt_files(session: AsyncSession, task_id: str, attempt_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    attempt = await session.get(AttemptModel, attempt_id)
    if attempt is None:
        raise missing_resource_error(f"unknown attempt_id '{attempt_id}'")
    assignment = await session.scalar(
        select(AssignmentModel).where(AssignmentModel.current_attempt_id == attempt_id)
    )
    if assignment is None:
        assignment = await session.get(AssignmentModel, attempt.assignment_id)
    if assignment is None:
        raise illegal_state_error(f"missing assignment for attempt '{attempt_id}'")
    assignment_projection = localize_assignment_projection(
        paths=paths,
        assignment=assignment_projection_from_model(assignment),
    )
    checkpoint_projection = None
    if attempt.latest_checkpoint_id is not None:
        checkpoint = await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)
        if checkpoint is not None:
            checkpoint_projection = localize_checkpoint_projection(
                paths=paths,
                checkpoint=checkpoint_projection_from_model(checkpoint),
            )
    produced_refs = list(
        await session.scalars(
            select(AttemptProducedRefModel)
            .where(AttemptProducedRefModel.attempt_id == attempt_id)
            .order_by(AttemptProducedRefModel.order_index.asc())
        )
    )
    write_attempt_projection_files(
        paths=paths,
        attempt_id=attempt_id,
        assignment_projection=assignment_projection,
        node_key=attempt.node_key,
        checkpoint_projection=checkpoint_projection,
        produced_refs=produced_refs,
    )


def write_attempt_projection_files(
    *,
    paths: TaskRootPaths,
    attempt_id: str,
    assignment_projection: AssignmentProjection,
    node_key: str,
    checkpoint_projection: CheckpointProjection | None = None,
    produced_refs: list[AttemptProducedRefModel] | None = None,
) -> None:
    write_assignment_projection(
        paths=paths,
        attempt_id=attempt_id,
        assignment=assignment_projection,
    )
    if checkpoint_projection is not None:
        write_checkpoint_projection(
            paths=paths,
            attempt_id=attempt_id,
            checkpoint=checkpoint_projection,
        )
    write_json_file(
        artifact_index_json_path(paths=paths, attempt_id=attempt_id),
        {
            "attempt_id": attempt_id,
            "node_key": node_key,
            "assignment_key": assignment_projection.assignment_key,
            "publications": _artifact_publication_payloads(produced_refs or []),
        },
    )
    write_json_file(
        transient_index_json_path(paths=paths, attempt_id=attempt_id),
        _transient_index_payload(assignment_projection, checkpoint_projection),
    )


def _artifact_publication_payloads(
    produced_refs: list[AttemptProducedRefModel],
) -> list[dict[str, object]]:
    return [
        {
            "owner_node_key": produced.owner_node_key,
            "slot": produced.slot,
            "version": produced.version,
            "path": produced.path,
            "description": produced.description,
            "published_at": produced.published_at.isoformat(),
            "became_current": produced.became_current,
        }
        for produced in produced_refs
    ]


def _transient_index_payload(
    assignment_projection: AssignmentProjection,
    checkpoint_projection: CheckpointProjection | None,
) -> list[dict[str, str]]:
    transient_entries: list[dict[str, str]] = []
    seen_transient_keys: set[tuple[str, str]] = set()
    for transient_ref in (
        *assignment_projection.transient_refs,
        *(checkpoint_projection.transient_refs if checkpoint_projection is not None else ()),
    ):
        entry = {
            "path": str(transient_ref.path),
            "description": transient_ref.description,
        }
        key = (entry["path"], entry["description"])
        if key in seen_transient_keys:
            continue
        seen_transient_keys.add(key)
        transient_entries.append(entry)
    return transient_entries
