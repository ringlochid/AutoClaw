from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.persistence import ArtifactPublicationModel, AssignmentModel, DispatchTurnModel
from autoclaw.runtime import CheckpointOutcome, EgressBoundary, runtime_flow_read
from autoclaw.runtime.post_commit import drive_runtime_once
from sqlalchemy import select
from tests.integration.runtime.db.actions import (
    record_progress_checkpoint_for_session,
    record_terminal_checkpoint_for_session,
    release_blocked,
    release_green,
    run_child_outcome,
    yield_child_assignment,
)
from tests.integration.runtime.db.context import (
    RuntimeDatabaseContext,
    accept_boundary_and_continue,
    launch_runtime_case,
    require_flow_model,
    runtime_database_context,
    write_task_file,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def _launch_minimal_change_case(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
    compiler_version: str,
) -> None:
    await launch_runtime_case(
        context,
        task_id=task_id,
        workflow_key="minimal-implement-change",
        compiler_version=compiler_version,
    )


async def _run_minimal_implement_return_root(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
    patch_path: str,
    verification_path: str,
) -> Any:
    return await run_child_outcome(
        context,
        task_id=task_id,
        child_node_key="implement_change",
        assignment_summary="Implement the bounded change.",
        assignment_instruction="Publish the patch and verification evidence only.",
        outcome=CheckpointOutcome.GREEN,
        handoff_summary="Minimal implementation completed.",
        next_step="Root should verify the bounded change and close the flow.",
        artifacts=[
            (
                "change_patch",
                write_task_file(context.paths.task_root, patch_path, "diff --git a b"),
            ),
            (
                "verification_report",
                write_task_file(context.paths.task_root, verification_path, "verification ok"),
            ),
        ],
    )


async def _stage_release_green_precondition(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> str:
    async with context.session_factory() as session:
        flow = await require_flow_model(session, task_id=task_id)
        assert flow.active_flow_revision_id is not None
        await release_green(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
        )
        assert flow.current_open_dispatch_id is not None
        await session.commit()
        return flow.current_open_dispatch_id


async def _publish_two_patch_versions_and_return_root(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> None:
    await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key="implement_change",
        summary="Implement the bounded change.",
        instruction="Publish the patch and verification evidence only.",
    )
    async with context.session_factory() as session:
        await record_progress_checkpoint_for_session(
            session,
            task_id=task_id,
            summary="Published the first patch draft.",
            next_step="Publish the final patch and verification.",
            artifacts=[
                (
                    "change_patch",
                    write_task_file(
                        context.paths.task_root,
                        "workspace/older_ref_patch_v1.diff",
                        "diff --git a b\n+v1\n",
                    ),
                )
            ],
        )
        await record_terminal_checkpoint_for_session(
            session,
            task_id=task_id,
            outcome=CheckpointOutcome.GREEN,
            summary="Published the final patch and verification.",
            next_step="Root should verify and close.",
            artifacts=[
                (
                    "change_patch",
                    write_task_file(
                        context.paths.task_root,
                        "workspace/older_ref_patch_v2.diff",
                        "diff --git a b\n+v2\n",
                    ),
                ),
                (
                    "verification_report",
                    write_task_file(
                        context.paths.task_root,
                        "workspace/older_ref_verification.md",
                        "verification ok",
                    ),
                ),
            ],
        )
        await session.commit()
    await drive_runtime_once(task_id=task_id)
    async with context.session_factory() as session:
        await accept_boundary_and_continue(
            session,
            task_id=task_id,
            boundary=EgressBoundary.GREEN,
        )
        await session.commit()
    await drive_runtime_once(task_id=task_id)


async def _append_older_patch_ref_to_child_assignment(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> None:
    async with context.session_factory() as session:
        older_publication = await session.scalar(
            select(ArtifactPublicationModel).where(
                ArtifactPublicationModel.task_id == task_id,
                ArtifactPublicationModel.owner_node_key == "implement_change",
                ArtifactPublicationModel.slot == "change_patch",
                ArtifactPublicationModel.version == 1,
            )
        )
        assert older_publication is not None
        child_assignment = await session.scalar(
            select(AssignmentModel).where(
                AssignmentModel.task_id == task_id,
                AssignmentModel.node_key == "implement_change",
            )
        )
        assert child_assignment is not None
        child_assignment.consumes_json = [
            *child_assignment.consumes_json,
            {
                "kind": "artifact",
                "slot": "change_patch",
                "version": 1,
                "path": older_publication.path,
                "description": "Older pinned patch evidence kept for audit context.",
            },
        ]
        await session.commit()


async def test_root_terminal_green_checkpoint_requires_release_green_preflight(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-green-preflight",
    ) as context:
        task_id = "task_root_green_preflight"
        await _launch_minimal_change_case(
            context,
            task_id=task_id,
            compiler_version="runtime-root-green-preflight",
        )
        await _run_minimal_implement_return_root(
            context,
            task_id=task_id,
            patch_path="workspace/preflight_patch.diff",
            verification_path="workspace/preflight_verification.md",
        )
        async with context.session_factory() as session:
            with pytest.raises(
                ValueError,
                match="terminal green checkpoint requires release_green first",
            ):
                await record_terminal_checkpoint_for_session(
                    session,
                    task_id=task_id,
                    outcome=CheckpointOutcome.GREEN,
                    summary="Root tried to close green without release preflight.",
                    next_step="This checkpoint should be rejected.",
                )


async def test_terminal_checkpoint_supersession_resets_incompatible_release_precondition(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-terminal-supersession",
    ) as context:
        task_id = "task_root_terminal_supersession"
        await _launch_minimal_change_case(
            context,
            task_id=task_id,
            compiler_version="runtime-root-terminal-supersession",
        )
        await _run_minimal_implement_return_root(
            context,
            task_id=task_id,
            patch_path="workspace/supersession_patch.diff",
            verification_path="workspace/supersession_verification.md",
        )
        root_dispatch_id = await _stage_release_green_precondition(context, task_id=task_id)
        async with context.session_factory() as session:
            await record_terminal_checkpoint_for_session(
                session,
                task_id=task_id,
                outcome=CheckpointOutcome.GREEN,
                summary="Root initially marked the flow green.",
                next_step="A later check found this should block.",
            )
            await record_terminal_checkpoint_for_session(
                session,
                task_id=task_id,
                outcome=CheckpointOutcome.BLOCKED,
                summary="Root superseded green with a blocker.",
                next_step="Commit blocked release and close blocked.",
            )
            dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
            assert dispatch is not None
            assert dispatch.release_precondition_kind is None
            await session.commit()
        await drive_runtime_once(task_id=task_id)
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.active_flow_revision_id is not None
            await release_blocked(
                session,
                task_id=task_id,
                expected_structural_revision_id=flow.active_flow_revision_id,
            )
            completed = await accept_boundary_and_continue(
                session,
                task_id=task_id,
                boundary=EgressBoundary.BLOCKED,
            )
            assert completed.status.value == "blocked"


async def test_release_green_allows_older_pinned_artifact_ref_when_file_exists(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-older-artifact-ref",
    ) as context:
        task_id = "task_release_older_artifact_ref"
        await _launch_minimal_change_case(
            context,
            task_id=task_id,
            compiler_version="runtime-older-artifact-ref",
        )
        await _publish_two_patch_versions_and_return_root(context, task_id=task_id)
        await _append_older_patch_ref_to_child_assignment(context, task_id=task_id)
        async with context.session_factory() as session:
            flow = await runtime_flow_read(session, task_id)
            await release_green(
                session,
                task_id=task_id,
                expected_structural_revision_id=flow.active_flow_revision_id,
            )
