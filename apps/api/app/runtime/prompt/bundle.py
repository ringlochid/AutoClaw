from __future__ import annotations

import hashlib

from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    ManifestDependencyProjection,
    ManifestNodeProjection,
    ManifestProjection,
    PromptRenderRequest,
    RenderedPromptBundle,
)
from app.runtime.prompt.instructions import render_prompt_instructions
from app.runtime.prompt.sections import render_prompt_sections, render_ref_with_path
from app.runtime.prompt.structural_edit_palette import structural_edit_palette_lines


def render_prompt_bundle(request: PromptRenderRequest) -> RenderedPromptBundle:
    sections = render_prompt_sections(request)
    full_markdown = "\n\n".join(section for _section_id, section in sections)
    input_markdown = full_markdown
    instructions_text = render_prompt_instructions(request)
    return RenderedPromptBundle(
        prompt_family=request.prompt_family,
        send_mode=request.send_mode,
        instructions_text=instructions_text,
        input_text=input_markdown,
        full_markdown=full_markdown,
        content_hash=_content_hash(full_markdown),
    )


def render_manifest_markdown(manifest: ManifestProjection) -> str:
    lines = [
        "# Workflow Manifest",
        "",
        f"- manifest_version: {manifest.manifest_version}",
        f"- active_flow_revision_id: {manifest.active_flow_revision_id}",
        f"- generated_at: {manifest.generated_at.isoformat()}",
        "",
        "## Task",
        f"- task_id: {manifest.task.task_id}",
        f"- task_key: {manifest.task.task_key}",
        f"- title: {manifest.task.title}",
        f"- summary: {manifest.task.summary}",
    ]
    if manifest.task.instruction is not None:
        lines.append(f"- instruction: {manifest.task.instruction}")
    lines.extend(
        (
            "",
            "## Workflow",
            f"- workflow_key: {manifest.workflow.workflow_key}",
            f"- description: {manifest.workflow.description}",
            "",
            "## Filesystem Roots",
            f"- workspace_path: {manifest.filesystem_roots.workspace_path}",
            f"- context_path: {manifest.filesystem_roots.context_path}",
            f"- outputs_path: {manifest.filesystem_roots.outputs_path}",
            f"- tmp_path: {manifest.filesystem_roots.tmp_path}",
            f"- runtime_path: {manifest.filesystem_roots.runtime_path}",
            "",
            "## Current Context",
            f"- current_node_key: {manifest.current_context.current_node_key}",
            f"- owner_node_key: {manifest.current_context.owner_node_key}",
            f"- active_attempt_id: {manifest.current_context.active_attempt_id}",
            f"- active_assignment_path: {manifest.current_context.active_assignment_path}",
        )
    )
    lines.append(
        f"- latest_checkpoint_path: {manifest.current_context.latest_checkpoint_path}"
        if manifest.current_context.latest_checkpoint_path is not None
        else "- latest_checkpoint_path: null"
    )
    lines.append(
        "- latest_relevant_checkpoint_path: "
        f"{manifest.current_context.latest_relevant_checkpoint_path}"
        if manifest.current_context.latest_relevant_checkpoint_path is not None
        else "- latest_relevant_checkpoint_path: null"
    )
    if manifest.current_context.current_relevant_paths:
        lines.append("- current_relevant_paths:")
        for ref in manifest.current_context.current_relevant_paths:
            lines.extend(f"  {line}" for line in render_ref_with_path(ref))

    if manifest.structural_edit_palette is not None:
        lines.extend(("", "## Structural Edit Palette"))
        lines.extend(structural_edit_palette_lines(manifest.structural_edit_palette))

    lines.extend(("", "## Node Tree"))
    for node in manifest.node_tree:
        lines.extend(_render_manifest_node(node))

    lines.extend(("", "## Dependency Index"))
    for dependency in manifest.dependency_index:
        lines.extend(_render_manifest_dependency(dependency))
    return "\n".join(lines).rstrip() + "\n"


