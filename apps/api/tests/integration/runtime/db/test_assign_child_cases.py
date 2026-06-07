from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.persistence import (
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
)
from autoclaw.runtime import CheckpointOutcome
from sqlalchemy import select
from tests.integration.runtime.contracts.pending_materialization_support import (
    artifact_handoff_workflow,
)
from tests.integration.runtime.db.actions import (
    assign_child,
    assign_child_on_current_flow,
    record_terminal_checkpoint_and_continue,
    yield_child_assignment,
)
from tests.integration.runtime.db.context import (
    RuntimeDatabaseContext,
    launch_runtime_case,
    require_flow_model,
    require_flow_node,
    runtime_database_context,
    write_task_file,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def open_implementation_subtree(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> None:
    await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key="implementation_subtree",
        summary="Open the implementation subtree.",
        instruction="Dispatch only the implementation subtree.",
    )


async def complete_artifact_handoff_implementation(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> None:
    await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key="implement_change",
        summary="Implement the scoped change.",
        instruction="Publish the implementation evidence.",
    )
    returned_root = await record_terminal_checkpoint_and_continue(
        context,
        task_id=task_id,
        outcome=CheckpointOutcome.GREEN,
        summary="Implementation completed.",
        next_step="Root should review the current implementation evidence.",
        artifacts=[
            (
                "change_patch",
                write_task_file(
                    context.paths.task_root,
                    "workspace/change_patch.diff",
                    "diff --git a b",
                ),
            ),
            (
                "verification_report",
                write_task_file(
                    context.paths.task_root,
                    "workspace/verification_report.md",
                    "verification ok",
                ),
            ),
        ],
    )
    assert returned_root.current_node_key == "root"


async def assert_missing_backing_file_rejected(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await require_flow_model(session, task_id=task_id)
        assert flow.active_flow_revision_id is not None
        review_node = await require_flow_node(
            session,
            flow_revision_id=flow.active_flow_revision_id,
            node_key="review_change",
        )
        assert review_node.consumes_json is not None
        artifact_selectors = cast(
            list[dict[str, Any]],
            review_node.consumes_json["artifacts"],
        )
        assert any(selector["slot"] == "change_patch" for selector in artifact_selectors)
        publication = await session.scalar(
            select(ArtifactPublicationModel).where(
                ArtifactPublicationModel.task_id == task_id,
                ArtifactPublicationModel.owner_node_key == "implement_change",
                ArtifactPublicationModel.slot == "change_patch",
                ArtifactPublicationModel.version == 1,
            )
        )
        assert publication is not None
        artifact_path = Path(publication.path)
        assert await asyncio.to_thread(artifact_path.is_file)
        await asyncio.to_thread(artifact_path.unlink)
        with pytest.raises(
            ValueError,
            match="missing current artifact for slot 'change_patch'",
        ):
            await assign_child(
                session,
                task_id=task_id,
                expected_structural_revision_id=flow.active_flow_revision_id,
                child_node_key="review_change",
                summary="Review the current implementation evidence.",
                instruction="Publish only the bounded review report.",
            )


async def test_assign_child_uses_relational_direct_child_authority(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-relational-assign-child",
    ) as context:
        task_id = "task_relational_assign_child"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="runtime-relational-assign-child",
        )
        await open_implementation_subtree(context, task_id=task_id)
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.active_flow_revision_id is not None
            child_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="implement_change",
            )
            child_node.parent_node_key = "root"
            await session.commit()

        assign_success = await assign_child_on_current_flow(
            context,
            task_id=task_id,
            child_node_key="investigate_issue",
            summary="Investigate the scoped issue.",
            instruction="Publish the investigation findings.",
        )
        async with context.session_factory() as session:
            assignment = await session.scalar(
                select(AssignmentModel).where(
                    AssignmentModel.assignment_key == assign_success.target_assignment_key
                )
            )
            assert assignment is not None
            assert assignment.node_key == "investigate_issue"


async def test_assign_child_blocks_open_overwrite_and_supersedes_closed_assignment(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-assign-child-overwrite",
    ) as context:
        task_id = "task_assign_child_overwrite"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="runtime-assign-child-overwrite",
        )
        await open_implementation_subtree(context, task_id=task_id)
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.active_flow_revision_id is not None
            first_assign = await assign_child(
                session,
                task_id=task_id,
                expected_structural_revision_id=flow.active_flow_revision_id,
                child_node_key="investigate_issue",
                summary="Investigate the scoped issue.",
                instruction="Publish the investigation findings.",
            )
            await session.commit()
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.current_open_dispatch_id is not None
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            assert dispatch is not None
            dispatch.staged_child_assignment_id = None
            await session.commit()
            assert flow.active_flow_revision_id is not None
            with pytest.raises(
                ValueError,
                match="assign_child cannot overwrite open child assignment",
            ):
                await assign_child(
                    session,
                    task_id=task_id,
                    expected_structural_revision_id=flow.active_flow_revision_id,
                    child_node_key="investigate_issue",
                    summary="Retry the same child while it is still open.",
                    instruction="This must be rejected.",
                )
            first_assignment = await session.scalar(
                select(AssignmentModel).where(
                    AssignmentModel.assignment_key == first_assign.target_assignment_key
                )
            )
            assert first_assignment is not None
            first_attempt = await session.get(AttemptModel, first_assign.target_attempt_id)
            assert first_attempt is not None
            first_attempt.status = "succeeded"
            first_attempt.terminal_outcome = "green"
            first_attempt.closed_at = first_attempt.created_at
            assert flow.active_flow_revision_id is not None
            second_assign = await assign_child(
                session,
                task_id=task_id,
                expected_structural_revision_id=flow.active_flow_revision_id,
                child_node_key="investigate_issue",
                summary="Stage a legal superseding child assignment.",
                instruction="Publish the new investigation findings.",
            )
            await session.commit()
            assert second_assign.target_assignment_key != first_assign.target_assignment_key
            assert first_assignment.superseded_at is not None


async def test_assign_child_rejects_missing_backing_current_artifact_file(
    tmp_path: Path,
) -> None:
    workflow_definition = artifact_handoff_workflow()
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-assign-child-missing-backing-file",
    ) as context:
        task_id = "task_assign_child_missing_backing_file"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version="runtime-assign-child-missing-backing-file",
            workflow_definition=workflow_definition,
        )
        await complete_artifact_handoff_implementation(context, task_id=task_id)
        await assert_missing_backing_file_rejected(context, task_id=task_id)
