from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence import AssignmentModel, BudgetCounterModel, FlowNodeModel
from autoclaw.runtime import CheckpointOutcome
from sqlalchemy import select
from tests.integration.runtime.db.actions import (
    run_child_outcome,
    update_child,
    update_child_on_current_flow,
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
from tests.integration.runtime.db.workflows import parent_budget_rebind_workflow

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def test_structural_replan_uses_relational_parent_child_authority(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-relational-replan",
    ) as context:
        task_id = "task_relational_replan"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="reviewed-change-release",
            compiler_version="runtime-relational-replan",
        )
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="change_subtree",
            summary="Open the implementation subtree.",
            instruction="Dispatch only the implementation subtree.",
        )
        assert yielded.current_node_key == "change_subtree"
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.active_flow_revision_id is not None
            subtree_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="change_subtree",
            )
            child_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="scope_change",
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
                node_key="change_subtree",
            )
            updated_child_node = await require_flow_node(
                session,
                flow_revision_id=revision_id,
                node_key="implement_change",
            )
            assert updated_child_node.parent_node_key == "change_subtree"
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
    context: RuntimeDatabaseContext,
    *,
    node_key: str,
    task_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await require_flow_model(session, task_id=task_id)
        assert flow.active_flow_revision_id is not None
        budgeted_node = await require_flow_node(
            session,
            flow_revision_id=flow.active_flow_revision_id,
            node_key=node_key,
        )
        assert budgeted_node.current_assignment_id is not None
        budgeted_assignment = await session.get(
            AssignmentModel,
            budgeted_node.current_assignment_id,
        )
        assert budgeted_assignment is not None
        budget_counter = await session.get(
            BudgetCounterModel,
            f"budget.child_assignment.{budgeted_assignment.assignment_id}",
        )
        assert budget_counter is not None
        assert budget_counter.flow_node_id == budgeted_node.flow_node_id
        updated = await update_child(
            session,
            task_id=task_id,
            expected_structural_revision_id=flow.active_flow_revision_id,
            child_node_key="implement_change",
            description="Refresh the implementation step after child return.",
        )
        await session.commit()
        updated_budgeted_node = await require_flow_node(
            session,
            flow_revision_id=updated.flow.active_flow_revision_id,
            node_key=node_key,
        )
        rebound = await session.get(
            BudgetCounterModel,
            f"budget.child_assignment.{budgeted_assignment.assignment_id}",
        )
        assert rebound is not None
        assert rebound.flow_node_id == updated_budgeted_node.flow_node_id


async def test_structural_replan_rebinds_parent_child_assignment_budget_counter(
    tmp_path: Path,
) -> None:
    workflow_definition = parent_budget_rebind_workflow()
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-parent-budget-rebind",
    ) as context:
        task_id = "task_budget_rebind"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version="runtime-budget-rebind",
            workflow_definition=workflow_definition,
        )
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="implementation_parent",
            summary="Open the implementation subtree.",
            instruction="Dispatch only the implementation subtree.",
        )
        assert yielded.current_node_key == "implementation_parent"
        returned_root = await run_child_outcome(
            context,
            task_id=task_id,
            child_node_key="implement_change",
            assignment_summary="Implement the bounded change.",
            assignment_instruction="Publish the patch and verification evidence only.",
            outcome=CheckpointOutcome.GREEN,
            handoff_summary="Bounded implementation completed.",
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
        assert returned_root.current_node_key == "implementation_parent"
        await assert_budget_counter_rebound(
            context,
            node_key="implementation_parent",
            task_id=task_id,
        )
