from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest
from autoclaw.persistence import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    AttemptProducedRefModel,
    DispatchTurnModel,
    FlowModel,
)
from autoclaw.runtime import CheckpointOutcome, EgressBoundary
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.runtime.db.actions import (
    record_progress_checkpoint_for_session,
    record_terminal_checkpoint_for_session,
    yield_child_assignment,
)
from tests.integration.runtime.db.context import (
    RuntimeDatabaseContext,
    accept_boundary_and_continue,
    launch_runtime_case,
    runtime_database_context,
    write_task_file,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def launch_minimal_worker(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> str:
    await launch_runtime_case(
        context,
        task_id=task_id,
        workflow_key="bounded-change",
        compiler_version="runtime-db",
    )
    yielded = await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key="implement_change",
        summary="Implement the bounded change.",
        instruction="Publish the patch and verification evidence only.",
    )
    assert yielded.active_attempt_id is not None
    return cast(str, yielded.active_attempt_id)


async def retry_dispatch_has_prompt_path(
    session: AsyncSession,
    *,
    task_id: str,
) -> bool:
    retry_dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.node_key == "implement_change",
            DispatchTurnModel.closed_at.is_(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    return retry_dispatch is not None and bool(retry_dispatch.prompt_path)


def write_checkpoint_sources(task_root: Path) -> tuple[Path, Path, Path]:
    return (
        write_task_file(task_root, "workspace/change_patch_v1.diff", "diff --git g h"),
        write_task_file(task_root, "workspace/change_patch_v2.diff", "diff --git g h v2"),
        write_task_file(task_root, "workspace/verification_v1.md", "verification ok"),
    )


def checkpoint_output_paths(
    task_root: Path,
    *,
    attempt_id: str,
) -> tuple[Path, Path, Path, Path]:
    return (
        task_root / "_runtime" / "attempts" / attempt_id / "latest-checkpoint.md",
        task_root
        / "outputs"
        / "artifacts"
        / "implement_change"
        / "change_patch"
        / "change_patch.v01.diff",
        task_root
        / "outputs"
        / "artifacts"
        / "implement_change"
        / "change_patch"
        / "change_patch.v02.diff",
        task_root
        / "outputs"
        / "artifacts"
        / "implement_change"
        / "verification_report"
        / "verification_report.v01.md",
    )


async def record_uncommitted_checkpoint_sequence(
    session: AsyncSession,
    *,
    task_id: str,
    patch_v1: Path,
    patch_v2: Path,
    verification: Path,
) -> None:
    await record_progress_checkpoint_for_session(
        session,
        task_id=task_id,
        summary="Published an initial patch draft.",
        next_step="Finish verification and publish the final patch.",
        artifacts=[("change_patch", patch_v1)],
    )
    await record_terminal_checkpoint_for_session(
        session,
        task_id=task_id,
        outcome=CheckpointOutcome.GREEN,
        summary="Published the final patch and verification note.",
        next_step="Return to root for release review.",
        artifacts=[("change_patch", patch_v2), ("verification_report", verification)],
    )


async def assert_precommit_checkpoint_state(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    patch_v1_source: Path,
    patch_v2_source: Path,
    verification_source: Path,
    patch_v1_destination: Path,
    patch_v2_destination: Path,
) -> None:
    checkpoints = list(
        await session.scalars(
            select(AttemptCheckpointModel)
            .where(AttemptCheckpointModel.attempt_id == attempt_id)
            .order_by(
                AttemptCheckpointModel.recorded_at.asc(),
                AttemptCheckpointModel.checkpoint_id.asc(),
            )
        )
    )
    assert len(checkpoints) == 2
    latest_checkpoint = checkpoints[-1]
    assert latest_checkpoint.produced_artifact_claims_json == [
        {"kind": "artifact", "slot": "change_patch", "path": str(patch_v2_source)},
        {
            "kind": "artifact",
            "slot": "verification_report",
            "path": str(verification_source),
        },
    ]
    assert [ref["slot"] for ref in latest_checkpoint.produced_artifacts_json] == [
        "change_patch",
        "verification_report",
    ]
    assert [ref["version"] for ref in latest_checkpoint.produced_artifacts_json] == [2, 1]
    attempt = await session.get(AttemptModel, attempt_id)
    assert attempt is not None
    assignment = await session.get(AssignmentModel, attempt.assignment_id)
    assert assignment is not None
    final_patch_publication = await session.scalar(
        select(ArtifactPublicationModel).where(
            ArtifactPublicationModel.task_id == task_id,
            ArtifactPublicationModel.flow_node_id == assignment.flow_node_id,
            ArtifactPublicationModel.owner_node_key == "implement_change",
            ArtifactPublicationModel.slot == "change_patch",
            ArtifactPublicationModel.version == 2,
        )
    )
    assert final_patch_publication is not None
    assert final_patch_publication.supersedes_version == 1
    assert final_patch_publication.supersedes_path == str(patch_v1_destination)
    current_pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.owner_node_key == "implement_change",
            ArtifactCurrentPointerModel.slot == "change_patch",
        )
    )
    assert current_pointer is not None
    assert current_pointer.flow_node_id == assignment.flow_node_id
    assert current_pointer.current_path == str(patch_v2_destination)
    assert current_pointer.supersedes_path == str(patch_v1_destination)
    produced_ref = await session.scalar(
        select(AttemptProducedRefModel).where(
            AttemptProducedRefModel.attempt_id == attempt_id,
            AttemptProducedRefModel.slot == "change_patch",
            AttemptProducedRefModel.version == 2,
        )
    )
    assert produced_ref is not None
    assert produced_ref.owner_node_key == "implement_change"
    assert produced_ref.assignment_key == assignment.assignment_key
    assert produced_ref.became_current is True
    assert await asyncio.to_thread(patch_v1_source.is_file)


