from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import (
    AttemptCheckpointModel,
    AttemptProducedRefModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
)
from autoclaw.runtime.checkpoint.artifacts import collect_checkpoint_artifacts
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    CheckpointFileRef,
    CheckpointKind,
    CheckpointOutcome,
    CheckpointRead,
    CheckpointWrite,
    CheckpointWriteBody,
    EvidenceRef,
    NodeKind,
    TaskEventSource,
    TaskEventType,
)
from autoclaw.runtime.errors import (
    illegal_caller_error,
    illegal_state_error,
    missing_resource_error,
)
from autoclaw.runtime.flow.queries import latest_checkpoint_for_attempt
from autoclaw.runtime.ids import artifact_publication_id
from autoclaw.runtime.ids import checkpoint_id as runtime_checkpoint_id
from autoclaw.runtime.post_commit.cases import stage_checkpoint_outputs
from autoclaw.runtime.projection.runtime_state import (
    CurrentRuntimeState,
    current_runtime_state,
)
from autoclaw.runtime.task_events import append_task_event
from autoclaw.runtime.task_root.reads import load_task_root_paths


async def record_checkpoint(
    session: AsyncSession,
    task_id: str,
    payload: CheckpointWrite,
    *,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> CheckpointRead:
    state = state or await current_runtime_state(session, task_id)
    dispatch = await _load_checkpoint_dispatch(session, state=state, dispatch=dispatch)
    checkpoint_write = payload.checkpoint
    latest_checkpoint = await latest_checkpoint_for_attempt(session, state.current_attempt)
    _ensure_checkpoint_writable(state, latest_checkpoint, checkpoint_write)
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
    checkpoint = _persist_checkpoint_row(
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
    checkpoint_ref = CheckpointFileRef(
        path=paths.attempts_path / state.current_attempt.attempt_id / "latest-checkpoint.md",
        description="Latest checkpoint for the current attempt.",
    )
    await _append_checkpoint_recorded_event(
        session,
        task_id=task_id,
        state=state,
        dispatch=dispatch,
        checkpoint=checkpoint,
        checkpoint_write=checkpoint_write,
        produced_refs=artifacts.produced_refs,
        transient_refs=artifacts.transient_refs,
        checkpoint_ref=checkpoint_ref,
    )
    _stage_checkpoint_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        owner_node_key=state.current_node.node_key,
        attempt_id=state.current_attempt.attempt_id,
        produced_refs=artifacts.produced_refs,
        produced_file_copies=artifacts.produced_file_copies,
        transient_file_copies=artifacts.transient_file_copies,
    )
    return _checkpoint_read(
        attempt_id=state.current_attempt.attempt_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ref=checkpoint_ref,
    )


async def _load_checkpoint_dispatch(
    session: AsyncSession,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel | None,
) -> DispatchTurnModel:
    if dispatch is not None:
        return dispatch
    flow = state.flow
    if flow.current_open_dispatch_id is None:
        raise illegal_state_error("no current open dispatch")
    dispatch = await session.get(
        DispatchTurnModel,
        flow.current_open_dispatch_id,
        options=(raiseload("*"),),
    )
    if dispatch is None:
        raise missing_resource_error(f"missing dispatch '{flow.current_open_dispatch_id}'")
    return dispatch


def _checkpoint_read(
    *,
    attempt_id: str,
    checkpoint_id: str,
    checkpoint_ref: CheckpointFileRef,
) -> CheckpointRead:
    return CheckpointRead(
        attempt_id=attempt_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ref=checkpoint_ref,
        latest_checkpoint_ref=checkpoint_ref,
    )


def _ensure_checkpoint_writable(
    state: CurrentRuntimeState,
    latest_checkpoint: AttemptCheckpointModel | None,
    checkpoint_write: CheckpointWriteBody,
) -> None:
    if (
        state.current_attempt.closed_at is not None
        or state.current_attempt.terminal_outcome is not None
    ):
        raise illegal_state_error("closed attempt cannot record new checkpoints")
    if (
        latest_checkpoint is not None
        and latest_checkpoint.checkpoint_kind == CheckpointKind.TERMINAL.value
    ):
        raise illegal_state_error("attempt already has a terminal checkpoint")
    _ensure_checkpoint_outcome_allowed_for_node(state, checkpoint_write)


def _ensure_checkpoint_outcome_allowed_for_node(
    state: CurrentRuntimeState,
    checkpoint_write: CheckpointWriteBody,
) -> None:
    if (
        checkpoint_write.checkpoint_kind == CheckpointKind.TERMINAL
        and checkpoint_write.outcome == CheckpointOutcome.RETRY
        and state.current_node.structural_kind != NodeKind.WORKER.value
    ):
        raise illegal_caller_error("parent/root retry checkpoint is illegal")


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
) -> AttemptCheckpointModel:
    checkpoint = AttemptCheckpointModel(
        checkpoint_id=checkpoint_id,
        assignment_id=state.current_assignment.assignment_id,
        assignment_key=state.current_assignment.assignment_key,
        attempt_id=state.current_attempt.attempt_id,
        flow_node_id=state.current_assignment.flow_node_id,
        node_key=state.current_node.node_key,
        checkpoint_kind=checkpoint_write.checkpoint_kind.value,
        outcome=(checkpoint_write.outcome.value if checkpoint_write.outcome is not None else None),
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
    session.add(checkpoint)
    return checkpoint


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


async def _append_checkpoint_recorded_event(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    checkpoint: AttemptCheckpointModel,
    checkpoint_write: CheckpointWriteBody,
    produced_refs: list[EvidenceRef],
    transient_refs: tuple[EvidenceRef, ...],
    checkpoint_ref: CheckpointFileRef,
) -> None:
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.CHECKPOINT_RECORDED,
        event_source=TaskEventSource.NODE,
        occurred_at=checkpoint.recorded_at,
        flow_revision_id=state.flow_revision.flow_revision_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=state.current_attempt.attempt_id,
        node_key=state.current_node.node_key,
        payload={
            "checkpoint_id": checkpoint.checkpoint_id,
            "checkpoint_kind": checkpoint_write.checkpoint_kind.value,
            "outcome": (
                checkpoint_write.outcome.value if checkpoint_write.outcome is not None else None
            ),
            "summary": checkpoint_write.handoff.summary,
            "next_step": checkpoint_write.handoff.next_step,
            "blockers": list(checkpoint_write.handoff.blockers),
            "risks": list(checkpoint_write.handoff.risks),
            "produced_artifacts": [ref.model_dump(mode="json") for ref in produced_refs],
            "transient_refs": [ref.model_dump(mode="json") for ref in transient_refs],
            "task_memory_search_hints": list(checkpoint_write.task_memory_search_hints),
            "checkpoint_ref": checkpoint_ref.model_dump(mode="json"),
            "latest_checkpoint_ref": checkpoint_ref.model_dump(mode="json"),
        },
    )


def _stage_checkpoint_outputs(
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
    stage_checkpoint_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch_id,
        owner_node_key=owner_node_key,
        attempt_id=attempt_id,
        produced_refs=produced_refs,
        produced_file_copies=produced_file_copies,
        transient_file_copies=transient_file_copies,
    )


__all__ = ["record_checkpoint"]
