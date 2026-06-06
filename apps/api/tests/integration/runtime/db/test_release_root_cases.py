from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.persistence import AssignmentModel, DispatchTurnModel
from autoclaw.runtime import CheckpointOutcome, EgressBoundary, runtime_flow_read
from autoclaw.runtime.post_commit import drive_runtime_once
from sqlalchemy import select
from tests.integration.runtime.db.actions import (
    record_terminal_checkpoint_and_continue,
    record_terminal_checkpoint_for_session,
    release_blocked,
    release_green,
    release_green_on_current_flow,
    run_child_outcome,
)
from tests.integration.runtime.db.context import (
    Phase3RuntimeContext,
    accept_boundary_and_continue,
    launch_runtime_case,
    phase3_runtime_context,
    require_flow_model,
    write_task_file,
)
from tests.integration.runtime.db.workflows import root_blocked_workflow

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

async def release_green_and_return(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    summary: str,
    next_step: str,
) -> Any:
    await release_green_on_current_flow(context, task_id=task_id)
    return await record_terminal_checkpoint_and_continue(
        context,
        task_id=task_id,
        outcome=CheckpointOutcome.GREEN,
        summary=summary,
        next_step=next_step,
    )


async def run_minimal_implement_return_root(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    patch_path: str,
    patch_content: str,
    verification_path: str,
    verification_content: str,
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
                write_task_file(context.paths.task_root, patch_path, patch_content),
            ),
            (
                "verification_report",
                write_task_file(
                    context.paths.task_root,
                    verification_path,
                    verification_content,
                ),
            ),
        ],
    )


async def run_blocked_investigation_return_root(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
) -> Any:
    return await run_child_outcome(
        context,
        task_id=task_id,
        child_node_key="investigate_blocker",
        assignment_summary="Investigate the blocker.",
        assignment_instruction="Decide whether the whole flow is blocked.",
        outcome=CheckpointOutcome.BLOCKED,
        handoff_summary="The worker is blocked.",
        next_step="Root must decide whether the whole flow is blocked.",
    )


async def stage_release_green_precondition(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
) -> str:
    async with context.session_factory() as session:
        flow = await require_flow_model(session, task_id=task_id)
        assert flow.active_flow_revision_id is not None
        child_assignment = await session.scalar(
            select(AssignmentModel).where(
                AssignmentModel.task_id == task_id,
                AssignmentModel.node_key != "root",
            )
        )
        assert child_assignment is not None
        child_assignment.consumes_json = [
            *child_assignment.consumes_json,
            {
                "kind": "criteria",
                "slot": "stale_release_green_basis",
                "path": str(
                    context.paths.task_root / "context" / "criteria" / "stale-release-green.md"
                ),
                "description": (
                    "Injected stale evidence to prove release currentness revalidation."
                ),
            },
        ]
        with pytest.raises(ValueError, match="current surfaced evidence"):
            await release_green(
                session,
                task_id=task_id,
                expected_structural_revision_id=flow.active_flow_revision_id,
            )
        child_assignment.consumes_json = child_assignment.consumes_json[:-1]
        await release_green(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
        )
        dispatch = await session.scalar(
            select(DispatchTurnModel)
            .where(
                DispatchTurnModel.task_id == task_id,
                DispatchTurnModel.node_key == "root",
                DispatchTurnModel.closed_at.is_(None),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        )
        assert dispatch is not None
        assert dispatch.release_precondition_kind == "release_green"
        await session.commit()
        return dispatch.dispatch_id


async def stage_release_blocked_precondition(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
) -> str:
    async with context.session_factory() as session:
        root_flow = await runtime_flow_read(session, task_id)
        with pytest.raises(
            ValueError,
            match="current root basis to be terminal-blocked",
        ):
            await release_blocked(
                session,
                task_id=task_id,
                expected_structural_revision_id=root_flow.active_flow_revision_id,
            )
        await record_terminal_checkpoint_for_session(
            session,
            task_id=task_id,
            outcome=CheckpointOutcome.BLOCKED,
            summary="Root confirms the whole flow is blocked.",
            next_step="Close the root dispatch as blocked.",
        )
        await session.commit()
    await drive_runtime_once(task_id=task_id)
    async with context.session_factory() as session:
        root_flow = await runtime_flow_read(session, task_id)
        child_assignment = await session.scalar(
            select(AssignmentModel).where(
                AssignmentModel.task_id == task_id,
                AssignmentModel.node_key == "investigate_blocker",
            )
        )
        assert child_assignment is not None
        child_assignment.consumes_json = [
            *child_assignment.consumes_json,
            {
                "kind": "criteria",
                "slot": "stale_root_blocked_basis",
                "path": str(
                    context.paths.task_root / "context" / "criteria" / "stale-root-blocked.md"
                ),
                "description": "Injected stale evidence to prove currentness revalidation.",
            },
        ]
        with pytest.raises(ValueError, match="current surfaced evidence"):
            await release_blocked(
                session,
                task_id=task_id,
                expected_structural_revision_id=root_flow.active_flow_revision_id,
            )
        child_assignment.consumes_json = child_assignment.consumes_json[:-1]
        await release_blocked(
            session,
            task_id=task_id,
            expected_structural_revision_id=root_flow.active_flow_revision_id,
        )
        flow = await require_flow_model(session, task_id=task_id)
        assert flow.current_open_dispatch_id is not None
        root_dispatch_id = flow.current_open_dispatch_id
        await accept_boundary_and_continue(
            session,
            task_id=task_id,
            boundary=EgressBoundary.BLOCKED,
        )
        return root_dispatch_id


async def test_phase3_minimal_root_closure_remains_readable(tmp_path: Path) -> None:
    async with phase3_runtime_context(tmp_path, task_root_name="task-root") as context:
        task_id = "task_2026_0045"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="minimal-implement-change",
            compiler_version="phase-3-runtime-db",
        )
        returned_root = await run_minimal_implement_return_root(
            context,
            task_id=task_id,
            patch_path="workspace/minimal_change_patch.diff",
            patch_content="diff --git c d",
            verification_path="workspace/minimal_verification_report.md",
            verification_content="minimal verification ok",
        )
        assert returned_root.current_node_key == "root"
        completed = await release_green_and_return(
            context,
            task_id=task_id,
            summary="Root verified the minimal bounded evidence.",
            next_step="Close the flow.",
        )
        async with context.session_factory() as session:
            reread = await runtime_flow_read(session, task_id)
            assert completed.status.value == "succeeded"
            assert completed.current_node_key == "root"
            assert reread.status.value == "succeeded"
            assert reread.current_node_key == "root"


