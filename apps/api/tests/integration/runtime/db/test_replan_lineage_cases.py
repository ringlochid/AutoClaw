from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from autoclaw.persistence import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowNodeModel,
    FlowRevisionModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.runtime.db.actions import (
    add_child_on_current_flow,
    assign_child,
    record_progress_checkpoint_for_session,
    remove_child_on_current_flow,
    update_child_on_current_flow,
)
from tests.integration.runtime.db.context import (
    RuntimeDatabaseContext,
    launch_runtime_case,
    require_flow_model,
    require_flow_node,
    runtime_database_context,
    write_task_file,
)
from tests.integration.runtime.db.workflows import root_replan_publication_workflow

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


@dataclass(frozen=True)
class RootLineageState:
    flow_id: str
    revision_id: str
    assignment_id: str
    attempt_id: str
    dispatch_id: str


async def read_root_lineage(
    session: AsyncSession,
    *,
    task_id: str,
) -> RootLineageState:
    flow = await require_flow_model(session, task_id=task_id)
    assert flow.active_flow_revision_id is not None
    assert flow.current_open_dispatch_id is not None
    root_node = await require_flow_node(
        session,
        flow_revision_id=flow.active_flow_revision_id,
        node_key="root",
    )
    assert root_node.current_assignment_id is not None
    assignment = await session.get(AssignmentModel, root_node.current_assignment_id)
    assert assignment is not None
    assert assignment.current_attempt_id is not None
    return RootLineageState(
        flow_id=flow.flow_id,
        revision_id=flow.active_flow_revision_id,
        assignment_id=assignment.assignment_id,
        attempt_id=assignment.current_attempt_id,
        dispatch_id=flow.current_open_dispatch_id,
    )


async def assert_revision_and_root_rebound(
    session: AsyncSession,
    *,
    task_id: str,
    revision_id: str,
    parent_revision_id: str,
    cause: str,
    lineage: RootLineageState,
) -> None:
    flow = await require_flow_model(session, task_id=task_id)
    revision = await session.get(FlowRevisionModel, revision_id)
    assert revision is not None
    assert revision.parent_flow_revision_id == parent_revision_id
    assert revision.source_compiled_plan_id == flow.compiled_plan_id
    assert revision.cause == cause
    assert revision.created_by_dispatch_id == flow.current_open_dispatch_id
    root_node = await require_flow_node(
        session,
        flow_revision_id=revision_id,
        node_key="root",
    )
    assert root_node.flow_id == lineage.flow_id
    assert root_node.current_assignment_id == lineage.assignment_id
    assignment = await session.get(AssignmentModel, lineage.assignment_id)
    assert assignment is not None
    assert assignment.flow_revision_id == revision_id
    assert assignment.flow_node_id == root_node.flow_node_id
    attempt = await session.get(AttemptModel, lineage.attempt_id)
    assert attempt is not None
    assert attempt.flow_node_id == root_node.flow_node_id
    dispatch = await session.get(DispatchTurnModel, lineage.dispatch_id)
    assert dispatch is not None
    assert dispatch.flow_revision_id == revision_id
    assert dispatch.flow_node_id == root_node.flow_node_id


async def update_and_assert_root_rebound(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
    lineage: RootLineageState,
    parent_revision_id: str,
    child_node_key: str,
    description: str,
) -> str:
    updated = await update_child_on_current_flow(
        context,
        task_id=task_id,
        child_node_key=child_node_key,
        description=description,
    )
    revision_id = updated.flow.active_flow_revision_id
    assert revision_id is not None
    async with context.session_factory() as session:
        await assert_revision_and_root_rebound(
            session,
            task_id=task_id,
            revision_id=revision_id,
            parent_revision_id=parent_revision_id,
            cause="update_child",
            lineage=lineage,
        )
    return cast(str, revision_id)


async def add_and_assert_root_rebound(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
    lineage: RootLineageState,
    parent_revision_id: str,
) -> str:
    added = await add_child_on_current_flow(
        context,
        task_id=task_id,
        child={
            "id": "qa_sweep",
            "role": "architect",
            "description": "Run a bounded QA sweep over the subtree.",
        },
    )
    revision_id = added.flow.active_flow_revision_id
    assert revision_id is not None
    async with context.session_factory() as session:
        await assert_revision_and_root_rebound(
            session,
            task_id=task_id,
            revision_id=revision_id,
            parent_revision_id=parent_revision_id,
            cause="add_child",
            lineage=lineage,
        )
        qa_node = await require_flow_node(
            session,
            flow_revision_id=revision_id,
            node_key="qa_sweep",
        )
        assert qa_node.flow_id == lineage.flow_id
    return cast(str, revision_id)


async def remove_and_assert_root_rebound(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
    lineage: RootLineageState,
    parent_revision_id: str,
) -> str:
    removed = await remove_child_on_current_flow(
        context,
        task_id=task_id,
        child_node_key="qa_sweep",
    )
    revision_id = removed.flow.active_flow_revision_id
    assert revision_id is not None
    async with context.session_factory() as session:
        await assert_revision_and_root_rebound(
            session,
            task_id=task_id,
            revision_id=revision_id,
            parent_revision_id=parent_revision_id,
            cause="remove_child",
            lineage=lineage,
        )
        removed_qa = await session.scalar(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == revision_id,
                FlowNodeModel.node_key == "qa_sweep",
            )
        )
        assert removed_qa is None
    return cast(str, revision_id)


