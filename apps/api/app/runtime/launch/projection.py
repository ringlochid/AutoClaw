from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.compiler import NormalizedCompiledNode, NormalizedCompiledPlan
from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    ManifestCurrentContextProjection,
    ManifestDependencyProjection,
    ManifestFilesystemRootsProjection,
    ManifestNodeConsumeProjection,
    ManifestNodeCriteriaProjection,
    ManifestNodeProduceProjection,
    ManifestNodeProjection,
    ManifestProjection,
    ManifestTaskProjection,
    ManifestWorkflowProjection,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    PersistedPromptRecord,
    ProduceRequirement,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    PromptTransportRequest,
    ResolvedNodeContext,
    RuntimeBootstrapResult,
    RuntimeContextRef,
    TaskRootPaths,
    _RuntimeBootstrapProjectionInput,
)
from app.runtime.prompt.bundle import render_prompt_bundle
from app.runtime.resources import (
    assignment_markdown_path,
    checkpoint_markdown_path,
    criteria_file_path,
    ensure_task_root_layout,
    localize_assignment_projection,
    localize_checkpoint_projection,
    localize_manifest_projection,
    prompt_markdown_path,
    prompt_request_json_path,
    resolve_task_root_paths,
    stable_json_hash,
    write_assignment_projection,
    write_checkpoint_projection,
    write_criteria_files,
    write_manifest_projection,
    write_prompt_artifact,
)


def _compiled_nodes_by_key(
    compiled_plan: NormalizedCompiledPlan,
) -> dict[str, NormalizedCompiledNode]:
    return {node.node_key: node for node in compiled_plan.nodes}


def _criteria_descriptions_by_slot(compiled_plan: NormalizedCompiledPlan) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for node in compiled_plan.nodes:
        for criteria in node.criteria:
            descriptions[criteria.slot] = criteria.description
    return descriptions


def _merge_criteria_refs(
    *criteria_groups: tuple[EvidenceRef, ...],
) -> tuple[EvidenceRef, ...]:
    merged: list[EvidenceRef] = []
    seen_slots: set[str] = set()
    for group in criteria_groups:
        for ref in group:
            if ref.slot is None:
                merged.append(ref)
                continue
            if ref.slot in seen_slots:
                continue
            seen_slots.add(ref.slot)
            merged.append(ref)
    return tuple(merged)


def _resolve_node_context(
    *,
    compiled_plan: NormalizedCompiledPlan,
    current_node_key: str,
    bootstrap_input: _RuntimeBootstrapProjectionInput,
) -> ResolvedNodeContext:
    compiled_node = _compiled_nodes_by_key(compiled_plan).get(current_node_key)
    if compiled_node is None:
        raise ValueError(f"unknown current_node_key '{current_node_key}'")

    role_revision = bootstrap_input.role_policy_lookup.get_role(compiled_node.role)
    if role_revision is None:
        raise ValueError(f"missing role definition for '{compiled_node.role}'")

    policy_revision = None
    if compiled_node.policy is not None:
        policy_revision = bootstrap_input.role_policy_lookup.get_policy(compiled_node.policy)
        if policy_revision is None:
            raise ValueError(f"missing policy definition for '{compiled_node.policy}'")

    return ResolvedNodeContext(
        node_key=compiled_node.node_key,
        node_kind=compiled_node.structural_kind,
        node_description=compiled_node.description,
        role_key=compiled_node.role,
        role_revision_no=compiled_node.role_revision_no,
        role_description=role_revision.definition.description,
        role_instruction=role_revision.definition.instruction,
        policy_key=compiled_node.policy,
        policy_revision_no=compiled_node.policy_revision_no,
        policy_description=policy_revision.definition.description if policy_revision else None,
        policy_instruction=policy_revision.definition.instruction if policy_revision else None,
    )


