from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.runtime import (
    CheckpointKind,
    CheckpointOutcome,
    EgressBoundary,
    ParentRootToolName,
    call_parent_tool,
    record_checkpoint,
    runtime_flow_read,
)
from app.runtime.post_commit import wait_for_runtime_effects
from app.schemas.runtime import (
    AddChildPayload,
    AssignChildPayload,
    AssignChildSuccess,
    AssignmentIntent,
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ChildNodeDraft,
    ChildNodePatch,
    ParentToolCall,
    ProducedArtifactClaim,
    ReleaseBlockedPayload,
    ReleaseGreenPayload,
    RemoveChildPayload,
    UpdateChildPayload,
)
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.phase3_runtime_db_context import (
    Phase3RuntimeContext,
    accept_boundary_and_continue,
    advance_boundary_on_current_flow,
)

ArtifactSpec = tuple[str, Path]


async def assign_child(
    session: AsyncSession,
    *,
    task_id: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> AssignChildSuccess:
    result = await call_parent_tool(
        session,
        task_id,
        ParentRootToolName.ASSIGN_CHILD,
        ParentToolCall(
            tool_name=ParentRootToolName.ASSIGN_CHILD,
            payload=AssignChildPayload(
                child_node_key=child_node_key,
                assignment_intent=AssignmentIntent(
                    summary=summary,
                    instruction=instruction,
                ),
            ),
            expected_structural_revision_id=expected_structural_revision_id,
        ),
    )
    assert isinstance(result, AssignChildSuccess)
    return result


async def add_child(
    session: AsyncSession,
    *,
    task_id: str,
    expected_structural_revision_id: str,
    child: dict[str, Any],
) -> Any:
    return await call_parent_tool(
        session,
        task_id,
        ParentRootToolName.ADD_CHILD,
        ParentToolCall(
            tool_name=ParentRootToolName.ADD_CHILD,
            payload=AddChildPayload(child=ChildNodeDraft.model_validate(child)),
            expected_structural_revision_id=expected_structural_revision_id,
        ),
    )


async def update_child(
    session: AsyncSession,
    *,
    task_id: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    description: str,
) -> Any:
    return await call_parent_tool(
        session,
        task_id,
        ParentRootToolName.UPDATE_CHILD,
        ParentToolCall(
            tool_name=ParentRootToolName.UPDATE_CHILD,
            payload=UpdateChildPayload(
                child_node_key=child_node_key,
                patch=ChildNodePatch(description=description),
            ),
            expected_structural_revision_id=expected_structural_revision_id,
        ),
    )


async def remove_child(
    session: AsyncSession,
    *,
    task_id: str,
    expected_structural_revision_id: str,
    child_node_key: str,
) -> Any:
    return await call_parent_tool(
        session,
        task_id,
        ParentRootToolName.REMOVE_CHILD,
        ParentToolCall(
            tool_name=ParentRootToolName.REMOVE_CHILD,
            payload=RemoveChildPayload(child_node_key=child_node_key),
            expected_structural_revision_id=expected_structural_revision_id,
        ),
    )


async def release_green(
    session: AsyncSession,
    *,
    task_id: str,
    expected_structural_revision_id: str,
) -> Any:
    return await call_parent_tool(
        session,
        task_id,
        ParentRootToolName.RELEASE_GREEN,
        ParentToolCall(
            tool_name=ParentRootToolName.RELEASE_GREEN,
            payload=ReleaseGreenPayload(),
            expected_structural_revision_id=expected_structural_revision_id,
        ),
    )


async def release_blocked(
    session: AsyncSession,
    *,
    task_id: str,
    expected_structural_revision_id: str,
) -> Any:
    return await call_parent_tool(
        session,
        task_id,
        ParentRootToolName.RELEASE_BLOCKED,
        ParentToolCall(
            tool_name=ParentRootToolName.RELEASE_BLOCKED,
            payload=ReleaseBlockedPayload(),
            expected_structural_revision_id=expected_structural_revision_id,
        ),
    )


async def assign_child_on_current_flow(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> AssignChildSuccess:
    async with context.session_factory() as session:
        flow = await runtime_flow_read(session, task_id)
        result = await assign_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
            child_node_key=child_node_key,
            summary=summary,
            instruction=instruction,
        )
        await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    return result


async def add_child_on_current_flow(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child: dict[str, Any],
) -> Any:
    async with context.session_factory() as session:
        flow = await runtime_flow_read(session, task_id)
        result = await add_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
            child=child,
        )
        await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    return result


async def update_child_on_current_flow(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child_node_key: str,
    description: str,
) -> Any:
    async with context.session_factory() as session:
        flow = await runtime_flow_read(session, task_id)
        result = await update_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
            child_node_key=child_node_key,
            description=description,
        )
        await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    return result


async def remove_child_on_current_flow(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child_node_key: str,
) -> Any:
    async with context.session_factory() as session:
        flow = await runtime_flow_read(session, task_id)
        result = await remove_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
            child_node_key=child_node_key,
        )
        await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    return result


async def release_green_on_current_flow(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
) -> Any:
    async with context.session_factory() as session:
        flow = await runtime_flow_read(session, task_id)
        result = await release_green(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
        )
        await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    return result


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
    assert yielded.current_node_key == child_node_key
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
) -> Any:
    await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key=child_node_key,
        summary=assignment_summary,
        instruction=assignment_instruction,
    )
    return await record_terminal_checkpoint_and_continue(
        context,
        task_id=task_id,
        outcome=outcome,
        summary=handoff_summary,
        next_step=next_step,
        artifacts=artifacts,
    )
