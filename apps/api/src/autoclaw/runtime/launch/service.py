from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.registry import compile_current_workflow_launch_snapshot
from autoclaw.runtime import (
    RuntimeBootstrapInput,
    RuntimeBootstrapResult,
    RuntimeLaunchInput,
)
from autoclaw.runtime.ids import (
    assignment_key_for_task,
    attempt_id_for_task,
    flow_id_for_task,
    flow_revision_id,
)
from autoclaw.runtime.launch.persistence.runtime import persist_bootstrap_runtime_from_precomputed


async def launch_task_runtime(
    session: AsyncSession,
    launch_input: RuntimeLaunchInput,
) -> RuntimeBootstrapResult:
    """Stage task, flow, assignment, attempt, and durable root-source truth."""

    snapshot = await compile_current_workflow_launch_snapshot(
        session,
        workflow_key=launch_input.task_compose.workflow.key,
        compiler_version=launch_input.compiler_version,
    )
    root_node_key = snapshot.workflow.definition.root.node_key
    bootstrap_input = RuntimeBootstrapInput(
        task_id=launch_input.task_id,
        active_flow_revision_id=flow_revision_id(flow_id_for_task(launch_input.task_id), 1),
        attempt_id=attempt_id_for_task(launch_input.task_id, root_node_key, 1),
        assignment_key=assignment_key_for_task(launch_input.task_id, root_node_key, 1),
        task_root=launch_input.task_root,
        task_compose=launch_input.task_compose,
        workflow_definition=snapshot.workflow.definition,
        compiled_plan=snapshot.compiled_plan,
        role_policy_lookup=snapshot.role_policy_lookup,
    )
    return await persist_bootstrap_runtime_from_precomputed(
        session,
        bootstrap_input,
        should_commit=False,
    )


__all__ = ["launch_task_runtime"]
