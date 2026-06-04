from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from autoclaw.runtime import (
    CheckpointKind,
    CheckpointOutcome,
    EgressBoundary,
    record_checkpoint,
)
from autoclaw.runtime.control.flow.service import runtime_flow_read
from autoclaw.runtime.effects import drive_runtime_once
from autoclaw.schemas.runtime import (
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ProducedArtifactClaim,
)
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.phase3.db.context import (
    Phase3RuntimeContext,
    accept_boundary_and_continue,
    advance_boundary_on_current_flow,
)

ArtifactSpec = tuple[str, Path]


def produced_artifact_claims(
    artifacts: Sequence[ArtifactSpec],
) -> tuple[ProducedArtifactClaim, ...]:
    return tuple(ProducedArtifactClaim(slot=slot, path=path) for slot, path in artifacts)


async def record_progress_checkpoint_for_session(
    session: AsyncSession,
    *,
    task_id: str,
    summary: str,
    next_step: str,
    artifacts: Sequence[ArtifactSpec] = (),
) -> None:
    await record_checkpoint(
        session,
        task_id,
        CheckpointWrite(
            checkpoint=CheckpointWriteBody(
                checkpoint_kind=CheckpointKind.PROGRESS,
                outcome=None,
                handoff=CheckpointHandoffRead(summary=summary, next_step=next_step),
                produced_artifacts=produced_artifact_claims(artifacts),
            )
        ),
    )


async def record_terminal_checkpoint_for_session(
    session: AsyncSession,
    *,
    task_id: str,
    outcome: CheckpointOutcome,
    summary: str,
    next_step: str,
    artifacts: Sequence[ArtifactSpec] = (),
) -> None:
    await record_checkpoint(
        session,
        task_id,
        CheckpointWrite(
            checkpoint=CheckpointWriteBody(
                checkpoint_kind=CheckpointKind.TERMINAL,
                outcome=outcome,
                handoff=CheckpointHandoffRead(summary=summary, next_step=next_step),
                produced_artifacts=produced_artifact_claims(artifacts),
            )
        ),
    )


def boundary_for_outcome(outcome: CheckpointOutcome) -> EgressBoundary:
    if outcome is CheckpointOutcome.GREEN:
        return EgressBoundary.GREEN
    if outcome is CheckpointOutcome.RETRY:
        return EgressBoundary.RETRY
    return EgressBoundary.BLOCKED


async def record_terminal_checkpoint_and_continue(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    outcome: CheckpointOutcome,
    summary: str,
    next_step: str,
    artifacts: Sequence[ArtifactSpec] = (),
) -> Any:
    async with context.session_factory() as session:
        await record_terminal_checkpoint_for_session(
            session,
            task_id=task_id,
            outcome=outcome,
            summary=summary,
            next_step=next_step,
            artifacts=artifacts,
        )
        await session.commit()
    await drive_runtime_once(task_id=task_id)
    async with context.session_factory() as session:
        return await accept_boundary_and_continue(
            session,
            task_id=task_id,
            boundary=boundary_for_outcome(outcome),
        )


async def yield_child_assignment(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
    assign_child_on_current_flow: Any,
) -> Any:
    await assign_child_on_current_flow(
        context,
        task_id=task_id,
        child_node_key=child_node_key,
        summary=summary,
        instruction=instruction,
    )
    yielded = await advance_boundary_on_current_flow(
        context,
        task_id=task_id,
        boundary=EgressBoundary.YIELD,
    )
    async with context.session_factory() as session:
        reread = await runtime_flow_read(session, task_id)
        assert reread.current_node_key == child_node_key
        assert reread.active_attempt_id is not None
    return yielded


async def run_child_outcome(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child_node_key: str,
    assignment_summary: str,
    assignment_instruction: str,
    outcome: CheckpointOutcome,
    handoff_summary: str,
    next_step: str,
    artifacts: Sequence[ArtifactSpec] = (),
    assign_child_on_current_flow: Any,
) -> Any:
    await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key=child_node_key,
        summary=assignment_summary,
        instruction=assignment_instruction,
        assign_child_on_current_flow=assign_child_on_current_flow,
    )
    result = await record_terminal_checkpoint_and_continue(
        context,
        task_id=task_id,
        outcome=outcome,
        summary=handoff_summary,
        next_step=next_step,
        artifacts=artifacts,
    )
    await drive_runtime_once(task_id=task_id)
    return result