async def test_record_checkpoint_defers_artifact_and_projection_files_until_commit(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(tmp_path, task_root_name="task-root") as context:
        task_id = "task_2026_0047"
        attempt_id = await launch_minimal_worker(context, task_id=task_id)
        latest_projection, patch_v1_destination, patch_v2_destination, verification_destination = (
            checkpoint_output_paths(context.paths.task_root, attempt_id=attempt_id)
        )
        async with context.session_factory() as session:
            patch_v1, patch_v2, verification = write_checkpoint_sources(context.paths.task_root)
            await record_uncommitted_checkpoint_sequence(
                session,
                task_id=task_id,
                patch_v1=patch_v1,
                patch_v2=patch_v2,
                verification=verification,
            )
            assert not patch_v1_destination.exists()
            assert not patch_v2_destination.exists()
            assert not verification_destination.exists()
            assert not latest_projection.exists()
            await assert_precommit_checkpoint_state(
                session,
                task_id=task_id,
                attempt_id=attempt_id,
                patch_v1_source=patch_v1,
                patch_v2_source=patch_v2,
                verification_source=verification,
                patch_v1_destination=patch_v1_destination,
                patch_v2_destination=patch_v2_destination,
            )
            await session.commit()
        await drive_runtime_once(task_id=task_id)
        async with context.session_factory() as session:
            await accept_boundary_and_continue(
                session,
                task_id=task_id,
                boundary=EgressBoundary.GREEN,
            )
        assert patch_v1_destination.is_file()
        assert patch_v2_destination.is_file()
        assert verification_destination.is_file()
        assert latest_projection.is_file()
        assert (
            context.paths.task_root
            / "outputs"
            / "artifacts"
            / "implement_change"
            / "change_patch"
            / "current.json"
        ).is_file()


async def test_record_checkpoint_allows_terminal_checkpoint_supersession_on_open_attempt(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-single-terminal-checkpoint",
    ) as context:
        task_id = "task_single_terminal_checkpoint"
        attempt_id = await launch_minimal_worker(context, task_id=task_id)
        async with context.session_factory() as session:
            patch_source = write_task_file(
                context.paths.task_root,
                "workspace/change_patch.diff",
                "diff --git a b",
            )
            verification_source = write_task_file(
                context.paths.task_root,
                "workspace/verification_report.md",
                "verification passed",
            )
            await record_terminal_checkpoint_for_session(
                session,
                task_id=task_id,
                outcome=CheckpointOutcome.GREEN,
                summary="Published the final bounded result.",
                next_step="Return to the parent review node.",
                artifacts=[
                    ("change_patch", patch_source),
                    ("verification_report", verification_source),
                ],
            )
            await record_terminal_checkpoint_for_session(
                session,
                task_id=task_id,
                outcome=CheckpointOutcome.BLOCKED,
                summary="Superseded the green terminal handoff with a blocker.",
                next_step="Return to the parent with the blocker instead.",
            )
            attempt = await session.get(AttemptModel, attempt_id)
            assert attempt is not None
            latest_checkpoint = await session.get(
                AttemptCheckpointModel,
                attempt.latest_checkpoint_id,
            )
            assert latest_checkpoint is not None
            assert latest_checkpoint.outcome == CheckpointOutcome.BLOCKED.value
            checkpoints = list(
                await session.scalars(
                    select(AttemptCheckpointModel)
                    .where(AttemptCheckpointModel.attempt_id == attempt_id)
                    .order_by(AttemptCheckpointModel.checkpoint_id.asc())
                )
            )
            assert [checkpoint.outcome for checkpoint in checkpoints] == ["green", "blocked"]


async def test_record_checkpoint_rejects_parent_retry_terminal_checkpoint(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-parent-retry-checkpoint",
    ) as context:
        task_id = "task_parent_retry_terminal_checkpoint"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="reviewed-change-release",
            compiler_version="runtime-db",
        )
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="change_subtree",
            summary="Start the implementation subtree.",
            instruction="Stage the current implementation subtree only.",
        )
        assert yielded.current_node_key == "change_subtree"
        async with context.session_factory() as session:
            with pytest.raises(
                ValueError,
                match="parent/root retry checkpoint is illegal",
            ):
                await record_terminal_checkpoint_for_session(
                    session,
                    task_id=task_id,
                    outcome=CheckpointOutcome.RETRY,
                    summary="Tried to retry the parent node.",
                    next_step="This should be rejected before persistence.",
                )
            checkpoint = await session.scalar(select(AttemptCheckpointModel))
            assert checkpoint is None


