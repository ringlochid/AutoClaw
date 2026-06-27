from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from autoclaw.definitions.compiler import NormalizedCompiledNode, NormalizedCompiledPlan
from autoclaw.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    EvidenceKind,
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
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    ResolvedNodeContext,
    RuntimeBootstrapProjectionInput,
    RuntimeContextRef,
    TaskRootPaths,
)
from autoclaw.runtime.projection.manifest.structural_palette import (
    structural_edit_palette_from_lookup,
)
from autoclaw.runtime.task_root import assignment_markdown_path, checkpoint_markdown_path


def build_manifest_projection(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    criteria_paths: dict[str, Path],
    criteria_descriptions: dict[str, str],
    assignment: AssignmentProjection,
    latest_checkpoint: CheckpointProjection | None,
    task_root_paths: TaskRootPaths,
) -> ManifestProjection:
    compiled_plan = bootstrap_input.compiled_plan
    depends_on, depended_on_by, dependency_descriptions = _dependency_maps(compiled_plan)
    node_tree = tuple(
        _build_manifest_node_projection(
            compiled_node=compiled_node,
            criteria_paths=criteria_paths,
            depends_on=depends_on,
            depended_on_by=depended_on_by,
            dependency_descriptions=dependency_descriptions,
            criteria_descriptions=criteria_descriptions,
        )
        for compiled_node in compiled_plan.nodes
    )
    task = bootstrap_input.task_compose.task
    return ManifestProjection(
        active_flow_revision_id=bootstrap_input.active_flow_revision_id,
        generated_at=datetime.now(tz=UTC),
        task=ManifestTaskProjection(
            task_id=bootstrap_input.task_id,
            task_key=task.key,
            title=task.title,
            summary=task.summary,
            instruction=task.instruction,
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
        structural_edit_palette=bootstrap_input.structural_edit_palette
        or structural_edit_palette_from_lookup(bootstrap_input.role_policy_lookup),
        current_context=_build_manifest_current_context(
            bootstrap_input=bootstrap_input,
            current_node=current_node,
            assignment=assignment,
            latest_checkpoint=latest_checkpoint,
            task_root_paths=task_root_paths,
        ),
        node_tree=node_tree,
        dependency_index=_build_dependency_index(compiled_plan),
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
        policy=compiled_node.policy,
        description=compiled_node.description,
        node_instruction=compiled_node.node_instruction,
        consumes=tuple(consumes),
        produces=produces,
        criteria=criteria,
        depends_on_node_keys=tuple(sorted(depends_on.get(compiled_node.node_key, set()))),
        depended_on_by_node_keys=tuple(sorted(depended_on_by.get(compiled_node.node_key, set()))),
    )


def _build_dependency_index(
    compiled_plan: NormalizedCompiledPlan,
) -> tuple[ManifestDependencyProjection, ...]:
    return tuple(
        ManifestDependencyProjection(
            provider_node_key=edge.provider_node_key,
            consumer_node_key=edge.consumer_node_key,
            kind=edge.kind.value,
            slot=edge.slot,
            description=edge.description,
        )
        for edge in compiled_plan.dependency_edges
    )


def _build_manifest_current_context(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    current_node: ResolvedNodeContext,
    assignment: AssignmentProjection,
    latest_checkpoint: CheckpointProjection | None,
    task_root_paths: TaskRootPaths,
) -> ManifestCurrentContextProjection:
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

    return ManifestCurrentContextProjection(
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
    )
