from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    CompiledPlanEdgeModel,
    CompiledPlanModel,
    CompiledPlanNodeModel,
    ContextSpaceModel,
    ManifestRootModel,
    TaskComposeModel,
    TaskModel,
    TaskResourceBindingModel,
    WorkspaceRootModel,
)
from autoclaw.runtime.contracts import (
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
)
from autoclaw.runtime.ids import (
    compiled_plan_edge_id,
    compiled_plan_node_id,
    context_space_id_for_task,
    manifest_root_id_for_task,
    task_compose_id_for_task,
    task_resource_binding_id,
    workspace_root_id_for_task,
)
from autoclaw.runtime.launch.bootstrap.context import LaunchBootstrapPersistenceContext
from autoclaw.runtime.launch.bootstrap.criteria import build_node_criteria_json
from autoclaw.runtime.launch.bootstrap.revisions import resolve_pinned_role_policy
from autoclaw.runtime.launch.bootstrap.workspace import acquire_workspace_root_lease
from autoclaw.runtime.launch.persistence.flows import (
    build_flow_edge_row,
    build_flow_node_row,
    build_flow_revision_row,
    build_flow_row,
    build_node_plan_revision_row,
)


async def stage_launch_bootstrap_rows(
    session: AsyncSession,
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    result: RuntimeBootstrapResult,
    context: LaunchBootstrapPersistenceContext,
) -> None:
    await _stage_task_root_rows(
        session,
        bootstrap_input=bootstrap_input,
        result=result,
        context=context,
    )
    await _stage_compiled_plan_graph_rows(
        session,
        bootstrap_input=bootstrap_input,
        result=result,
        context=context,
    )
    await _stage_flow_rows(
        session,
        bootstrap_input=bootstrap_input,
        result=result,
        context=context,
    )


async def _stage_task_root_rows(
    session: AsyncSession,
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    result: RuntimeBootstrapResult,
    context: LaunchBootstrapPersistenceContext,
) -> None:
    session.add(
        TaskModel(
            task_id=bootstrap_input.task_id,
            task_key=bootstrap_input.task_compose.task.key,
            title=bootstrap_input.task_compose.task.title,
            summary=bootstrap_input.task_compose.task.summary,
            instruction=bootstrap_input.task_compose.task.instruction,
            workflow_key=bootstrap_input.workflow_definition.id,
            task_root_path=str(result.paths.task_root),
        )
    )
    await session.flush()

    session.add(
        WorkspaceRootModel(
            workspace_root_id=workspace_root_id_for_task(bootstrap_input.task_id),
            task_id=bootstrap_input.task_id,
            path=str(result.paths.workspace_path),
            binding_mode=context.workspace_binding_mode,
        )
    )
    session.add(
        ContextSpaceModel(
            context_space_id=context_space_id_for_task(bootstrap_input.task_id),
            task_id=bootstrap_input.task_id,
            path=str(result.paths.context_path),
            binding_mode=context.context_binding_mode,
        )
    )
    session.add(
        ManifestRootModel(
            manifest_root_id=manifest_root_id_for_task(bootstrap_input.task_id),
            task_id=bootstrap_input.task_id,
            path=str(result.paths.runtime_path),
        )
    )
    session.add(
        TaskComposeModel(
            task_compose_id=task_compose_id_for_task(bootstrap_input.task_id),
            task_id=bootstrap_input.task_id,
            workflow_key=bootstrap_input.task_compose.workflow.key,
            workflow_revision_no=bootstrap_input.compiled_plan.definition_revision_no,
            compiled_plan_id=context.compiled_plan_id,
            workspace_root_path=str(result.paths.workspace_path),
            context_root_path=str(result.paths.context_path),
            outputs_root_path=str(result.paths.outputs_path),
            runtime_root_path=str(result.paths.runtime_path),
            compose_payload=bootstrap_input.task_compose.model_dump(mode="json"),
        )
    )
    session.add(
        CompiledPlanModel(
            compiled_plan_id=context.compiled_plan_id,
            task_id=bootstrap_input.task_id,
            workflow_key=bootstrap_input.compiled_plan.workflow_key,
            definition_revision_no=bootstrap_input.compiled_plan.definition_revision_no,
            compiler_version=bootstrap_input.compiled_plan.compiler_version,
            snapshot_json=bootstrap_input.compiled_plan.model_dump(mode="json"),
        )
    )
    for resource_binding_row in _task_resource_binding_rows(
        task_id=bootstrap_input.task_id,
        binding_paths=context.binding_paths,
    ):
        session.add(resource_binding_row)
    await session.flush()


def _task_resource_binding_rows(
    *,
    task_id: str,
    binding_paths: dict[str, str],
) -> tuple[TaskResourceBindingModel, ...]:
    return tuple(
        TaskResourceBindingModel(
            task_resource_binding_id=task_resource_binding_id(task_id, binding_kind),
            task_id=task_id,
            binding_kind=binding_kind,
            path=path,
            binding_mode=None,
        )
        for binding_kind, path in binding_paths.items()
    )


