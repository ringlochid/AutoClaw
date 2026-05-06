from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compiler import (
    MappingRolePolicyLookup,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
)
from app.db.models import (
    AssignmentCriteriaRefModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    AttemptProducedRefModel,
    CompiledPlanEdgeModel,
    CompiledPlanModel,
    CompiledPlanNodeModel,
    ContextSpaceModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    ManifestRootModel,
    NodePlanRevisionModel,
    TaskComposeModel,
    TaskModel,
    TaskResourceBindingModel,
    WorkspaceRootLeaseModel,
    WorkspaceRootModel,
)
from app.runtime.contracts import (
    EvidenceRef,
    NodeRuntimeFileRef,
    RuntimeBootstrapResult,
    _RuntimeBootstrapProjectionInput,
)
from app.runtime.ids import (
    artifact_publication_id,
    assignment_criteria_ref_id,
    assignment_id,
    attempt_consumed_ref_id,
    compiled_plan_edge_id,
    compiled_plan_id_for_task,
    compiled_plan_node_id,
    context_space_id_for_task,
    flow_edge_id,
    flow_id_for_task,
    flow_node_id,
    manifest_root_id_for_task,
    node_plan_revision_id,
    task_compose_id_for_task,
    task_resource_binding_id,
    workspace_root_id_for_task,
)
from app.runtime.launch.projection import _build_bootstrap_runtime_projection_result
from app.runtime.projection import (
    materialize_attempt_files,
    materialize_manifest,
)
from app.runtime.resources import criteria_file_path


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _binding_paths(result: RuntimeBootstrapResult) -> dict[str, str]:
    return {
        "workspace": str(result.paths.workspace_path),
        "context": str(result.paths.context_path),
        "criteria": str(result.paths.criteria_path),
        "wiki": str(result.paths.wiki_path),
        "outputs": str(result.paths.outputs_path),
        "artifacts": str(result.paths.artifacts_path),
        "tmp": str(result.paths.tmp_path),
        "transfers": str(result.paths.transfers_path),
        "runtime": str(result.paths.runtime_path),
        "attempts": str(result.paths.attempts_path),
        "dispatch": str(result.paths.dispatch_path),
    }


def _workspace_binding_requires_lease(binding_mode: str) -> bool:
    return binding_mode != "ensure_task_default"


def _workspace_root_lease_id(task_id: str) -> str:
    return f"workspace-root-lease.{task_id}"


def _consume_json(ref: EvidenceRef | NodeRuntimeFileRef) -> dict[str, object]:
    return ref.model_dump(mode="json")


def _stage_assignment_criteria_refs(session: AsyncSession, assignment: AssignmentModel) -> None:
    for index, criteria in enumerate(assignment.criteria_json, start=1):
        slot = str(criteria["slot"])
        session.add(
            AssignmentCriteriaRefModel(
                assignment_criteria_ref_id=assignment_criteria_ref_id(
                    assignment.assignment_id,
                    slot,
                ),
                assignment_id=assignment.assignment_id,
                slot=slot,
                path=str(criteria["path"]),
                description=str(criteria["description"]),
                version=criteria.get("version"),
                order_index=index,
            )
        )


def _pinned_role_policy_for_node(
    lookup: MappingRolePolicyLookup,
    *,
    role_key: str,
    role_revision_no: int,
    policy_key: str | None,
    policy_revision_no: int | None,
) -> tuple[RoleRevisionDefinition, PolicyRevisionDefinition | None]:
    role = lookup.get_role(role_key)
    if role is None:
        raise ValueError(f"missing role definition for '{role_key}'")
    if role.revision_no != role_revision_no:
        raise ValueError(
            "role "
            f"'{role_key}' resolved revision {role.revision_no} but node pins "
            f"{role_revision_no}"
        )
    policy = None
    if policy_key is not None:
        policy = lookup.get_policy(policy_key)
        if policy is None:
            raise ValueError(f"missing policy definition for '{policy_key}'")
        if policy.revision_no != policy_revision_no:
            raise ValueError(
                "policy "
                f"'{policy_key}' resolved revision {policy.revision_no} but node pins "
                f"{policy_revision_no}"
            )
    return role, policy


