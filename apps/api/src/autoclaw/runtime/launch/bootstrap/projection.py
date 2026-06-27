from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from autoclaw.definitions.compiler import NormalizedCompiledNode, NormalizedCompiledPlan
from autoclaw.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    ManifestProjection,
    PersistedPromptRecord,
    ProduceRequirement,
    PromptRenderRequest,
    PromptSendMode,
    PromptTransportRequest,
    RenderedPromptBundle,
    ResolvedNodeContext,
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
    TaskRootPaths,
    prompt_family_for_node_kind,
)
from autoclaw.runtime.errors import illegal_state_error, missing_resource_error
from autoclaw.runtime.launch.bootstrap.manifest import build_manifest_projection
from autoclaw.runtime.prompt.bundle import render_prompt_bundle
from autoclaw.runtime.task_root import (
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


def materialize_bootstrap_runtime_projection(
    bootstrap_input: RuntimeBootstrapProjectionInput,
) -> RuntimeBootstrapResult:
    result = build_bootstrap_runtime_projection_result(bootstrap_input)
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
    prompt_bundle, transport_request = _render_bootstrap_prompt(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        assignment=assignment,
        manifest=manifest,
        latest_checkpoint=latest_checkpoint,
    )
    prompt_record = result.prompt_record.model_copy(
        update={
            "assignment_key": assignment.assignment_key,
            "content_hash": prompt_bundle.content_hash,
            "transport_request_hash": stable_json_hash(transport_request),
            "transport_request": transport_request,
        }
    )
    localized_result = result.model_copy(
        update={
            "manifest": manifest,
            "assignment": assignment,
            "latest_checkpoint": latest_checkpoint,
            "prompt_bundle": prompt_bundle,
            "prompt_record": prompt_record,
        }
    )

    write_manifest_projection(paths=localized_result.paths, manifest=localized_result.manifest)
    write_assignment_projection(
        paths=localized_result.paths,
        attempt_id=bootstrap_input.attempt_id,
        assignment=localized_result.assignment,
    )
    if localized_result.latest_checkpoint is not None:
        write_checkpoint_projection(
            paths=localized_result.paths,
            attempt_id=bootstrap_input.attempt_id,
            checkpoint=localized_result.latest_checkpoint,
        )
    write_prompt_artifact(
        paths=localized_result.paths,
        prompt_record=localized_result.prompt_record,
        full_markdown=localized_result.prompt_bundle.full_markdown,
    )
    return localized_result


def build_bootstrap_runtime_projection_result(
    bootstrap_input: RuntimeBootstrapProjectionInput,
) -> RuntimeBootstrapResult:
    task_root_paths = resolve_task_root_paths(
        task_root=bootstrap_input.task_root,
        task_compose=bootstrap_input.task_compose,
    )
    criteria_paths = _criteria_paths(
        bootstrap_input,
        task_root_paths=task_root_paths,
    )
    criteria_descriptions = _criteria_descriptions_by_slot(bootstrap_input.compiled_plan)
    current_node = _resolve_node_context(
        compiled_plan=bootstrap_input.compiled_plan,
        current_node_key=bootstrap_input.current_node_key,
        bootstrap_input=bootstrap_input,
    )
    assignment = bootstrap_input.assignment or _build_launch_assignment(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        criteria_paths=criteria_paths,
        criteria_descriptions=criteria_descriptions,
    )
    if assignment.node_key != current_node.node_key:
        raise illegal_state_error(
            f"assignment node_key '{assignment.node_key}' does not match current node "
            f"'{current_node.node_key}'"
        )

    manifest = build_manifest_projection(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        criteria_paths=criteria_paths,
        criteria_descriptions=criteria_descriptions,
        assignment=assignment,
        latest_checkpoint=bootstrap_input.latest_checkpoint,
        task_root_paths=task_root_paths,
    )
    prompt_bundle, transport_request = _render_bootstrap_prompt(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        assignment=assignment,
        manifest=manifest,
        latest_checkpoint=bootstrap_input.latest_checkpoint,
    )
    prompt_record = _build_persisted_prompt_record(
        bootstrap_input=bootstrap_input,
        current_node=current_node,
        assignment=assignment,
        prompt_bundle=prompt_bundle,
        task_root_paths=task_root_paths,
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
    bootstrap_input: RuntimeBootstrapProjectionInput,
) -> ResolvedNodeContext:
    compiled_node = _compiled_nodes_by_key(compiled_plan).get(current_node_key)
    if compiled_node is None:
        raise illegal_state_error(f"unknown current_node_key '{current_node_key}'")

    role_revision = bootstrap_input.role_policy_lookup.get_role(compiled_node.role)
    if role_revision is None:
        raise missing_resource_error(f"missing role definition for '{compiled_node.role}'")

    policy_revision = None
    if compiled_node.policy is not None:
        policy_revision = bootstrap_input.role_policy_lookup.get_policy(compiled_node.policy)
        if policy_revision is None:
            raise missing_resource_error(f"missing policy definition for '{compiled_node.policy}'")

    return ResolvedNodeContext(
        node_key=compiled_node.node_key,
        node_kind=compiled_node.structural_kind,
        node_description=compiled_node.description,
        node_instruction=compiled_node.node_instruction,
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
    bootstrap_input: RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    criteria_paths: dict[str, Path],
    criteria_descriptions: dict[str, str],
) -> AssignmentProjection:
    if current_node.node_key != "root":
        raise illegal_state_error(
            "Automatic assignment generation only supports the launch/root path; "
            "later node assignments require explicit projected assignment input so "
            "runtime truth is not guessed early.",
            suggested_next_step=(
                "Provide an explicit projected assignment for non-root bootstrap inputs "
                "instead of asking launch projection to infer later-node runtime truth."
            ),
        )

    compiled_node = _compiled_nodes_by_key(bootstrap_input.compiled_plan)[current_node.node_key]
    if compiled_node.consumes is not None and compiled_node.consumes.artifacts:
        raise illegal_state_error(
            "Automatic assignment generation does not resolve artifact consumes; "
            "provide an explicit projected assignment instead.",
            suggested_next_step=(
                "Provide an explicit projected assignment when bootstrap inputs need "
                "artifact consumes resolved before launch."
            ),
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
            description=criteria_descriptions[selector.slot],
        )
        for selector in (compiled_node.consumes.criteria if compiled_node.consumes else ())
    )
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
    if current_node.node_instruction is not None:
        instruction_parts.append(f"Node instruction: {current_node.node_instruction}")
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
        consumes=(),
        produces=produces,
    )


def _criteria_paths(
    bootstrap_input: RuntimeBootstrapProjectionInput,
    *,
    task_root_paths: TaskRootPaths,
) -> dict[str, Path]:
    return {
        criteria.slot: criteria_file_path(paths=task_root_paths, slot=criteria.slot, version=1)
        for node in bootstrap_input.compiled_plan.nodes
        for criteria in node.criteria
    }


def _render_bootstrap_prompt(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    assignment: AssignmentProjection,
    manifest: ManifestProjection,
    latest_checkpoint: CheckpointProjection | None,
) -> tuple[RenderedPromptBundle, PromptTransportRequest]:
    prompt_bundle = render_prompt_bundle(
        PromptRenderRequest(
            prompt_family=prompt_family_for_node_kind(current_node.node_kind),
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
        instructions_text=prompt_bundle.instructions_text,
        input_text=prompt_bundle.input_text,
    )
    return prompt_bundle, transport_request


def _build_persisted_prompt_record(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    assignment: AssignmentProjection,
    prompt_bundle: RenderedPromptBundle,
    task_root_paths: TaskRootPaths,
    transport_request: PromptTransportRequest,
) -> PersistedPromptRecord:
    return PersistedPromptRecord(
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
