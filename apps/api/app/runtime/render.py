from __future__ import annotations

import hashlib
from collections.abc import Iterable

from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    EvidenceRef,
    ManifestDependencyProjection,
    ManifestNodeProjection,
    ManifestProjection,
    NodeKind,
    NodeRuntimeFileRef,
    PromptRenderRequest,
    PromptSendMode,
    RenderedPromptBundle,
)


def _content_hash(markdown: str) -> str:
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _section(title: str, lines: Iterable[str]) -> str:
    collected = [line for line in lines if line]
    return f"## {title}\n" + "\n".join(collected)


def _render_ref_without_path(ref: EvidenceRef) -> list[str]:
    lines = [f"- kind: {ref.kind.value}"]
    if ref.slot is not None:
        lines.append(f"  - slot: {ref.slot}")
    lines.append(f"  - description: {ref.description}")
    return lines


def _render_ref_with_path(ref: EvidenceRef) -> list[str]:
    lines = [f"- kind: {ref.kind.value}"]
    if ref.slot is not None:
        lines.append(f"  - slot: {ref.slot}")
    if ref.version is not None:
        lines.append(f"  - version: {ref.version}")
    lines.append(f"  - path: {ref.path}")
    lines.append(f"  - description: {ref.description}")
    return lines


def _render_node_runtime_ref(ref: NodeRuntimeFileRef) -> list[str]:
    return [
        f"- kind: {ref.kind.value}",
        f"  - path: {ref.path}",
        f"  - description: {ref.description}",
    ]


def _render_operating_model() -> str:
    return _section(
        "Operating Model",
        (
            "- controller/DB state owns runtime truth",
            "- generated files are shared projections derived from that truth",
            "- `dispatch` is ingress and `yield | green | retry | blocked` are the "
            "only egress boundaries",
            "- `record_checkpoint` is the durable publication lane for what happened "
            "and what should happen next",
            "- `workspace/` is mutable work and `_runtime/dispatch/` monitoring files "
            "are observability-only projections",
        ),
    )


def _render_task_identity(request: PromptRenderRequest) -> str:
    task = request.manifest.task
    lines = [
        f"- task key: {task.task_key}",
        f"- title: {task.title}",
        f"- summary: {task.summary}",
    ]
    if task.instruction is not None:
        lines.append(f"- task instruction: {task.instruction}")
    return _section("Task Identity", lines)


def _render_node_purpose(request: PromptRenderRequest) -> str:
    node = request.current_node
    return _section(
        "Node Purpose",
        (
            f"- node key: {node.node_key}",
            f"- node kind: {node.node_kind.value}",
            f"- role: {node.role_key}",
            f"- description: {node.node_description}",
        ),
    )


def _render_current_dispatch(request: PromptRenderRequest) -> str:
    node_kind = request.current_node.node_kind
    if node_kind == NodeKind.WORKER:
        closure = "publish a checkpoint and then close with `green`, `retry`, or `blocked`"
        bound_turn = "current worker turn (internal dispatch id hidden)"
    else:
        closure = "use control tools now and later close with `yield`, `green`, or `blocked`"
        bound_turn = "current parent/root turn (internal dispatch id hidden)"
    return _section(
        "Current Dispatch",
        (
            f"- current bound turn: {bound_turn}",
            f"- send mode: {request.send_mode.value}",
            f"- closure expectation: {closure}",
        ),
    )


def _render_workflow_manifest(request: PromptRenderRequest) -> str:
    context = request.manifest.current_context
    lines = [
        f"- path: {request.manifest.filesystem_roots.runtime_path / 'workflow-manifest.md'}",
        "- description: whole-workflow visible contract for the current task",
        f"- current node anchor: {context.current_node_key}",
    ]
    for ref in context.current_relevant_paths:
        if isinstance(ref, EvidenceRef):
            lines.append(f"- surfaced path: {ref.path}")
        else:
            lines.append(f"- surfaced runtime file: {ref.path}")
    return _section("Workflow Manifest", lines)


