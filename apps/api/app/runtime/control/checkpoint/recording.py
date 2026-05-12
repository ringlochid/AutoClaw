from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AttemptCheckpointModel,
    AttemptProducedRefModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
)
from app.runtime.contracts import CheckpointKind, EvidenceRef
from app.runtime.control.checkpoint.artifacts import collect_checkpoint_artifacts
from app.runtime.control.clock import utc_now
from app.runtime.control.flow.queries import latest_checkpoint_for_attempt
from app.runtime.effects.queue import (
    queue_artifact_current_pointer_materialization,
    queue_attempt_materialization,
    queue_dispatch_materialization,
    queue_file_copy,
    queue_manifest_materialization,
)
from app.runtime.ids import artifact_publication_id
from app.runtime.ids import checkpoint_id as runtime_checkpoint_id
from app.runtime.projection import CurrentRuntimeState, current_runtime_state, load_task_root_paths
from app.schemas.runtime import CheckpointFileRef, CheckpointRead, CheckpointWrite


def _ensure_checkpoint_writable(
    state: CurrentRuntimeState,
    latest_checkpoint: AttemptCheckpointModel | None,
) -> None:
    if (
        state.current_attempt.closed_at is not None
        or state.current_attempt.terminal_outcome is not None
    ):
        raise ValueError("closed attempt cannot record new checkpoints")
    if (
        latest_checkpoint is not None
        and latest_checkpoint.checkpoint_kind == CheckpointKind.TERMINAL.value
    ):
        raise ValueError("attempt already has a terminal checkpoint")


async def _checkpoint_sequence(session: AsyncSession, attempt_id: str) -> int:
    return (
        int(
            await session.scalar(
                select(func.count())
                .select_from(AttemptCheckpointModel)
                .where(AttemptCheckpointModel.attempt_id == attempt_id)
            )
            or 0
        )
        + 1
    )


def _persist_checkpoint_row(
    session: AsyncSession,
    *,
    checkpoint_id: str,
    state: CurrentRuntimeState,
    checkpoint_write: Any,
    produced_refs: list[EvidenceRef],
    transient_refs: tuple[EvidenceRef, ...],
) -> None:
    session.add(
        AttemptCheckpointModel(
            checkpoint_id=checkpoint_id,
            assignment_id=state.current_assignment.assignment_id,
            assignment_key=state.current_assignment.assignment_key,
            attempt_id=state.current_attempt.attempt_id,
            flow_node_id=state.current_assignment.flow_node_id,
            node_key=state.current_node.node_key,
            checkpoint_kind=checkpoint_write.checkpoint_kind.value,
            outcome=(
                checkpoint_write.outcome.value if checkpoint_write.outcome is not None else None
            ),
            summary=checkpoint_write.handoff.summary,
            next_step=checkpoint_write.handoff.next_step,
            blockers_json=list(checkpoint_write.handoff.blockers),
            risks_json=list(checkpoint_write.handoff.risks),
            produced_artifact_claims_json=[
                claim.model_dump(mode="json") for claim in checkpoint_write.produced_artifacts
            ],
            produced_artifacts_json=[ref.model_dump(mode="json") for ref in produced_refs],
            artifact_refs_json=[ref.model_dump(mode="json") for ref in produced_refs],
            transient_refs_json=[ref.model_dump(mode="json") for ref in transient_refs],
            task_memory_search_hints_json=list(checkpoint_write.task_memory_search_hints),
        )
    )


def _persist_attempt_produced_refs(
    session: AsyncSession,
    *,
    attempt_id: str,
    assignment_key: str,
    owner_node_key: str,
    produced_refs: list[EvidenceRef],
) -> None:
    for index, ref in enumerate(produced_refs, start=1):
        session.add(
            AttemptProducedRefModel(
                attempt_produced_ref_id=artifact_publication_id(
                    attempt_id,
                    ref.slot or f"artifact-{index}",
                    ref.version or index,
                ),
                attempt_id=attempt_id,
                owner_node_key=owner_node_key,
                assignment_key=assignment_key,
                slot=ref.slot or f"artifact-{index}",
                version=ref.version or index,
                path=str(ref.path),
                description=ref.description,
                published_at=utc_now(),
                became_current=True,
                order_index=index,
            )
        )


