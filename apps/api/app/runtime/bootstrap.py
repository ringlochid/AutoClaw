from __future__ import annotations

from secrets import token_urlsafe

from sqlalchemy.ext.asyncio import AsyncSession

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
    DispatchCallbackBindingModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    ManifestRootModel,
    NodePlanRevisionModel,
    TaskComposeModel,
    TaskModel,
    TaskResourceBindingModel,
    WorkspaceRootModel,
)
from app.runtime.contracts import (
    EvidenceRef,
    NodeRuntimeFileRef,
    RuntimeBootstrapInput,
    RuntimeBootstrapResult,
)
from app.runtime.dispatcher import bootstrap_task_runtime
from app.runtime.ids import (
    artifact_publication_id,
    assignment_criteria_ref_id,
    assignment_id,
    attempt_consumed_ref_id,
    compiled_plan_edge_id,
    compiled_plan_id_for_task,
    compiled_plan_node_id,
    context_space_id_for_task,
    dispatch_callback_binding_id,
    flow_edge_id,
    flow_id_for_task,
    flow_node_id,
    manifest_root_id_for_task,
    node_plan_revision_id,
    task_compose_id_for_task,
    task_resource_binding_id,
    workspace_root_id_for_task,
)
from app.runtime.projector import materialize_dispatch_files


def _binding_paths(paths: RuntimeBootstrapResult) -> dict[str, str]:
    return {
        "workspace": str(paths.paths.workspace_path),
        "context": str(paths.paths.context_path),
        "criteria": str(paths.paths.criteria_path),
        "wiki": str(paths.paths.wiki_path),
        "outputs": str(paths.paths.outputs_path),
        "artifacts": str(paths.paths.artifacts_path),
        "tmp": str(paths.paths.tmp_path),
        "transfers": str(paths.paths.transfers_path),
        "runtime": str(paths.paths.runtime_path),
        "attempts": str(paths.paths.attempts_path),
        "dispatch": str(paths.paths.dispatch_path),
    }


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
                order_index=index,
            )
        )