async def _stage_compiled_plan_graph_rows(
    session: AsyncSession,
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    result: RuntimeBootstrapResult,
    context: LaunchBootstrapPersistenceContext,
) -> None:
    for node in bootstrap_input.compiled_plan.nodes:
        role, policy = resolve_pinned_role_policy(
            bootstrap_input.role_policy_lookup,
            role_key=node.role,
            role_revision_no=node.role_revision_no,
            policy_key=node.policy,
            policy_revision_no=node.policy_revision_no,
        )
        session.add(
            CompiledPlanNodeModel(
                compiled_plan_node_id=compiled_plan_node_id(
                    context.compiled_plan_id,
                    node.node_key,
                ),
                compiled_plan_id=context.compiled_plan_id,
                node_key=node.node_key,
                parent_compiled_plan_node_id=(
                    compiled_plan_node_id(context.compiled_plan_id, node.parent_node_key)
                    if node.parent_node_key is not None
                    else None
                ),
                parent_node_key=node.parent_node_key,
                structural_kind=node.structural_kind.value,
                role_key=node.role,
                role_revision_no=node.role_revision_no,
                role_description=role.definition.description,
                role_instruction=role.definition.instruction,
                policy_key=node.policy,
                policy_revision_no=node.policy_revision_no,
                policy_description=policy.definition.description if policy else None,
                policy_instruction=policy.definition.instruction if policy else None,
                description=node.description,
                child_node_keys_json=list(node.child_node_keys),
                consumes_json=(node.consumes.model_dump(mode="json") if node.consumes else None),
                produces_json=(node.produces.model_dump(mode="json") if node.produces else None),
                criteria_json=build_node_criteria_json(paths=result.paths, node=node),
                child_defaults_json=node.child_defaults.model_dump(mode="json")
                if node.child_defaults
                else None,
                order_index=node.order_index,
            )
        )
    for edge in bootstrap_input.compiled_plan.dependency_edges:
        session.add(
            CompiledPlanEdgeModel(
                compiled_plan_edge_id=compiled_plan_edge_id(
                    context.compiled_plan_id,
                    edge.consumer_node_key,
                    edge.kind.value,
                    edge.slot,
                ),
                compiled_plan_id=context.compiled_plan_id,
                provider_compiled_plan_node_id=compiled_plan_node_id(
                    context.compiled_plan_id,
                    edge.provider_node_key,
                ),
                consumer_compiled_plan_node_id=compiled_plan_node_id(
                    context.compiled_plan_id,
                    edge.consumer_node_key,
                ),
                provider_node_key=edge.provider_node_key,
                consumer_node_key=edge.consumer_node_key,
                kind=edge.kind.value,
                slot=edge.slot,
                description=edge.description,
                order_index=edge.order_index,
            )
        )
    await session.flush()


async def _stage_flow_rows(
    session: AsyncSession,
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    result: RuntimeBootstrapResult,
    context: LaunchBootstrapPersistenceContext,
) -> None:
    session.add(
        build_flow_row(
            bootstrap_input=bootstrap_input,
            context=context,
        )
    )
    flow_revision = build_flow_revision_row(
        bootstrap_input=bootstrap_input,
        context=context,
    )
    session.add(flow_revision)
    await session.flush()
    await acquire_workspace_root_lease(
        session,
        task_id=bootstrap_input.task_id,
        flow_id=context.flow_id,
        workspace_root_path=str(result.paths.workspace_path),
        binding_mode=context.workspace_binding_mode,
    )

    for node in bootstrap_input.compiled_plan.nodes:
        role, policy = resolve_pinned_role_policy(
            bootstrap_input.role_policy_lookup,
            role_key=node.role,
            role_revision_no=node.role_revision_no,
            policy_key=node.policy,
            policy_revision_no=node.policy_revision_no,
        )
        flow_node = build_flow_node_row(
            result=result,
            flow_revision=flow_revision,
            context=context,
            bootstrap_input=bootstrap_input,
            node=node,
            role_description=role.definition.description,
            role_instruction=role.definition.instruction,
            policy_description=policy.definition.description if policy else None,
            policy_instruction=policy.definition.instruction if policy else None,
        )
        session.add(flow_node)
        session.add(
            build_node_plan_revision_row(
                flow_revision=flow_revision,
                flow_node=flow_node,
                bootstrap_input=bootstrap_input,
                node=node,
                role_description=role.definition.description,
                role_instruction=role.definition.instruction,
                policy_description=policy.definition.description if policy else None,
                policy_instruction=policy.definition.instruction if policy else None,
            )
        )
    await session.flush()

    for edge in bootstrap_input.compiled_plan.dependency_edges:
        session.add(build_flow_edge_row(bootstrap_input=bootstrap_input, edge=edge))
    await session.flush()