def _update_delivery_state_for_checkpoint(
    delivery_state: DispatchDeliveryStateModel | None,
    *,
    checkpoint_kind: CheckpointKind,
) -> None:
    if delivery_state is None:
        return
    if checkpoint_kind == CheckpointKind.PROGRESS:
        delivery_state.last_controller_progress_at = utc_now()
    else:
        delivery_state.last_controller_terminal_at = utc_now()
    delivery_state.updated_at = utc_now()


def _queue_checkpoint_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    owner_node_key: str,
    attempt_id: str,
    produced_refs: list[EvidenceRef],
    produced_file_copies: list[tuple[Path, Path]],
    transient_file_copies: list[tuple[Path, Path]],
    delivery_state: DispatchDeliveryStateModel | None,
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
    queue_attempt_materialization(
        session,
        task_id=task_id,
        attempt_id=attempt_id,
    )
    queue_manifest_materialization(session, task_id=task_id)
    for ref in produced_refs:
        if ref.slot is not None:
            queue_artifact_current_pointer_materialization(
                session,
                task_id=task_id,
                owner_node_key=owner_node_key,
                slot=ref.slot,
            )
    if delivery_state is not None:
        queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=dispatch_id,
        )


async def record_checkpoint(
    session: AsyncSession,
    task_id: str,
    payload: CheckpointWrite,
) -> CheckpointRead:
    state = await current_runtime_state(session, task_id)
    flow = state.flow
    if flow.current_open_dispatch_id is None:
        raise ValueError("no current open dispatch")
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is None:
        raise ValueError(f"missing dispatch '{flow.current_open_dispatch_id}'")
    latest_checkpoint = await latest_checkpoint_for_attempt(session, state.current_attempt)
    _ensure_checkpoint_writable(state, latest_checkpoint)
    checkpoint_write = payload.checkpoint
    checkpoint_id = runtime_checkpoint_id(
        state.current_attempt.attempt_id,
        await _checkpoint_sequence(session, state.current_attempt.attempt_id),
    )
    paths = await load_task_root_paths(session, task_id)
    artifacts = await collect_checkpoint_artifacts(
        session,
        task_id=task_id,
        state=state,
        checkpoint_write=checkpoint_write,
        paths=paths,
    )
    _persist_checkpoint_row(
        session,
        checkpoint_id=checkpoint_id,
        state=state,
        checkpoint_write=checkpoint_write,
        produced_refs=artifacts.produced_refs,
        transient_refs=artifacts.transient_refs,
    )
    state.current_attempt.latest_checkpoint_id = checkpoint_id
    _persist_attempt_produced_refs(
        session,
        attempt_id=state.current_attempt.attempt_id,
        assignment_key=state.current_assignment.assignment_key,
        owner_node_key=state.current_node.node_key,
        produced_refs=artifacts.produced_refs,
    )
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    _update_delivery_state_for_checkpoint(
        delivery_state,
        checkpoint_kind=checkpoint_write.checkpoint_kind,
    )
    await session.flush()
    _queue_checkpoint_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        owner_node_key=state.current_node.node_key,
        attempt_id=state.current_attempt.attempt_id,
        produced_refs=artifacts.produced_refs,
        produced_file_copies=artifacts.produced_file_copies,
        transient_file_copies=artifacts.transient_file_copies,
        delivery_state=delivery_state,
    )
    checkpoint_ref = CheckpointFileRef(
        path=paths.attempts_path / state.current_attempt.attempt_id / "latest-checkpoint.md",
        description="Latest checkpoint for the current attempt.",
    )
    return CheckpointRead(
        attempt_id=state.current_attempt.attempt_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ref=checkpoint_ref,
        latest_checkpoint_ref=checkpoint_ref,
    )


__all__ = ["record_checkpoint"]
