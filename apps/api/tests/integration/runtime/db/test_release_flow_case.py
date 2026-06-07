from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from autoclaw.runtime import CheckpointOutcome, EgressBoundary, runtime_flow_read
from tests.integration.runtime.db.actions import (
    assign_child,
    record_terminal_checkpoint_and_continue,
    release_green,
    release_green_on_current_flow,
    yield_child_assignment,
)
from tests.integration.runtime.db.context import (
    Phase3RuntimeContext,
    advance_boundary_on_current_flow,
    launch_runtime_case,
    phase3_runtime_context,
    write_task_file,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def start_parent_worker_flow(context: Phase3RuntimeContext) -> None:
    task_id = "task_2026_0042"
    await launch_runtime_case(
        context,
        task_id=task_id,
        workflow_key="normal-parent-first-release",
        compiler_version="phase-3-runtime-db",
    )
    yielded = await yield_child_assignment(
        context,
        task_id=task_id,
        child_node_key="implementation_subtree",
        summary="Start the implementation subtree.",
        instruction="Stage the current implementation subtree only.",
    )
    assert yielded.current_node_key == "implementation_subtree"


async def run_subtree_child_outcome(
    context: Phase3RuntimeContext,
    *,
    child_node_key: str,
    assignment_summary: str,
    assignment_instruction: str,
    handoff_summary: str,
    next_step: str,
    artifacts: Sequence[tuple[str, Path]] = (),
) -> Any:
    await yield_child_assignment(
        context,
        task_id="task_2026_0042",
        child_node_key=child_node_key,
        summary=assignment_summary,
        instruction=assignment_instruction,
    )
    returned = await record_terminal_checkpoint_and_continue(
        context,
        task_id="task_2026_0042",
        outcome=CheckpointOutcome.GREEN,
        summary=handoff_summary,
        next_step=next_step,
        artifacts=artifacts,
    )
    assert returned.current_node_key == "implementation_subtree"
    return returned


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


async def assert_root_requires_release_closure(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
) -> None:
    async with context.session_factory() as session:
        root_flow = await runtime_flow_read(session, task_id)
        with pytest.raises(
            ValueError,
            match="child node 'release_closure' has no current assignment",
        ):
            await release_green(
                session,
                task_id=task_id,
                expected_structural_revision_id=root_flow.active_flow_revision_id,
            )
        await assign_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=root_flow.active_flow_revision_id,
            child_node_key="release_closure",
            summary="Run the final release closure.",
            instruction="Publish only the final closure report.",
        )
        await session.commit()


async def run_investigation_step(context: Phase3RuntimeContext) -> None:
    await run_subtree_child_outcome(
        context,
        child_node_key="investigate_issue",
        assignment_summary="Investigate the auth refresh regression.",
        assignment_instruction="Publish only the current findings report.",
        handoff_summary="Investigation completed.",
        next_step="Parent should review the findings.",
        artifacts=[
            (
                "findings_report",
                write_task_file(
                    context.paths.task_root,
                    "workspace/findings_report.md",
                    "bounded findings",
                ),
            )
        ],
    )
    assert (
        context.paths.task_root
        / "outputs"
        / "artifacts"
        / "investigate_issue"
        / "findings_report"
        / "current.json"
    ).is_file()


async def run_implementation_step(context: Phase3RuntimeContext) -> None:
    await run_subtree_child_outcome(
        context,
        child_node_key="implement_change",
        assignment_summary="Implement the scoped auth-refresh fix.",
        assignment_instruction="Publish only the patch and verification report.",
        handoff_summary="Implementation completed.",
        next_step="Parent should review the current patch and verification evidence.",
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


async def run_review_step(context: Phase3RuntimeContext) -> None:
    await run_subtree_child_outcome(
        context,
        child_node_key="review_change",
        assignment_summary="Review the current implementation evidence.",
        assignment_instruction="Publish only the bounded review report.",
        handoff_summary="Review completed.",
        next_step="Parent can release the implementation subtree.",
        artifacts=[
            (
                "review_report",
                write_task_file(
                    context.paths.task_root,
                    "workspace/review_report.md",
                    "review ok",
                ),
            )
        ],
    )


async def run_release_closure_step(context: Phase3RuntimeContext) -> None:
    yielded = await advance_boundary_on_current_flow(
        context,
        task_id="task_2026_0042",
        boundary=EgressBoundary.YIELD,
    )
    assert yielded.current_node_key == "release_closure"
    closure_green = await record_terminal_checkpoint_and_continue(
        context,
        task_id="task_2026_0042",
        outcome=CheckpointOutcome.GREEN,
        summary="Release closure completed.",
        next_step="Root can make the final release decision.",
        artifacts=[
            (
                "closure_report",
                write_task_file(
                    context.paths.task_root,
                    "workspace/closure_report.md",
                    "closure ok",
                ),
            )
        ],
    )
    assert closure_green.current_node_key == "root"


async def test_phase3_parent_worker_flow_and_replan_state(tmp_path: Path) -> None:
    async with phase3_runtime_context(tmp_path, task_root_name="task-root") as context:
        task_id = "task_2026_0042"
        await start_parent_worker_flow(context)
        await run_investigation_step(context)
        await run_implementation_step(context)
        await run_review_step(context)
        released_subtree = await release_green_and_return(
            context,
            task_id=task_id,
            summary="Implementation subtree is complete.",
            next_step="Root should run the final release closure worker.",
        )
        assert released_subtree.current_node_key == "root"
        await assert_root_requires_release_closure(context, task_id=task_id)
        await run_release_closure_step(context)
        completed = await release_green_and_return(
            context,
            task_id=task_id,
            summary="Root verified release evidence and closed the flow.",
            next_step="No further runtime work is required.",
        )
        assert completed.status.value == "succeeded"
        assert completed.current_node_key == "root"
        assert completed.active_attempt_id == "attempt.task_2026_0042.root.01"
        assert (context.paths.task_root / "_runtime" / "workflow-manifest.md").is_file()