async def persist_bootstrap_runtime(
    session: AsyncSession,
    bootstrap_input: RuntimeBootstrapInput,
) -> RuntimeBootstrapResult:
    result = bootstrap_task_runtime(bootstrap_input)
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
        role = bootstrap_input.role_policy_lookup.get_role(node.role)
        if role is None:
            raise ValueError(f"missing role definition for '{node.role}'")
        policy = None
        if node.policy is not None:
            policy = bootstrap_input.role_policy_lookup.get_policy(node.policy)
            if policy is None:
                raise ValueError(f"missing policy definition for '{node.policy}'")
        session.add(
            CompiledPlanNodeModel(
                compiled_plan_node_id=compiled_plan_node_id(compiled_plan_id, node.node_key),
                compiled_plan_id=compiled_plan_id,
                node_key=node.node_key,
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
                criteria_json=[criteria.model_dump(mode="json") for criteria in node.criteria],
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
            current_open_dispatch_id=bootstrap_input.dispatch_id,
            current_node_key=bootstrap_input.current_node_key,
        )
    )
    session.add(
        FlowRevisionModel(
            flow_revision_id=bootstrap_input.active_flow_revision_id,
            flow_id=flow_id,
            revision_index=1,
            snapshot_json=bootstrap_input.compiled_plan.model_dump(mode="json"),
        )
    )
    await session.flush()

    for node in bootstrap_input.compiled_plan.nodes:
        role = bootstrap_input.role_policy_lookup.get_role(node.role)
        if role is None:
            raise ValueError(f"missing role definition for '{node.role}'")
        policy = None
        if node.policy is not None:
            policy = bootstrap_input.role_policy_lookup.get_policy(node.policy)
            if policy is None:
                raise ValueError(f"missing policy definition for '{node.policy}'")
        session.add(
            FlowNodeModel(
                flow_node_id=flow_node_id(bootstrap_input.active_flow_revision_id, node.node_key),
                flow_revision_id=bootstrap_input.active_flow_revision_id,
                node_key=node.node_key,
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
                criteria_json=[criteria.model_dump(mode="json") for criteria in node.criteria],
                child_defaults_json=node.child_defaults.model_dump(mode="json")
                if node.child_defaults
                else None,
                current_assignment_id=assignment_id(result.assignment.assignment_key)
                if node.node_key == result.assignment.node_key
                else None,
                order_index=node.order_index,
            )
        )
        session.add(
            NodePlanRevisionModel(
                node_plan_revision_id=node_plan_revision_id(
                    bootstrap_input.active_flow_revision_id,
                    node.node_key,
                ),
                flow_revision_id=bootstrap_input.active_flow_revision_id,
                flow_node_id=flow_node_id(bootstrap_input.active_flow_revision_id, node.node_key),
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
        created_by_dispatch_id=bootstrap_input.dispatch_id,
    )
    session.add(assignment_row)
    await session.flush()
    _stage_assignment_criteria_refs(session, assignment_row)
    session.add(
        AttemptModel(
            attempt_id=bootstrap_input.attempt_id,
            assignment_id=assignment_row.assignment_id,
            task_id=bootstrap_input.task_id,
            node_key=result.assignment.node_key,
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
                attempt_id=bootstrap_input.attempt_id,
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
                produced_artifacts_json=[
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
                    slot=artifact_ref.slot or f"artifact-{index}",
                    version=artifact_ref.version or index,
                    path=str(artifact_ref.path),
                    description=artifact_ref.description,
                    order_index=index,
                )
            )
    session.add(
        DispatchTurnModel(
            dispatch_id=bootstrap_input.dispatch_id,
            flow_id=flow_id,
            task_id=bootstrap_input.task_id,
            node_key=result.assignment.node_key,
            assignment_id=assignment_id(result.assignment.assignment_key),
            assignment_key=result.assignment.assignment_key,
            attempt_id=bootstrap_input.attempt_id,
            prompt_name=result.prompt_record.prompt_name.value,
            send_mode=result.prompt_record.send_mode.value,
            delivery_status="accepted",
            control_state="live",
            prompt_path=str(result.prompt_record.rendered_markdown_path),
            content_hash=result.prompt_record.content_hash,
            rendered_at=result.prompt_record.rendered_at,
        )
    )
    session.add(
        DispatchDeliveryStateModel(
            dispatch_id=bootstrap_input.dispatch_id,
            task_id=bootstrap_input.task_id,
            attempt_id=bootstrap_input.attempt_id,
            assignment_key=result.assignment.assignment_key,
            node_key=result.assignment.node_key,
            transport_family="phase3_local_runtime",
            transport_state="accepted",
            controller_observation_state="live",
            send_mode=result.prompt_record.send_mode.value,
            accepted_at=result.prompt_record.rendered_at,
        )
    )
    session.add(
        DispatchContinuityStateModel(
            dispatch_id=bootstrap_input.dispatch_id,
            task_id=bootstrap_input.task_id,
            attempt_id=bootstrap_input.attempt_id,
            assignment_key=result.assignment.assignment_key,
            node_key=result.assignment.node_key,
            continuity_state="candidate",
            session_key_present=False,
        )
    )
    session.add(
        DispatchWatchdogStateModel(
            dispatch_id=bootstrap_input.dispatch_id,
            task_id=bootstrap_input.task_id,
            attempt_id=bootstrap_input.attempt_id,
            assignment_key=result.assignment.assignment_key,
            node_key=result.assignment.node_key,
            watchdog_state="clear",
        )
    )
    await session.flush()
    session.add(
        DispatchCallbackBindingModel(
            dispatch_callback_binding_id=dispatch_callback_binding_id(bootstrap_input.dispatch_id),
            dispatch_id=bootstrap_input.dispatch_id,
            attempt_id=bootstrap_input.attempt_id,
            assignment_id=assignment_row.assignment_id,
            task_id=bootstrap_input.task_id,
            session_key=token_urlsafe(24),
            binding_status="live",
        )
    )
    await session.flush()
    await materialize_dispatch_files(session, bootstrap_input.task_id, bootstrap_input.dispatch_id)
    return result