async def record_root_decision_note(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
    relative_path: str,
    content: str,
    summary: str,
    next_step: str,
) -> None:
    async with context.session_factory() as session:
        note = write_task_file(context.paths.task_root, relative_path, content)
        await record_progress_checkpoint_for_session(
            session,
            task_id=task_id,
            summary=summary,
            next_step=next_step,
            artifacts=[("decision_note", note)],
        )
        await session.commit()


async def assert_root_decision_note_lineage(
    session: AsyncSession,
    *,
    task_id: str,
    lineage: RootLineageState,
    revision_id: str,
    current_version: int,
) -> None:
    root_node = await require_flow_node(
        session,
        flow_revision_id=revision_id,
        node_key="root",
    )
    attempt = await session.get(AttemptModel, lineage.attempt_id)
    assert attempt is not None
    assert attempt.flow_node_id == root_node.flow_node_id
    dispatch = await session.get(DispatchTurnModel, lineage.dispatch_id)
    assert dispatch is not None
    assert dispatch.flow_revision_id == revision_id
    assert dispatch.flow_node_id == root_node.flow_node_id
    checkpoints = list(
        await session.scalars(
            select(AttemptCheckpointModel)
            .where(AttemptCheckpointModel.attempt_id == lineage.attempt_id)
            .order_by(AttemptCheckpointModel.recorded_at.asc())
        )
    )
    assert checkpoints
    assert {checkpoint.flow_node_id for checkpoint in checkpoints} == {root_node.flow_node_id}
    publication = await session.scalar(
        select(ArtifactPublicationModel).where(
            ArtifactPublicationModel.task_id == task_id,
            ArtifactPublicationModel.owner_node_key == "root",
            ArtifactPublicationModel.slot == "decision_note",
            ArtifactPublicationModel.version == current_version,
        )
    )
    assert publication is not None
    assert publication.flow_node_id == root_node.flow_node_id
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.owner_node_key == "root",
            ArtifactCurrentPointerModel.slot == "decision_note",
        )
    )
    assert pointer is not None
    assert pointer.current_version == current_version
    assert pointer.flow_node_id == root_node.flow_node_id


async def test_structural_replan_and_assign_child_persist_lineage(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-lineage",
    ) as context:
        task_id = "task_runtime_lineage"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="runtime-lineage",
        )
        async with context.session_factory() as session:
            initial = await read_root_lineage(session, task_id=task_id)
        updated_revision_id = await update_and_assert_root_rebound(
            context,
            task_id=task_id,
            lineage=initial,
            parent_revision_id=initial.revision_id,
            child_node_key="release_closure",
            description="Run the refreshed release closure check.",
        )
        added_revision_id = await add_and_assert_root_rebound(
            context,
            task_id=task_id,
            lineage=initial,
            parent_revision_id=updated_revision_id,
        )
        removed_revision_id = await remove_and_assert_root_rebound(
            context,
            task_id=task_id,
            lineage=initial,
            parent_revision_id=added_revision_id,
        )
        async with context.session_factory() as session:
            assign_success = await assign_child(
                session,
                task_id=task_id,
                expected_structural_revision_id=removed_revision_id,
                child_node_key="implementation_subtree",
                summary="Stage the implementation subtree.",
                instruction="Publish only the subtree assignment basis.",
            )
            implementation_node = await require_flow_node(
                session,
                flow_revision_id=removed_revision_id,
                node_key="implementation_subtree",
            )
            staged_assignment = await session.scalar(
                select(AssignmentModel).where(
                    AssignmentModel.assignment_key == assign_success.target_assignment_key
                )
            )
            await session.commit()
            assert staged_assignment is not None
            assert staged_assignment.flow_id == initial.flow_id
            assert staged_assignment.flow_revision_id == removed_revision_id
            assert staged_assignment.flow_node_id == implementation_node.flow_node_id
            assert staged_assignment.created_by_dispatch_id == initial.dispatch_id


async def test_structural_replan_rebinds_same_attempt_publication_and_checkpoint_lineage(
    tmp_path: Path,
) -> None:
    workflow_definition = root_replan_publication_workflow()
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-replan-publication",
    ) as context:
        task_id = "task_replan_publication"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version="runtime-replan-publication",
            workflow_definition=workflow_definition,
        )
        async with context.session_factory() as session:
            initial = await read_root_lineage(session, task_id=task_id)
        await record_root_decision_note(
            context,
            task_id=task_id,
            relative_path="workspace/decision-note-v1.md",
            content="decision note v1",
            summary="Recorded the first root decision note.",
            next_step="Refresh the child structure before finalizing.",
        )
        updated_revision_id = await update_and_assert_root_rebound(
            context,
            task_id=task_id,
            lineage=initial,
            parent_revision_id=initial.revision_id,
            child_node_key="review_step",
            description="Refresh the review step after progress evidence.",
        )
        async with context.session_factory() as session:
            await assert_root_decision_note_lineage(
                session,
                task_id=task_id,
                lineage=initial,
                revision_id=updated_revision_id,
                current_version=1,
            )
        await record_root_decision_note(
            context,
            task_id=task_id,
            relative_path="workspace/decision-note-v2.md",
            content="decision note v2",
            summary="Recorded the refreshed root decision note.",
            next_step="Keep the current root attempt open.",
        )
        async with context.session_factory() as session:
            await assert_root_decision_note_lineage(
                session,
                task_id=task_id,
                lineage=initial,
                revision_id=updated_revision_id,
                current_version=2,
            )