async def test_retry_creates_new_attempt_with_checkpoint_consume_ref(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(tmp_path, task_root_name="task-root") as context:
        task_id = "task_2026_0043"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="bounded-change",
            compiler_version="runtime-db",
        )
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="implement_change",
            summary="Repair the settings-loader bug.",
            instruction="Publish a bounded patch and retry-safe evidence.",
        )
        assert yielded.current_node_key == "implement_change"
        async with context.session_factory() as session:
            patch_source = write_task_file(
                context.paths.task_root,
                "workspace/change_patch.diff",
                "diff --git a b",
            )
            await record_terminal_checkpoint_for_session(
                session,
                task_id=task_id,
                outcome=CheckpointOutcome.RETRY,
                summary="Retry is required after a partial patch.",
                next_step="Retry the same assignment with the prior checkpoint in view.",
                artifacts=[("change_patch", patch_source)],
            )
            retry_boundary = await accept_boundary_and_continue(
                session,
                task_id=task_id,
                boundary=EgressBoundary.RETRY,
            )
            assert retry_boundary.current_node_key == "implement_change"
            assert retry_boundary.active_attempt_id is not None
            previous_attempt_id = "attempt.task_2026_0043.implement_change.01"
            assert retry_boundary.active_attempt_id != previous_attempt_id
            await drive_runtime_once(task_id=task_id)
            await drive_runtime_until(
                lambda: retry_dispatch_has_prompt_path(session, task_id=task_id),
                task_id=task_id,
                max_cycles=20,
            )
            session.expire_all()
            retry_dispatch = await session.scalar(
                select(DispatchTurnModel)
                .where(
                    DispatchTurnModel.task_id == task_id,
                    DispatchTurnModel.node_key == "implement_change",
                    DispatchTurnModel.closed_at.is_(None),
                )
                .order_by(DispatchTurnModel.rendered_at.desc())
            )
            if retry_dispatch is None:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                raise AssertionError(
                    {
                        "flow_current_open_dispatch_id": None
                        if flow is None
                        else flow.current_open_dispatch_id,
                        "flow_current_node_key": None if flow is None else flow.current_node_key,
                        "flow_status": None if flow is None else flow.status,
                    }
                )
            assert retry_dispatch.prompt_path
            retry_prompt = await asyncio.to_thread(
                Path(retry_dispatch.prompt_path).read_text,
                encoding="utf-8",
            )
            assert "## Consumed Durable Refs" in retry_prompt
            assert f"{previous_attempt_id}/latest-checkpoint.md" in retry_prompt