def _render_current_assignment(assignment: AssignmentProjection) -> str:
    lines = [f"- summary: {assignment.summary}"]
    if assignment.instruction is not None:
        lines.append(f"- instruction: {assignment.instruction}")
    if assignment.criteria:
        lines.append("- criteria:")
        for ref in assignment.criteria:
            lines.extend(f"  {line}" for line in _render_ref_without_path(ref))
    if assignment.consumes:
        lines.append("- consumes:")
        for ref in assignment.consumes:
            lines.extend(f"  {line}" for line in _render_ref_without_path(ref))
    if assignment.produces:
        lines.append("- produces:")
        for requirement in assignment.produces:
            lines.append(f"  - slot: {requirement.slot}")
            lines.append(f"    - description: {requirement.description}")
    if assignment.transient_refs:
        lines.append("- transient_refs:")
        for ref in assignment.transient_refs:
            lines.append(f"  - path: {ref.path}")
            lines.append(f"    - description: {ref.description}")
    if assignment.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        for hint in assignment.task_memory_search_hints:
            lines.append(f"  - {hint}")
    return _section("Current Assignment", lines)


def _render_latest_checkpoint(checkpoint: CheckpointProjection) -> str:
    lines = [
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
            lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
    if checkpoint.transient_refs:
        lines.append("- transient_refs:")
        for ref in checkpoint.transient_refs:
            lines.append(f"  - path: {ref.path}")
            lines.append(f"    - description: {ref.description}")
    if checkpoint.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        lines.extend(f"  - {hint}" for hint in checkpoint.task_memory_search_hints)
    return _section("Latest Checkpoint Context", lines)


def _render_consumed_durable_refs(assignment: AssignmentProjection) -> str | None:
    durable_refs = [*assignment.criteria, *assignment.consumes]
    if not durable_refs:
        return None
    lines = []
    for ref in durable_refs:
        lines.extend(_render_ref_with_path(ref))
    return _section("Consumed Durable Refs", lines)


def _render_transient_refs(assignment: AssignmentProjection) -> str | None:
    if not assignment.transient_refs:
        return None
    lines = ["- transient refs are optional carryover only"]
    for ref in assignment.transient_refs:
        lines.append(f"- path: {ref.path}")
        lines.append(f"  - description: {ref.description}")
    return _section("Transient Refs", lines)


def _render_task_memory(assignment: AssignmentProjection) -> str | None:
    if not assignment.task_memory_search_hints:
        return None
    lines = ["- `context/wiki/` contains curated task-memory pages"]
    lines.append("- other curated docs under `context/` are source/reference material")
    lines.append("- direct file/path search is the v1 retrieval model")
    lines.append("- current search hints:")
    lines.extend(f"  - {hint}" for hint in assignment.task_memory_search_hints)
    return _section("Task Memory", lines)


def _render_allowed_actions(request: PromptRenderRequest) -> str:
    node_kind = request.current_node.node_kind
    lines: list[str] = []
    if node_kind == NodeKind.WORKER:
        lines.extend(
            (
                "- publish checkpoint state through `record_checkpoint` when the "
                "handoff must survive redispatch",
                "- close with `green`, `retry`, or `blocked` only when justified by "
                "the current assignment",
                "- callback remains a write-only semantic lane and not a context-discovery helper",
            )
        )
    else:
        lines.extend(
            (
                "- tools: `assign_child`, `add_child`, `update_child`, `remove_child`, "
                "`release_green`, `release_blocked`",
                "- reread the manifest before structural edits and reread the "
                "regenerated manifest after them",
                "- emit `yield` only after exactly one staged child assignment already exists",
                "- use `green` or `blocked` only for terminal parent/root closure when justified",
                "- use `record_checkpoint` when reasoning must survive redispatch",
            )
        )
    return _section("Allowed Actions Now", lines)


def _render_publication_rule() -> str:
    return _section(
        "Publication Rule",
        (
            "- `produces` are requirements that gate successful completion",
            "- runtime authors final durable publication metadata after required outputs exist",
            "- later agents learn what happened from checkpoints plus surfaced refs, "
            "not hidden transcript memory",
            "- ordinary prompt surfaces keep artifact refs compact and path-only",
        ),
    )


def _render_sections(request: PromptRenderRequest) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [
        ("operating_model", _render_operating_model()),
        ("task_identity", _render_task_identity(request)),
        ("node_purpose", _render_node_purpose(request)),
        ("current_dispatch", _render_current_dispatch(request)),
        ("workflow_manifest", _render_workflow_manifest(request)),
        ("current_assignment", _render_current_assignment(request.assignment)),
    ]
    if request.latest_checkpoint is not None:
        sections.append(
            ("latest_checkpoint_context", _render_latest_checkpoint(request.latest_checkpoint))
        )
    consumed_durable_refs = _render_consumed_durable_refs(request.assignment)
    if consumed_durable_refs is not None:
        sections.append(("consumed_durable_refs", consumed_durable_refs))
    transient_refs = _render_transient_refs(request.assignment)
    if transient_refs is not None:
        sections.append(("transient_refs", transient_refs))
    task_memory = _render_task_memory(request.assignment)
    if task_memory is not None:
        sections.append(("task_memory", task_memory))
    sections.append(("allowed_actions_now", _render_allowed_actions(request)))
    sections.append(("publication_rule", _render_publication_rule()))
    return sections


def _render_instructions(request: PromptRenderRequest) -> str:
    node = request.current_node
    lines = [
        "You are AutoClaw inside a controller-first runtime.",
        "Controller and database truth win over generated projections.",
        "`dispatch` is ingress and `record_checkpoint` plus the boundary outcomes "
        "are the semantic write surfaces.",
        "Read the workflow manifest, current assignment, latest checkpoint, and "
        "surfaced refs in that order before acting.",
        f"Current node kind: {node.node_kind.value}",
        f"Role: {node.role_key}",
        f"Role description: {node.role_description}",
    ]
    if node.role_instruction is not None:
        lines.append(f"Role instruction: {node.role_instruction}")
    if node.policy_key is not None and node.policy_description is not None:
        lines.append(f"Policy: {node.policy_key}")
        lines.append(f"Policy description: {node.policy_description}")
    if node.policy_instruction is not None:
        lines.append(f"Policy instruction: {node.policy_instruction}")
    return "\n".join(lines)


def render_prompt_bundle(request: PromptRenderRequest) -> RenderedPromptBundle:
    sections = _render_sections(request)
    full_markdown = "\n\n".join(section for _section_id, section in sections)
    if request.send_mode == PromptSendMode.SAME_SESSION_CONTINUE:
        static_sections = {"operating_model", "task_identity", "node_purpose"}
        input_markdown = "\n\n".join(
            section for section_id, section in sections if section_id not in static_sections
        )
    else:
        input_markdown = full_markdown
    return RenderedPromptBundle(
        prompt_family=request.prompt_family,
        send_mode=request.send_mode,
        instructions_text=_render_instructions(request),
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
    if manifest.current_context.latest_checkpoint_path is not None:
        lines.append(f"- latest_checkpoint_path: {manifest.current_context.latest_checkpoint_path}")
    if manifest.current_context.current_relevant_paths:
        lines.append("- current_relevant_paths:")
        for ref in manifest.current_context.current_relevant_paths:
            if isinstance(ref, EvidenceRef):
                lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
            else:
                lines.extend(f"  {line}" for line in _render_node_runtime_ref(ref))

    lines.extend(("", "## Node Tree"))
    for node in manifest.node_tree:
        lines.extend(_render_manifest_node(node))

    lines.extend(("", "## Dependency Index"))
    for dependency in manifest.dependency_index:
        lines.extend(_render_manifest_dependency(dependency))
    return "\n".join(lines).rstrip() + "\n"


def _render_manifest_node(node: ManifestNodeProjection) -> list[str]:
    lines = [
        f"- node_key: {node.node_key}",
        f"  - node_kind: {node.node_kind.value}",
        f"  - role: {node.role}",
        f"  - description: {node.description}",
    ]
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
        for ref in assignment.criteria:
            lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
    if assignment.consumes:
        lines.append("- consumes:")
        for ref in assignment.consumes:
            lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
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
            lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
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
            lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
    if checkpoint.transient_refs:
        lines.append("- transient_refs:")
        for ref in checkpoint.transient_refs:
            lines.extend(f"  {line}" for line in _render_ref_with_path(ref))
    if checkpoint.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        lines.extend(f"  - {hint}" for hint in checkpoint.task_memory_search_hints)
    return "\n".join(lines).rstrip() + "\n"
