from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence import DispatchTurnModel
from autoclaw.runtime import (
    CheckpointOutcome,
    EgressBoundary,
    accept_boundary,
)
from autoclaw.runtime.contracts import BoundaryWrite as BoundaryWriteSchema
from autoclaw.runtime.projection import build_dispatch_prompt
from tests.integration.runtime.db.actions import (
    add_child_on_current_flow,
    assign_child_on_current_flow,
    record_terminal_checkpoint_and_continue,
    record_terminal_checkpoint_for_session,
    yield_child_assignment,
)
from tests.integration.runtime.db.context import (
    launch_runtime_case,
    require_flow_model,
    require_flow_node,
    runtime_database_context,
)
from tests.integration.runtime.db.workflows import root_blocked_workflow

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def test_rerenders_historical_dispatch_from_dispatch_lineage(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-rerender",
    ) as context:
        task_id = "task_rerender_history"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="runtime-rerender-history",
        )
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.current_open_dispatch_id is not None
            root_dispatch_id = flow.current_open_dispatch_id
        await assign_child_on_current_flow(
            context,
            task_id=task_id,
            child_node_key="implementation_subtree",
            summary="Stage only the unique child review path.",
            instruction="Do not mutate the historical root prompt.",
        )
        async with context.session_factory() as session:
            yielded = await accept_boundary(
                session,
                task_id,
                BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
            )
            await session.commit()
            assert yielded.flow.current_node_key == "implementation_subtree"
        async with context.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
            assert dispatch is not None
            bundle, record = await build_dispatch_prompt(session, task_id, dispatch)
            assert record.node_key == "root"
            assert "Investigate and fix the auth refresh regression." in bundle.full_markdown
            assert "Stage only the unique child review path." not in bundle.full_markdown


async def test_rerenders_historical_parent_dispatch_without_later_child_checkpoint(
    tmp_path: Path,
) -> None:
    workflow_definition = root_blocked_workflow()
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-rerender-child-checkpoint",
    ) as context:
        task_id = "task_rerender_child_checkpoint"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version="runtime-rerender-child-checkpoint",
            workflow_definition=workflow_definition,
        )
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.current_open_dispatch_id is not None
            root_dispatch_id = flow.current_open_dispatch_id
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="investigate_blocker",
            summary="Investigate the blocker.",
            instruction="Return blocked truth if the worker is blocked.",
        )
        child_attempt_id = yielded.active_attempt_id
        assert child_attempt_id is not None
        async with context.session_factory() as session:
            await record_terminal_checkpoint_for_session(
                session,
                task_id=task_id,
                outcome=CheckpointOutcome.BLOCKED,
                summary="The worker is blocked.",
                next_step="Root must decide whether the whole flow is blocked.",
            )
            await accept_boundary(
                session,
                task_id,
                BoundaryWriteSchema(boundary=EgressBoundary.BLOCKED),
            )
            await session.commit()
        async with context.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
            assert dispatch is not None
            bundle, record = await build_dispatch_prompt(session, task_id, dispatch)
            assert record.node_key == "root"
            assert child_attempt_id not in bundle.full_markdown
            assert "The worker is blocked." not in bundle.full_markdown


async def test_parent_prompt_uses_relational_child_authority_when_shadows_drift(
    tmp_path: Path,
) -> None:
    async with runtime_database_context(
        tmp_path,
        task_root_name="task-root-relational-prompt",
    ) as context:
        task_id = "task_relational_prompt"
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="runtime-relational-prompt",
        )
        await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="implementation_subtree",
            summary="Open the implementation subtree.",
            instruction="Dispatch only the implementation subtree.",
        )
        await add_child_on_current_flow(
            context,
            task_id=task_id,
            child={
                "id": "qa_sweep",
                "role": "architect",
                "description": "Run a bounded QA sweep over the subtree.",
            },
        )
        yielded = await yield_child_assignment(
            context,
            task_id=task_id,
            child_node_key="qa_sweep",
            summary="Run the bounded QA sweep.",
            instruction="Return the QA result to the parent subtree.",
        )
        child_attempt_id = yielded.active_attempt_id
        assert child_attempt_id is not None
        returned_parent = await record_terminal_checkpoint_and_continue(
            context,
            task_id=task_id,
            outcome=CheckpointOutcome.GREEN,
            summary="QA sweep completed.",
            next_step="Parent should review the QA result.",
        )
        assert returned_parent.current_node_key == "implementation_subtree"
        async with context.session_factory() as session:
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.active_flow_revision_id is not None
            root_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="implementation_subtree",
            )
            child_node = await require_flow_node(
                session,
                flow_revision_id=flow.active_flow_revision_id,
                node_key="qa_sweep",
            )
            child_node.parent_node_key = "root"
            root_node.child_node_keys_json = ["shadow_only_child"]
            await session.commit()
            flow = await require_flow_model(session, task_id=task_id)
            assert flow.current_open_dispatch_id is not None
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            assert dispatch is not None
            bundle, record = await build_dispatch_prompt(session, task_id, dispatch)
            assert record.node_key == "implementation_subtree"
            assert f"{child_attempt_id}/latest-checkpoint.md" in bundle.full_markdown
            assert "QA sweep completed." in bundle.full_markdown
