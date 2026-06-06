from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from autoclaw.runtime import (
    CheckpointOutcome,
    ParentRootToolName,
    call_parent_tool,
    runtime_flow_read,
)
from autoclaw.runtime.contracts import (
    AddChildPayload,
    AssignChildPayload,
    AssignChildSuccess,
    AssignmentIntent,
    ChildNodeDraft,
    ChildNodePatch,
    ParentToolCall,
    ReleaseBlockedPayload,
    ReleaseGreenPayload,
    RemoveChildPayload,
    UpdateChildPayload,
)
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.runtime.db.checkpoints import (
    ArtifactSpec,
    record_progress_checkpoint_for_session,
    record_terminal_checkpoint_and_continue,
    record_terminal_checkpoint_for_session,
)
from tests.integration.runtime.db.checkpoints import (
    run_child_outcome as _run_child_outcome,
)
from tests.integration.runtime.db.checkpoints import (
    yield_child_assignment as _yield_child_assignment,
)
from tests.integration.runtime.db.context import (
    Phase3RuntimeContext,
)

__all__ = [
    "ArtifactSpec",
    "add_child",
    "add_child_on_current_flow",
    "assign_child",
    "assign_child_on_current_flow",
    "record_progress_checkpoint_for_session",
    "record_terminal_checkpoint_and_continue",
    "record_terminal_checkpoint_for_session",
    "release_blocked",
    "release_green",
    "release_green_on_current_flow",
    "remove_child",
    "remove_child_on_current_flow",
    "run_child_outcome",
    "update_child",
    "update_child_on_current_flow",
    "yield_child_assignment",
]


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
    return result


async def yield_child_assignment(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> Any:
    return await _yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key=child_node_key,
        summary=summary,
        instruction=instruction,
        assign_child_on_current_flow=assign_child_on_current_flow,
    )


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
    return await _run_child_outcome(
        context,
        task_id=task_id,
        child_node_key=child_node_key,
        assignment_summary=assignment_summary,
        assignment_instruction=assignment_instruction,
        outcome=outcome,
        handoff_summary=handoff_summary,
        next_step=next_step,
        artifacts=artifacts,
        assign_child_on_current_flow=assign_child_on_current_flow,
    )
