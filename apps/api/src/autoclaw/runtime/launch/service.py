from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.registry import compile_current_workflow_launch_snapshot
from autoclaw.persistence.models import AssignmentModel, AttemptModel
from autoclaw.runtime import (
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
    RuntimeLaunchInput,
)
from autoclaw.runtime.contracts import TaskEventSource, TaskEventType, WorkflowManifestRef
from autoclaw.runtime.flow import WORKFLOW_MANIFEST_REF_DESCRIPTION
from autoclaw.runtime.ids import (
    assignment_key_for_task,
    attempt_id_for_task,
    dispatch_id_for_task,
    flow_id_for_task,
    flow_revision_id,
)
from autoclaw.runtime.launch.persistence.runtime import persist_bootstrap_runtime_from_precomputed
from autoclaw.runtime.task_events import append_task_event


async def launch_task_runtime(
    session: AsyncSession,
    launch_input: RuntimeLaunchInput,
) -> RuntimeBootstrapResult:
    from autoclaw.runtime.dispatch.control import open_dispatch_for_attempt
    from autoclaw.runtime.flow.queries import flow_node_by_key

    snapshot = await compile_current_workflow_launch_snapshot(
        session,
        workflow_key=launch_input.task_compose.workflow.key,
        compiler_version=launch_input.compiler_version,
    )
    bootstrap_input = RuntimeBootstrapProjectionInput(
        task_id=launch_input.task_id,
        active_flow_revision_id=flow_revision_id(flow_id_for_task(launch_input.task_id), 1),
        attempt_id=attempt_id_for_task(launch_input.task_id, "root", 1),
        assignment_key=assignment_key_for_task(launch_input.task_id, "root", 1),
        dispatch_id=dispatch_id_for_task(launch_input.task_id, "root", 1),
        task_root=launch_input.task_root,
        task_compose=launch_input.task_compose,
        workflow_definition=snapshot.workflow.definition,
        compiled_plan=snapshot.compiled_plan,
        role_policy_lookup=snapshot.role_policy_lookup,
    )
    result = await persist_bootstrap_runtime_from_precomputed(
        session,
        bootstrap_input,
        should_commit=False,
    )
    await _append_task_started_event(
        session,
        launch_input=launch_input,
        bootstrap_input=bootstrap_input,
        result=result,
    )
    assignment = await session.scalar(
        select(AssignmentModel).where(
            AssignmentModel.assignment_key == result.assignment.assignment_key
        )
    )
    if assignment is None:
        raise ValueError(
            f"missing launch assignment '{result.assignment.assignment_key}' after bootstrap"
        )
    attempt = await session.get(AttemptModel, bootstrap_input.attempt_id)
    if attempt is None:
        raise ValueError(f"missing launch attempt '{bootstrap_input.attempt_id}' after bootstrap")
    node = await flow_node_by_key(
        session,
        bootstrap_input.active_flow_revision_id,
        result.assignment.node_key,
    )
    await open_dispatch_for_attempt(
        session,
        task_id=launch_input.task_id,
        node=node,
        assignment=assignment,
        attempt=attempt,
        previous_dispatch_id=None,
        should_stage_launch_projection_outputs=True,
    )
    return result


async def _append_task_started_event(
    session: AsyncSession,
    *,
    launch_input: RuntimeLaunchInput,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    result: RuntimeBootstrapResult,
) -> None:
    workflow_manifest_ref = WorkflowManifestRef(
        path=result.paths.runtime_path / "workflow-manifest.md",
        description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
    )
    await append_task_event(
        session,
        task_id=launch_input.task_id,
        event_type=TaskEventType.TASK_STARTED,
        event_source=TaskEventSource.CONTROLLER,
        flow_revision_id=bootstrap_input.active_flow_revision_id,
        attempt_id=bootstrap_input.attempt_id,
        node_key=result.assignment.node_key,
        payload={
            "task_title": launch_input.task_compose.task.title,
            "task_summary": launch_input.task_compose.task.summary,
            "workflow_key": launch_input.task_compose.workflow.key,
            "initial_node_key": result.assignment.node_key,
            "workflow_manifest_ref": workflow_manifest_ref.model_dump(mode="json"),
        },
    )