async def _acquire_workspace_root_lease(
    session: AsyncSession,
    *,
    task_id: str,
    flow_id: str,
    workspace_root_path: str,
    binding_mode: str,
) -> None:
    if not _workspace_binding_requires_lease(binding_mode):
        return
    normalized_path = await asyncio.to_thread(
        lambda: str(Path(workspace_root_path).expanduser().resolve())
    )
    existing_lease = await session.scalar(
        select(WorkspaceRootLeaseModel).where(
            WorkspaceRootLeaseModel.normalized_workspace_root_path == normalized_path
        )
    )
    if existing_lease is not None and existing_lease.lease_status == "live":
        raise ValueError(f"workspace host path already held by live task: {normalized_path}")
    if existing_lease is not None:
        existing_lease.task_id = task_id
        existing_lease.flow_id = flow_id
        existing_lease.lease_status = "live"
        existing_lease.leased_at = _now()
        existing_lease.released_at = None
        return
    session.add(
        WorkspaceRootLeaseModel(
            workspace_root_lease_id=_workspace_root_lease_id(task_id),
            normalized_workspace_root_path=normalized_path,
            task_id=task_id,
            flow_id=flow_id,
            lease_status="live",
        )
    )


async def persist_bootstrap_runtime_from_precomputed(
    session: AsyncSession,
    bootstrap_input: _RuntimeBootstrapProjectionInput,
    *,
    commit: bool = True,
) -> RuntimeBootstrapResult:
    result = _build_bootstrap_runtime_projection_result(bootstrap_input)
    binding_paths = _binding_paths(result)
    compiled_plan_id = compiled_plan_id_for_task(bootstrap_input.task_id)
    flow_id = flow_id_for_task(bootstrap_input.task_id)
    roots = bootstrap_input.task_compose.roots
    workspace_binding_mode = (
        roots.workspace.mode.value
        if roots is not None and roots.workspace is not None
        else "ensure_task_default"
    )
    context_binding_mode = (
        roots.context.mode.value
        if roots is not None and roots.context is not None
        else "ensure_task_default"
    )

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
            binding_mode=workspace_binding_mode,
        )
    )
    session.add(
        ContextSpaceModel(
            context_space_id=context_space_id_for_task(bootstrap_input.task_id),
            task_id=bootstrap_input.task_id,
            path=str(result.paths.context_path),
            binding_mode=context_binding_mode,
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
            compiled_plan_id=compiled_plan_id,
            workspace_root_path=str(result.paths.workspace_path),
            context_root_path=str(result.paths.context_path),
            outputs_root_path=str(result.paths.outputs_path),
            runtime_root_path=str(result.paths.runtime_path),
            compose_payload=bootstrap_input.task_compose.model_dump(mode="json"),
        )
    )
    session.add(
        CompiledPlanModel(
            compiled_plan_id=compiled_plan_id,
            task_id=bootstrap_input.task_id,
            workflow_key=bootstrap_input.compiled_plan.workflow_key,
            definition_revision_no=bootstrap_input.compiled_plan.definition_revision_no,
            compiler_version=bootstrap_input.compiled_plan.compiler_version,
            snapshot_json=bootstrap_input.compiled_plan.model_dump(mode="json"),
        )
    )
    for binding_kind, path in binding_paths.items():
        session.add(
            TaskResourceBindingModel(
                task_resource_binding_id=task_resource_binding_id(
                    bootstrap_input.task_id, binding_kind
                ),
                task_id=bootstrap_input.task_id,
                binding_kind=binding_kind,
                path=path,
                binding_mode=None,
            )
        )

    await session.flush()

    for node in bootstrap_input.compiled_plan.nodes:
        role, policy = _pinned_role_policy_for_node(
            bootstrap_input.role_policy_lookup,
            role_key=node.role,
            role_revision_no=node.role_revision_no,
            policy_key=node.policy,
            policy_revision_no=node.policy_revision_no,
        )
        session.add(
            CompiledPlanNodeModel(
                compiled_plan_node_id=compiled_plan_node_id(compiled_plan_id, node.node_key),
                compiled_plan_id=compiled_plan_id,
                node_key=node.node_key,
                parent_compiled_plan_node_id=(
                    compiled_plan_node_id(compiled_plan_id, node.parent_node_key)
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
                criteria_json=[
                    criteria.model_dump(mode="json")
                    | {
                        "version": 1,
                        "path": str(
                            criteria_file_path(paths=result.paths, slot=criteria.slot, version=1)
                        ),
                    }
                    for criteria in node.criteria
                ],
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
                    compiled_plan_id,
                    edge.consumer_node_key,
                    edge.kind.value,
                    edge.slot,
                ),
                compiled_plan_id=compiled_plan_id,
                provider_compiled_plan_node_id=compiled_plan_node_id(
                    compiled_plan_id, edge.provider_node_key
                ),
                consumer_compiled_plan_node_id=compiled_plan_node_id(
                    compiled_plan_id, edge.consumer_node_key
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
    session.add(
        FlowModel(
            flow_id=flow_id,
            task_id=bootstrap_input.task_id,
            compiled_plan_id=compiled_plan_id,
            status="running",
            active_flow_revision_id=bootstrap_input.active_flow_revision_id,
            current_open_dispatch_id=None,
            current_node_key=bootstrap_input.current_node_key,
        )
    )
    flow_revision = FlowRevisionModel(
        flow_revision_id=bootstrap_input.active_flow_revision_id,
        flow_id=flow_id,
        revision_index=1,
        source_compiled_plan_id=compiled_plan_id,
        cause="launch",
        snapshot_json=bootstrap_input.compiled_plan.model_dump(mode="json"),
    )
    session.add(flow_revision)
    await session.flush()
    await _acquire_workspace_root_lease(
        session,
        task_id=bootstrap_input.task_id,
        flow_id=flow_id,
        workspace_root_path=str(result.paths.workspace_path),
        binding_mode=workspace_binding_mode,
    )

    for node in bootstrap_input.compiled_plan.nodes:
        role, policy = _pinned_role_policy_for_node(
            bootstrap_input.role_policy_lookup,
            role_key=node.role,
            role_revision_no=node.role_revision_no,
            policy_key=node.policy,
            policy_revision_no=node.policy_revision_no,
        )
        flow_node = FlowNodeModel(
            flow_node_id=flow_node_id(bootstrap_input.active_flow_revision_id, node.node_key),
            flow_id=flow_id,
            flow_revision=flow_revision,
            node_key=node.node_key,
            parent_flow_node_id=(
                flow_node_id(bootstrap_input.active_flow_revision_id, node.parent_node_key)
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
            criteria_json=[
                criteria.model_dump(mode="json")
                | {
                    "version": 1,
                    "path": str(
                        criteria_file_path(paths=result.paths, slot=criteria.slot, version=1)
                    ),
                }
                for criteria in node.criteria
            ],
            child_defaults_json=node.child_defaults.model_dump(mode="json")
            if node.child_defaults
            else None,
            current_assignment_id=assignment_id(result.assignment.assignment_key)
            if node.node_key == result.assignment.node_key
            else None,
            order_index=node.order_index,
        )
        session.add(flow_node)
        session.add(
            NodePlanRevisionModel(
                node_plan_revision_id=node_plan_revision_id(
                    bootstrap_input.active_flow_revision_id,
                    node.node_key,
                ),
                flow_revision=flow_revision,
                flow_node=flow_node,
                role_key=node.role,
                role_revision_no=node.role_revision_no,
                role_description=role.definition.description,
                role_instruction=role.definition.instruction,
                policy_key=node.policy,
                policy_revision_no=node.policy_revision_no,
                policy_description=policy.definition.description if policy else None,
                policy_instruction=policy.definition.instruction if policy else None,
            )
        )
    await session.flush()

    for edge in bootstrap_input.compiled_plan.dependency_edges:
        session.add(
            FlowEdgeModel(
                flow_edge_id=flow_edge_id(
                    bootstrap_input.active_flow_revision_id,
                    edge.consumer_node_key,
                    edge.kind.value,
                    edge.slot,
                ),
                flow_revision_id=bootstrap_input.active_flow_revision_id,
                provider_flow_node_id=flow_node_id(
                    bootstrap_input.active_flow_revision_id,
                    edge.provider_node_key,
                ),
                consumer_flow_node_id=flow_node_id(
                    bootstrap_input.active_flow_revision_id,
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

    assignment_row = AssignmentModel(
        assignment_id=assignment_id(result.assignment.assignment_key),
        task_id=bootstrap_input.task_id,
        flow_id=flow_id,
        flow_revision_id=bootstrap_input.active_flow_revision_id,
        flow_node_id=flow_node_id(
            bootstrap_input.active_flow_revision_id,
            result.assignment.node_key,
        ),
        assignment_key=result.assignment.assignment_key,
        node_key=result.assignment.node_key,
        summary=result.assignment.summary,
        instruction=result.assignment.instruction,
        criteria_json=[ref.model_dump(mode="json") for ref in result.assignment.criteria],
        consumes_json=[_consume_json(ref) for ref in result.assignment.consumes],
        produces_json=[req.model_dump(mode="json") for req in result.assignment.produces],
        transient_refs_json=[
            ref.model_dump(mode="json") for ref in result.assignment.transient_refs
        ],
        task_memory_search_hints_json=list(result.assignment.task_memory_search_hints),
        current_attempt_id=bootstrap_input.attempt_id,
        created_by_dispatch_id=None,
    )
    session.add(assignment_row)
    await session.flush()
    _stage_assignment_criteria_refs(session, assignment_row)
    session.add(
        AttemptModel(
            attempt_id=bootstrap_input.attempt_id,
            assignment_id=assignment_row.assignment_id,
            assignment_key=assignment_row.assignment_key,
            flow_node_id=assignment_row.flow_node_id,
            task_id=bootstrap_input.task_id,
            node_key=result.assignment.node_key,
            status="running",
            latest_checkpoint_id=(
                f"checkpoint.{bootstrap_input.attempt_id}.01"
                if result.latest_checkpoint is not None
                else None
            ),
        )
    )
    await session.flush()

    consumed_refs = [*result.assignment.criteria, *result.assignment.consumes]
    for index, ref in enumerate(consumed_refs, start=1):
        session.add(
            AttemptConsumedRefModel(
                attempt_consumed_ref_id=attempt_consumed_ref_id(bootstrap_input.attempt_id, index),
                attempt_id=bootstrap_input.attempt_id,
                ref_kind=ref.kind.value,
                slot=getattr(ref, "slot", None),
                version=getattr(ref, "version", None),
                path=str(ref.path),
                description=ref.description,
                order_index=index,
            )
        )
    if result.latest_checkpoint is not None:
        checkpoint_id = f"checkpoint.{bootstrap_input.attempt_id}.01"
        session.add(
            AttemptCheckpointModel(
                checkpoint_id=checkpoint_id,
                assignment_id=assignment_row.assignment_id,
                assignment_key=assignment_row.assignment_key,
                attempt_id=bootstrap_input.attempt_id,
                flow_node_id=assignment_row.flow_node_id,
                node_key=result.assignment.node_key,
                checkpoint_kind=result.latest_checkpoint.checkpoint_kind.value,
                outcome=(
                    result.latest_checkpoint.outcome.value
                    if result.latest_checkpoint.outcome
                    else None
                ),
                summary=result.latest_checkpoint.handoff.summary,
                next_step=result.latest_checkpoint.handoff.next_step,
                blockers_json=list(result.latest_checkpoint.handoff.blockers),
                risks_json=list(result.latest_checkpoint.handoff.risks),
                produced_artifact_claims_json=[
                    {
                        "kind": "artifact",
                        "slot": ref.slot,
                        "path": str(ref.path),
                    }
                    for ref in result.latest_checkpoint.produced_artifacts
                ],
                produced_artifacts_json=[
                    ref.model_dump(mode="json")
                    for ref in result.latest_checkpoint.produced_artifacts
                ],
                artifact_refs_json=[
                    ref.model_dump(mode="json")
                    for ref in result.latest_checkpoint.produced_artifacts
                ],
                transient_refs_json=[
                    ref.model_dump(mode="json") for ref in result.latest_checkpoint.transient_refs
                ],
                task_memory_search_hints_json=list(
                    result.latest_checkpoint.task_memory_search_hints
                ),
            )
        )
        for index, artifact_ref in enumerate(
            result.latest_checkpoint.produced_artifacts,
            start=1,
        ):
            session.add(
                AttemptProducedRefModel(
                    attempt_produced_ref_id=artifact_publication_id(
                        bootstrap_input.attempt_id,
                        artifact_ref.slot or f"artifact-{index}",
                        artifact_ref.version or index,
                    ),
                    attempt_id=bootstrap_input.attempt_id,
                    owner_node_key=result.assignment.node_key,
                    assignment_key=assignment_row.assignment_key,
                    slot=artifact_ref.slot or f"artifact-{index}",
                    version=artifact_ref.version or index,
                    path=str(artifact_ref.path),
                    description=artifact_ref.description,
                    became_current=True,
                    order_index=index,
                )
            )
    await session.flush()
    if not commit:
        return result
    await session.commit()
    await materialize_manifest(session, bootstrap_input.task_id)
    await materialize_attempt_files(session, bootstrap_input.task_id, bootstrap_input.attempt_id)
    return result
