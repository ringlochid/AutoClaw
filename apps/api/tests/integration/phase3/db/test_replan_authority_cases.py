from __future__ import annotations

from pathlib import Path

from app.db import AssignmentModel, BudgetCounterModel, FlowNodeModel
from app.runtime import CheckpointOutcome
from sqlalchemy import select
from tests.integration.phase3.db.actions import (
    run_child_outcome,
    update_child,
    update_child_on_current_flow,
    yield_child_assignment,
)
from tests.integration.phase3.db.context import (
    Phase3RuntimeContext,
    launch_runtime_case,
    phase3_runtime_context,
    require_flow_model,
    require_flow_node,
    write_task_file,
)
from tests.integration.phase3.db.workflows import root_budget_rebind_workflow


async def test_phase3_structural_replan_uses_relational_parent_child_authority(
    tmp_path: Path,
) -> None:
    async with phase3_runtime_context(
        tmp_path,
        task_root_name="task-root-relational-replan",
    ) as context:
        task_id = "task_phase3_relational_replan"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="phase-3-relational-replan",
        )
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="implementation_subtree",
            summary="Open the implementation subtree.",
            instruction="Dispatch only the implementation subtree.",
        )
        assert yielded.current_node_key == "implementation_subtree"
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.active_flow_revision_id is not None
            subtree_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="implementation_subtree",
            )
            child_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="investigate_issue",
            )
            child_node.parent_node_key = "root"
            subtree_node.child_node_keys_json = ["shadow_only_child"]
            await session.commit()
        updated = await update_child_on_current_flow(
            context,
            task_id=task_id,
            child_node_key="implement_change",
            description="Refresh the implementation step after shadow drift.",
        )
        async with context.session_factory() as session:
            revision_id = updated.flow.active_flow_revision_id
            assert revision_id is not None
            updated_subtree_node = await require_flow_node(
                session,
                flow_revision_id=revision_id,
                node_key="implementation_subtree",
            )
            updated_child_node = await require_flow_node(
                session,
                flow_revision_id=revision_id,
                node_key="implement_change",
            )
            assert updated_child_node.parent_node_key == "implementation_subtree"
            assert "shadow_only_child" not in updated_subtree_node.child_node_keys_json
            relational_child_keys = list(
                await session.scalars(
                    select(FlowNodeModel.node_key)
                    .where(
                        FlowNodeModel.flow_revision_id == revision_id,
                        FlowNodeModel.parent_flow_node_id == updated_subtree_node.flow_node_id,
                    )
                    .order_by(FlowNodeModel.order_index.asc())
                )
            )
            assert updated_subtree_node.child_node_keys_json == relational_child_keys


async def assert_budget_counter_rebound(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await require_flow_model(session, task_id=task_id)
        assert flow.active_flow_revision_id is not None
        root_node = await require_flow_node(
            session,
            flow_revision_id=flow.active_flow_revision_id,
            node_key="root",
        )
        assert root_node.current_assignment_id is not None
        root_assignment = await session.get(AssignmentModel, root_node.current_assignment_id)
        assert root_assignment is not None
        budget_counter = await session.get(
            BudgetCounterModel,
            f"budget.child_assignment.{root_assignment.assignment_id}",
        )
        assert budget_counter is not None
        assert budget_counter.flow_node_id == root_node.flow_node_id
        updated = await update_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
            child_node_key="implement_change",
            description="Refresh the implementation step after child return.",
        )
        await session.commit()
        updated_root_node = await require_flow_node(
            session,
            flow_revision_id=updated.flow.active_flow_revision_id,
            node_key="root",
        )
        rebound = await session.get(
            BudgetCounterModel,
            f"budget.child_assignment.{root_assignment.assignment_id}",
        )
        assert rebound is not None
        assert rebound.flow_node_id == updated_root_node.flow_node_id


async def test_phase3_structural_replan_rebinds_child_assignment_budget_counter(
    tmp_path: Path,
) -> None:
    workflow_definition = root_budget_rebind_workflow()
    async with phase3_runtime_context(
        tmp_path,
        task_root_name="task-root-budget-rebind",
    ) as context:
        task_id = "task_phase3_budget_rebind"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version="phase-3-budget-rebind",
            workflow_definition=workflow_definition,
        )
        returned_root = await run_child_outcome(
            context,
            task_id=task_id,
            child_node_key="implement_change",
            assignment_summary="Implement the bounded change.",
            assignment_instruction="Publish the patch and verification evidence only.",
            outcome=CheckpointOutcome.GREEN,
            handoff_summary="Minimal implementation completed.",
            next_step="Return to root for structural refresh.",
            artifacts=[
                (
                    "change_patch",
                    write_task_file(
                        context.paths.task_root,
                        "workspace/budget-rebind-patch.diff",
                        "diff --git budget rebind",
                    ),
                ),
                (
                    "verification_report",
                    write_task_file(
                        context.paths.task_root,
                        "workspace/budget-rebind-verification.md",
                        "budget rebind verification ok",
                    ),
                ),
            ],
        )
        assert returned_root.current_node_key == "root"
        await assert_budget_counter_rebound(context, task_id=task_id)