async def test_phase3_release_precondition_is_dispatch_local_not_continuation_state(
    tmp_path: Path,
) -> None:
    async with phase3_runtime_context(tmp_path, task_root_name="task-root") as context:
        task_id = "task_2026_0046"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="minimal-implement-change",
            compiler_version="phase-3-runtime-db",
        )
        returned_root = await run_minimal_implement_return_root(
            context,
            task_id=task_id,
            patch_path="workspace/dispatch_local_patch.diff",
            patch_content="diff --git e f",
            verification_path="workspace/dispatch_local_verification.md",
            verification_content="dispatch local verification ok",
        )
        assert returned_root.current_node_key == "root"
        root_dispatch_id = await stage_release_green_precondition(
            context,
            task_id=task_id,
        )
        completed = await record_terminal_checkpoint_and_continue(
            context,
            task_id=task_id,
            outcome=CheckpointOutcome.GREEN,
            summary="Root verified the minimal bounded evidence.",
            next_step="Close the flow.",
        )
        async with context.session_factory() as session:
            closed_dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
            assert closed_dispatch is not None
            descendant_refs = closed_dispatch.release_precondition_descendant_refs_json
            assert descendant_refs is not None
            assert any(
                ref["kind"] == "checkpoint" and "implement_change" in str(ref["path"])
                for ref in descendant_refs
            )
            assert any(
                ref["kind"] == "artifact" and ref.get("slot") == "change_patch"
                for ref in descendant_refs
            )
            assert any(
                ref["kind"] == "artifact" and ref.get("slot") == "verification_report"
                for ref in descendant_refs
            )
            assert completed.status.value == "succeeded"


async def test_phase3_release_blocked_requires_current_root_and_whole_flow_blocked_basis(
    tmp_path: Path,
) -> None:
    workflow_definition = root_blocked_workflow()
    async with phase3_runtime_context(
        tmp_path,
        task_root_name="task-root-blocked",
    ) as context:
        task_id = "task_root_blocked"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version="phase-3-root-blocked",
            workflow_definition=workflow_definition,
        )
        blocked = await run_blocked_investigation_return_root(context, task_id=task_id)
        assert blocked.current_node_key == "root"
        root_dispatch_id = await stage_release_blocked_precondition(
            context,
            task_id=task_id,
        )
        async with context.session_factory() as session:
            closed_dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
            assert closed_dispatch is not None
            descendant_refs = closed_dispatch.release_precondition_descendant_refs_json
            assert descendant_refs is not None
            assert any(
                ref["kind"] == "checkpoint" and "investigate_blocker" in str(ref["path"])
                for ref in descendant_refs
            )
            reread = await runtime_flow_read(session, task_id)
            closed_dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
            assert closed_dispatch is not None
            assert reread.status == "blocked"
