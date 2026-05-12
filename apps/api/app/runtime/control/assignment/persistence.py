from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssignmentCriteriaRefModel, AttemptConsumedRefModel, FlowNodeModel
from app.runtime.contracts import EvidenceKind, EvidenceRef, NodeRuntimeFileRef, TaskRootPaths
from app.runtime.effects.queue import queue_file_copy
from app.runtime.ids import assignment_criteria_ref_id, attempt_consumed_ref_id
from app.runtime.task_root import planned_transient_surface_path
from app.schemas.runtime import CheckpointFileRef
from app.schemas.runtime.parent_tools import AssignChildToolCall


def planned_transient_refs(
    *,
    child_node: FlowNodeModel,
    typed_call: AssignChildToolCall,
    task_root_paths: TaskRootPaths,
) -> tuple[EvidenceRef, ...]:
    return tuple(
        EvidenceRef(
            kind=EvidenceKind.TRANSIENT,
            path=planned_transient_surface_path(
                paths=task_root_paths,
                source_path=surface.path,
                owner_node_key=child_node.node_key,
            ),
            description=surface.description,
        )
        for surface in typed_call.payload.transient_surfaces
    )


def queue_transient_surface_copies(
    session: AsyncSession,
    *,
    typed_call: AssignChildToolCall,
    transient_refs: tuple[EvidenceRef, ...],
) -> None:
    for surface, transient_ref in zip(
        typed_call.payload.transient_surfaces,
        transient_refs,
        strict=True,
    ):
        queue_file_copy(
            session,
            source_path=surface.path,
            destination=transient_ref.path,
        )


async def persist_assignment_criteria_refs(
    session: AsyncSession,
    *,
    assignment_id_value: str,
    criteria_refs: list[EvidenceRef],
) -> None:
    for index, ref in enumerate(criteria_refs, start=1):
        session.add(
            AssignmentCriteriaRefModel(
                assignment_criteria_ref_id=assignment_criteria_ref_id(
                    assignment_id_value,
                    ref.slot or f"criteria-{index}",
                ),
                assignment_id=assignment_id_value,
                slot=ref.slot or f"criteria-{index}",
                path=str(ref.path),
                description=ref.description,
                version=ref.version,
                order_index=index,
            )
        )


async def persist_attempt_consumed_refs(
    session: AsyncSession,
    *,
    attempt_id_value: str,
    consumed_refs: list[EvidenceRef | NodeRuntimeFileRef],
) -> None:
    for index, runtime_ref in enumerate(consumed_refs, start=1):
        session.add(
            AttemptConsumedRefModel(
                attempt_consumed_ref_id=attempt_consumed_ref_id(attempt_id_value, index),
                attempt_id=attempt_id_value,
                ref_kind=runtime_ref.kind.value,
                slot=getattr(runtime_ref, "slot", None),
                version=getattr(runtime_ref, "version", None),
                path=str(runtime_ref.path),
                description=runtime_ref.description,
                order_index=index,
            )
        )


def latest_checkpoint_ref(
    *,
    attempt_id: str,
    latest_checkpoint_id: str | None,
    task_root_paths: TaskRootPaths,
) -> CheckpointFileRef | None:
    if latest_checkpoint_id is None:
        return None
    return CheckpointFileRef(
        path=task_root_paths.attempts_path / attempt_id / "latest-checkpoint.md",
        description="Latest checkpoint for the current attempt.",
    )


__all__ = [
    "latest_checkpoint_ref",
    "persist_assignment_criteria_refs",
    "persist_attempt_consumed_refs",
    "planned_transient_refs",
    "queue_transient_surface_copies",
]
