from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    CompiledPlanModel,
    DispatchTurnModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    TaskModel,
    WorkflowRevisionModel,
)
from app.runtime.contracts import (
    ManifestDependencyProjection,
    ManifestFilesystemRootsProjection,
    ManifestProjection,
    ManifestTaskProjection,
    ManifestWorkflowProjection,
)
from app.runtime.projection.manifest.context import build_manifest_current_context
from app.runtime.projection.manifest.tree import (
    build_manifest_node_tree,
    child_node_keys_by_parent_id,
    criteria_description_by_slot,
    flow_node_parent_key_by_id,
)
from app.runtime.projection.runtime_state import (
    CurrentRuntimeState,
    current_runtime_state,
    dispatch_runtime_state,
)
from app.runtime.task_root import load_task_root_paths, localize_manifest_projection

__all__ = [
    "build_dispatch_manifest_projection",
    "build_manifest_projection",
    "build_manifest_projection_for_state",
]


async def _flow_revision_graph(
    session: AsyncSession,
    *,
    flow_revision_id: str,
) -> tuple[list[FlowNodeModel], list[FlowEdgeModel]]:
    nodes = list(
        await session.scalars(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(FlowNodeModel.flow_revision_id == flow_revision_id)
            .order_by(FlowNodeModel.order_index.asc())
        )
    )
    edges = list(
        await session.scalars(
            select(FlowEdgeModel)
            .options(raiseload("*"))
            .where(FlowEdgeModel.flow_revision_id == flow_revision_id)
        )
    )
    return nodes, edges


def _dependency_descriptions(
    edges: list[FlowEdgeModel],
) -> dict[tuple[str, str, str], str]:
    return {(edge.consumer_node_key, edge.kind, edge.slot): edge.description for edge in edges}


async def _workflow_description(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task: TaskModel,
    fallback_description: str,
) -> str:
    if task.workflow_key:
        compiled_plan = await session.scalar(
            select(CompiledPlanModel)
            .options(raiseload("*"))
            .where(CompiledPlanModel.compiled_plan_id == flow.compiled_plan_id)
        )
        if compiled_plan is None:
            raise ValueError(
                f"missing compiled plan '{flow.compiled_plan_id}' for task '{task.task_id}'"
            )
        workflow_revision = await session.scalar(
            select(WorkflowRevisionModel).where(
                WorkflowRevisionModel.workflow_key == task.workflow_key,
                WorkflowRevisionModel.revision_no == compiled_plan.definition_revision_no,
            )
        )
        if workflow_revision is None:
            raise ValueError(
                "missing pinned workflow revision "
                f"'{task.workflow_key}@{compiled_plan.definition_revision_no}'"
            )
        description = workflow_revision.content_json.get("description")
        if isinstance(description, str) and description.strip():
            return description
    return fallback_description


async def build_manifest_projection_for_state(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    current_relevant_cutoff: datetime | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> ManifestProjection:
    paths = await load_task_root_paths(session, task_id)
    nodes, edges = await _flow_revision_graph(
        session,
        flow_revision_id=state.flow_revision.flow_revision_id,
    )
    workflow_description = await _workflow_description(
        session,
        flow=state.flow,
        task=state.task,
        fallback_description=state.task.summary,
    )
    current_context = await build_manifest_current_context(
        session,
        task_id=task_id,
        paths=paths,
        state=state,
        current_relevant_cutoff=current_relevant_cutoff,
        dispatch=dispatch,
    )
    manifest = ManifestProjection(
        active_flow_revision_id=state.flow_revision.flow_revision_id,
        generated_at=datetime.now(tz=UTC),
        task=ManifestTaskProjection(
            task_id=state.task.task_id,
            task_key=state.task.task_key,
            title=state.task.title,
            summary=state.task.summary,
            instruction=state.task.instruction,
        ),
        workflow=ManifestWorkflowProjection(
            workflow_key=state.task.workflow_key or "",
            description=workflow_description,
        ),
        filesystem_roots=ManifestFilesystemRootsProjection(
            workspace_path=paths.workspace_path,
            context_path=paths.context_path,
            outputs_path=paths.outputs_path,
            tmp_path=paths.tmp_path,
            runtime_path=paths.runtime_path,
        ),
        current_context=current_context,
        node_tree=build_manifest_node_tree(
            nodes=nodes,
            edges=edges,
            paths=paths,
            parent_node_key_by_id=flow_node_parent_key_by_id(nodes),
            child_node_keys_by_parent_id=child_node_keys_by_parent_id(nodes),
            dependency_descriptions=_dependency_descriptions(edges),
            criteria_descriptions=criteria_description_by_slot(nodes),
        ),
        dependency_index=tuple(
            ManifestDependencyProjection(
                provider_node_key=edge.provider_node_key,
                consumer_node_key=edge.consumer_node_key,
                kind=edge.kind,
                slot=edge.slot,
                description=edge.description,
            )
            for edge in edges
        ),
    )
    return localize_manifest_projection(paths=paths, manifest=manifest)


async def build_manifest_projection(session: AsyncSession, task_id: str) -> ManifestProjection:
    state = await current_runtime_state(session, task_id)
    return await build_manifest_projection_for_state(
        session,
        task_id=task_id,
        state=state,
    )


async def build_dispatch_manifest_projection(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> ManifestProjection:
    state = await dispatch_runtime_state(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    return await build_manifest_projection_for_state(
        session,
        task_id=task_id,
        state=state,
        current_relevant_cutoff=dispatch.rendered_at,
        dispatch=dispatch,
    )