def _build_launch_assignment(
    *,
    bootstrap_input: _RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    criteria_paths: dict[str, Path],
) -> AssignmentProjection:
    if current_node.node_key != "root":
        raise ValueError(
            "Phase 2 automatic assignment generation only supports the launch/root path; "
            "later node assignments require explicit projected assignment input so Phase 3 "
            "runtime truth is not guessed early."
        )

    compiled_node = _compiled_nodes_by_key(bootstrap_input.compiled_plan)[current_node.node_key]
    if compiled_node.consumes is not None and compiled_node.consumes.artifacts:
        raise ValueError(
            "Phase 2 automatic assignment generation does not resolve artifact consumes; "
            "provide an explicit projected assignment instead."
        )

    criteria_refs = tuple(
        EvidenceRef(
            kind=EvidenceKind.CRITERIA,
            slot=criteria.slot,
            path=criteria_paths[criteria.slot],
            description=criteria.description,
        )
        for criteria in compiled_node.criteria
    )
    selector_criteria_refs = tuple(
        EvidenceRef(
            kind=EvidenceKind.CRITERIA,
            slot=selector.slot,
            path=criteria_paths[selector.slot],
            description=_criteria_descriptions_by_slot(bootstrap_input.compiled_plan)[
                selector.slot
            ],
        )
        for selector in (compiled_node.consumes.criteria if compiled_node.consumes else ())
    )
    consumes: tuple[EvidenceRef, ...] = ()
    produces = tuple(
        ProduceRequirement(
            slot=artifact.slot,
            description=artifact.description,
            file_hint=artifact.file_hint,
        )
        for artifact in (compiled_node.produces.artifacts if compiled_node.produces else ())
    )

    instruction_parts = []
    if bootstrap_input.task_compose.task.instruction is not None:
        instruction_parts.append(bootstrap_input.task_compose.task.instruction)
    instruction_parts.append(f"Node purpose: {current_node.node_description}")
    instruction_parts.append(f"Role guidance: {current_node.role_description}")
    if current_node.role_instruction is not None:
        instruction_parts.append(current_node.role_instruction)
    if current_node.policy_description is not None:
        instruction_parts.append(f"Policy guidance: {current_node.policy_description}")
    if current_node.policy_instruction is not None:
        instruction_parts.append(current_node.policy_instruction)

    return AssignmentProjection(
        assignment_key=bootstrap_input.assignment_key,
        node_key=current_node.node_key,
        summary=bootstrap_input.task_compose.task.summary,
        instruction="\n".join(instruction_parts).strip() or None,
        criteria=_merge_criteria_refs(criteria_refs, selector_criteria_refs),
        consumes=consumes,
        produces=produces,
    )


def _dependency_maps(
    compiled_plan: NormalizedCompiledPlan,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[tuple[str, str, str], str]]:
    depends_on: dict[str, set[str]] = {}
    depended_on_by: dict[str, set[str]] = {}
    descriptions: dict[tuple[str, str, str], str] = {}
    for edge in compiled_plan.dependency_edges:
        depends_on.setdefault(edge.consumer_node_key, set()).add(edge.provider_node_key)
        depended_on_by.setdefault(edge.provider_node_key, set()).add(edge.consumer_node_key)
        descriptions[(edge.consumer_node_key, edge.kind.value, edge.slot)] = edge.description
    return depends_on, depended_on_by, descriptions


def _build_manifest_node_projection(
    *,
    compiled_node: NormalizedCompiledNode,
    criteria_paths: dict[str, Path],
    depends_on: dict[str, set[str]],
    depended_on_by: dict[str, set[str]],
    dependency_descriptions: dict[tuple[str, str, str], str],
    criteria_descriptions: dict[str, str],
) -> ManifestNodeProjection:
    consumes: list[ManifestNodeConsumeProjection] = []
    if compiled_node.consumes is not None:
        for selector in compiled_node.consumes.artifacts:
            consumes.append(
                ManifestNodeConsumeProjection(
                    kind=EvidenceKind.ARTIFACT,
                    slot=selector.slot,
                    description=dependency_descriptions[
                        (compiled_node.node_key, EvidenceKind.ARTIFACT.value, selector.slot)
                    ],
                    required=selector.required,
                )
            )
        for selector in compiled_node.consumes.criteria:
            consumes.append(
                ManifestNodeConsumeProjection(
                    kind=EvidenceKind.CRITERIA,
                    slot=selector.slot,
                    description=criteria_descriptions[selector.slot],
                    required=selector.required,
                )
            )

    criteria = tuple(
        ManifestNodeCriteriaProjection(
            owner_node_key=criteria_declaration.owner_node_key,
            slot=criteria_declaration.slot,
            description=criteria_declaration.description,
            path=criteria_paths[criteria_declaration.slot],
        )
        for criteria_declaration in compiled_node.criteria
    )
    produces = tuple(
        ManifestNodeProduceProjection(
            slot=artifact.slot,
            description=artifact.description,
            file_hint=artifact.file_hint,
        )
        for artifact in (compiled_node.produces.artifacts if compiled_node.produces else ())
    )
    return ManifestNodeProjection(
        node_key=compiled_node.node_key,
        parent_node_key=compiled_node.parent_node_key,
        child_node_keys=compiled_node.child_node_keys,
        node_kind=compiled_node.structural_kind,
        role=compiled_node.role,
        description=compiled_node.description,
        consumes=tuple(consumes),
        produces=produces,
        criteria=criteria,
        depends_on_node_keys=tuple(sorted(depends_on.get(compiled_node.node_key, set()))),
        depended_on_by_node_keys=tuple(sorted(depended_on_by.get(compiled_node.node_key, set()))),
    )