def render_assignment_markdown(assignment: AssignmentProjection) -> str:
    lines = [
        "# Current Assignment",
        "",
        f"- assignment_key: {assignment.assignment_key}",
        f"- node_key: {assignment.node_key}",
        f"- summary: {assignment.summary}",
    ]
    if assignment.instruction is not None:
        lines.append(f"- instruction: {assignment.instruction}")
    if assignment.criteria:
        lines.append("- criteria:")
        for criteria_ref in assignment.criteria:
            lines.extend(f"  {line}" for line in render_ref_with_path(criteria_ref))
    if assignment.consumes:
        lines.append("- consumes:")
        for consume_ref in assignment.consumes:
            lines.extend(f"  {line}" for line in render_ref_with_path(consume_ref))
    if assignment.produces:
        lines.append("- produces:")
        for requirement in assignment.produces:
            lines.append(f"  - slot: {requirement.slot}")
            lines.append(f"    - description: {requirement.description}")
            if requirement.file_hint is not None:
                lines.append(f"    - file_hint: {requirement.file_hint}")
    if assignment.transient_refs:
        lines.append("- transient_refs:")
        for ref in assignment.transient_refs:
            lines.extend(f"  {line}" for line in render_ref_with_path(ref))
    if assignment.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        lines.extend(f"  - {hint}" for hint in assignment.task_memory_search_hints)
    return "\n".join(lines).rstrip() + "\n"


def render_checkpoint_markdown(checkpoint: CheckpointProjection) -> str:
    lines = [
        "# Latest Checkpoint",
        "",
        f"- checkpoint_kind: {checkpoint.checkpoint_kind.value}",
        f"- outcome: {checkpoint.outcome.value if checkpoint.outcome is not None else 'null'}",
        f"- summary: {checkpoint.handoff.summary}",
        f"- next_step: {checkpoint.handoff.next_step}",
    ]
    if checkpoint.handoff.blockers:
        lines.append("- blockers:")
        lines.extend(f"  - {blocker}" for blocker in checkpoint.handoff.blockers)
    if checkpoint.handoff.risks:
        lines.append("- risks:")
        lines.extend(f"  - {risk}" for risk in checkpoint.handoff.risks)
    if checkpoint.produced_artifacts:
        lines.append("- produced_artifacts:")
        for ref in checkpoint.produced_artifacts:
            lines.extend(f"  {line}" for line in render_ref_with_path(ref))
    if checkpoint.transient_refs:
        lines.append("- transient_refs:")
        for ref in checkpoint.transient_refs:
            lines.extend(f"  {line}" for line in render_ref_with_path(ref))
    if checkpoint.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        lines.extend(f"  - {hint}" for hint in checkpoint.task_memory_search_hints)
    return "\n".join(lines).rstrip() + "\n"


def _content_hash(markdown: str) -> str:
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _render_manifest_node(node: ManifestNodeProjection) -> list[str]:
    lines = [
        f"- node_key: {node.node_key}",
        f"  - node_kind: {node.node_kind.value}",
        f"  - role: {node.role}",
        f"  - description: {node.description}",
    ]
    if node.policy is not None:
        lines.append(f"  - policy: {node.policy}")
    if node.parent_node_key is not None:
        lines.append(f"  - parent_node_key: {node.parent_node_key}")
    if node.child_node_keys:
        lines.append(f"  - child_node_keys: {', '.join(node.child_node_keys)}")
    if node.consumes:
        lines.append("  - consumes:")
        for consume in node.consumes:
            lines.append(f"    - kind: {consume.kind.value}")
            lines.append(f"      - slot: {consume.slot}")
            lines.append(f"      - description: {consume.description}")
    if node.produces:
        lines.append("  - produces:")
        for produce in node.produces:
            lines.append(f"    - slot: {produce.slot}")
            lines.append(f"      - description: {produce.description}")
    if node.criteria:
        lines.append("  - criteria:")
        for criteria in node.criteria:
            lines.append(f"    - slot: {criteria.slot}")
            lines.append(f"      - owner_node_key: {criteria.owner_node_key}")
            lines.append(f"      - description: {criteria.description}")
            lines.append(f"      - path: {criteria.path}")
    if node.depends_on_node_keys:
        lines.append(f"  - depends_on_node_keys: {', '.join(node.depends_on_node_keys)}")
    if node.depended_on_by_node_keys:
        lines.append(f"  - depended_on_by_node_keys: {', '.join(node.depended_on_by_node_keys)}")
    return lines


def _render_manifest_dependency(dependency: ManifestDependencyProjection) -> list[str]:
    return [
        f"- provider_node_key: {dependency.provider_node_key}",
        f"  - consumer_node_key: {dependency.consumer_node_key}",
        f"  - kind: {dependency.kind}",
        f"  - slot: {dependency.slot}",
        f"  - description: {dependency.description}",
    ]