def _build_manifest_projection(
    *,
    bootstrap_input: _RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    criteria_paths: dict[str, Path],
    assignment: AssignmentProjection,
    latest_checkpoint: CheckpointProjection | None,
    task_root_paths: TaskRootPaths,
) -> ManifestProjection:
    depends_on, depended_on_by, dependency_descriptions = _dependency_maps(
        bootstrap_input.compiled_plan
    )
    criteria_descriptions = _criteria_descriptions_by_slot(bootstrap_input.compiled_plan)
    current_relevant_paths: list[RuntimeContextRef] = [
        *assignment.criteria,
        *assignment.consumes,
        *assignment.transient_refs,
    ]
    latest_checkpoint_path = None
    if latest_checkpoint is not None:
        latest_checkpoint_path = checkpoint_markdown_path(
            paths=task_root_paths,
            attempt_id=bootstrap_input.attempt_id,
        )
        current_relevant_paths.append(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=latest_checkpoint_path,
                description="Latest durable checkpoint for the current attempt.",
            )
        )

    node_tree = tuple(
        _build_manifest_node_projection(
            compiled_node=compiled_node,
            criteria_paths=criteria_paths,
            depends_on=depends_on,
            depended_on_by=depended_on_by,
            dependency_descriptions=dependency_descriptions,
            criteria_descriptions=criteria_descriptions,
        )
        for compiled_node in bootstrap_input.compiled_plan.nodes
    )
    dependency_index = tuple(
        ManifestDependencyProjection(
            provider_node_key=edge.provider_node_key,
            consumer_node_key=edge.consumer_node_key,
            kind=edge.kind.value,
            slot=edge.slot,
            description=edge.description,
        )
        for edge in bootstrap_input.compiled_plan.dependency_edges
    )
    return ManifestProjection(
        active_flow_revision_id=bootstrap_input.active_flow_revision_id,
        generated_at=datetime.now(tz=UTC),
        task=ManifestTaskProjection(
            task_id=bootstrap_input.task_id,
            task_key=bootstrap_input.task_compose.task.key,
            title=bootstrap_input.task_compose.task.title,
            summary=bootstrap_input.task_compose.task.summary,
            instruction=bootstrap_input.task_compose.task.instruction,
        ),
        workflow=ManifestWorkflowProjection(
            workflow_key=bootstrap_input.workflow_definition.id,
            description=bootstrap_input.workflow_definition.description,
        ),
        filesystem_roots=ManifestFilesystemRootsProjection(
            workspace_path=task_root_paths.workspace_path,
            context_path=task_root_paths.context_path,
            outputs_path=task_root_paths.outputs_path,
            tmp_path=task_root_paths.tmp_path,
            runtime_path=task_root_paths.runtime_path,
        ),
        current_context=ManifestCurrentContextProjection(
            current_node_key=current_node.node_key,
            owner_node_key=bootstrap_input.owner_node_key or current_node.node_key,
            active_attempt_id=bootstrap_input.attempt_id,
            active_assignment_path=assignment_markdown_path(
                paths=task_root_paths,
                attempt_id=bootstrap_input.attempt_id,
            ),
            latest_checkpoint_path=latest_checkpoint_path,
            latest_relevant_checkpoint_path=None,
            current_relevant_paths=tuple(current_relevant_paths),
        ),
        node_tree=node_tree,
        dependency_index=dependency_index,
    )


def _prompt_family_for_node_kind(node_kind: NodeKind) -> PromptFamily:
    if node_kind == NodeKind.WORKER:
        return PromptFamily.WORKER_DISPATCH
    return PromptFamily.PARENT_ROOT_DISPATCH


def _build_bootstrap_runtime_projection_result(
    bootstrap_input: _RuntimeBootstrapProjectionInput,
) -> RuntimeBootstrapResult:
    task_root_paths = resolve_task_root_paths(
        task_root=bootstrap_input.task_root,
        task_compose=bootstrap_input.task_compose,
    )
    criteria_paths = {
        criteria.slot: criteria_file_path(paths=task_root_paths, slot=criteria.slot, version=1)
        for node in bootstrap_input.compiled_plan.nodes
        for criteria in node.criteria
    }
    current_node = _resolve_node_context(
        compiled_plan=bootstrap_input.compiled_plan,
        current_node_key=bootstrap_input.current_node_key,
        bootstrap_input=bootstrap_input,
    )
    assignment = bootstrap_input.assignment or _build_launch_assignment(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        criteria_paths=criteria_paths,
    )
    if assignment.node_key != current_node.node_key:
        raise ValueError(
            f"assignment node_key '{assignment.node_key}' does not match current node "
            f"'{current_node.node_key}'"
        )

    manifest = _build_manifest_projection(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        criteria_paths=criteria_paths,
        assignment=assignment,
        latest_checkpoint=bootstrap_input.latest_checkpoint,
        task_root_paths=task_root_paths,
    )
    prompt_bundle = render_prompt_bundle(
        PromptRenderRequest(
            prompt_family=_prompt_family_for_node_kind(current_node.node_kind),
            send_mode=PromptSendMode.FULL_PROMPT,
            task_id=bootstrap_input.task_id,
            current_node=current_node,
            manifest=manifest,
            assignment=assignment,
            latest_checkpoint=bootstrap_input.latest_checkpoint,
        )
    )
    transport_request = PromptTransportRequest(
        send_mode=prompt_bundle.send_mode,
        previous_response_id=None,
        instructions_text=prompt_bundle.instructions_text,
        input_text=prompt_bundle.input_text,
    )
    prompt_record = PersistedPromptRecord(
        dispatch_id=bootstrap_input.dispatch_id,
        node_key=current_node.node_key,
        attempt_id=bootstrap_input.attempt_id,
        assignment_key=assignment.assignment_key,
        prompt_name=prompt_bundle.prompt_family,
        send_mode=prompt_bundle.send_mode,
        rendered_markdown_path=prompt_markdown_path(
            paths=task_root_paths,
            dispatch_id=bootstrap_input.dispatch_id,
        ),
        transport_request_path=prompt_request_json_path(
            paths=task_root_paths,
            dispatch_id=bootstrap_input.dispatch_id,
        ),
        content_hash=prompt_bundle.content_hash,
        transport_request_hash=stable_json_hash(transport_request),
        rendered_at=datetime.now(tz=UTC),
        transport_request=transport_request,
    )

    return RuntimeBootstrapResult(
        paths=task_root_paths,
        manifest=manifest,
        assignment=assignment,
        latest_checkpoint=bootstrap_input.latest_checkpoint,
        prompt_bundle=prompt_bundle,
        prompt_record=prompt_record,
    )


def _bootstrap_task_runtime_projection(
    bootstrap_input: _RuntimeBootstrapProjectionInput,
) -> RuntimeBootstrapResult:
    result = _build_bootstrap_runtime_projection_result(bootstrap_input)
    ensure_task_root_layout(result.paths)
    write_criteria_files(
        paths=result.paths,
        compiled_plan=bootstrap_input.compiled_plan,
    )

    current_node = _resolve_node_context(
        compiled_plan=bootstrap_input.compiled_plan,
        current_node_key=bootstrap_input.current_node_key,
        bootstrap_input=bootstrap_input,
    )
    assignment = localize_assignment_projection(paths=result.paths, assignment=result.assignment)
    latest_checkpoint = (
        localize_checkpoint_projection(paths=result.paths, checkpoint=result.latest_checkpoint)
        if result.latest_checkpoint is not None
        else None
    )
    manifest = localize_manifest_projection(paths=result.paths, manifest=result.manifest)
    prompt_bundle = render_prompt_bundle(
        PromptRenderRequest(
            prompt_family=_prompt_family_for_node_kind(current_node.node_kind),
            send_mode=PromptSendMode.FULL_PROMPT,
            task_id=bootstrap_input.task_id,
            current_node=current_node,
            manifest=manifest,
            assignment=assignment,
            latest_checkpoint=latest_checkpoint,
        )
    )
    transport_request = PromptTransportRequest(
        send_mode=prompt_bundle.send_mode,
        previous_response_id=None,
        instructions_text=prompt_bundle.instructions_text,
        input_text=prompt_bundle.input_text,
    )
    prompt_record = result.prompt_record.model_copy(
        update={
            "assignment_key": assignment.assignment_key,
            "content_hash": prompt_bundle.content_hash,
            "transport_request_hash": stable_json_hash(transport_request),
            "transport_request": transport_request,
        }
    )
    result = result.model_copy(
        update={
            "manifest": manifest,
            "assignment": assignment,
            "latest_checkpoint": latest_checkpoint,
            "prompt_bundle": prompt_bundle,
            "prompt_record": prompt_record,
        }
    )

    write_manifest_projection(paths=result.paths, manifest=result.manifest)
    write_assignment_projection(
        paths=result.paths,
        attempt_id=bootstrap_input.attempt_id,
        assignment=result.assignment,
    )
    if result.latest_checkpoint is not None:
        write_checkpoint_projection(
            paths=result.paths,
            attempt_id=bootstrap_input.attempt_id,
            checkpoint=result.latest_checkpoint,
        )
    write_prompt_artifact(
        paths=result.paths,
        prompt_record=result.prompt_record,
        full_markdown=result.prompt_bundle.full_markdown,
    )
    return result
