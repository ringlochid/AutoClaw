from __future__ import annotations

from collections.abc import Iterable

from app.runtime.contracts import (
    AssignmentConsumeRef,
    AssignmentProjection,
    EvidenceKind,
    EvidenceRef,
    NodeKind,
    NodeRuntimeFileRef,
    PromptRenderRequest,
    PromptSendMode,
    RuntimeContextRef,
)

STATIC_SECTION_IDS = ("operating_model", "task_identity", "node_purpose")


def render_markdown_section(title: str, lines: Iterable[str]) -> str:
    collected = [line for line in lines if line]
    return f"## {title}\n" + "\n".join(collected)


def render_ref_without_path(ref: AssignmentConsumeRef) -> list[str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return [
            f"- kind: {ref.kind.value}",
            f"  description: {ref.description}",
        ]
    lines = [f"- kind: {ref.kind.value}"]
    if ref.slot is not None:
        lines.append(f"  slot: {ref.slot}")
    lines.append(f"  description: {ref.description}")
    return lines


def render_ref_with_path(ref: AssignmentConsumeRef) -> list[str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return render_node_runtime_ref(ref)
    lines = [f"- kind: {ref.kind.value}"]
    if ref.slot is not None:
        lines.append(f"  slot: {ref.slot}")
    if ref.version is not None:
        lines.append(f"  version: {ref.version}")
    lines.append(f"  path: {ref.path}")
    lines.append(f"  description: {ref.description}")
    return lines


def render_node_runtime_ref(ref: NodeRuntimeFileRef) -> list[str]:
    return [
        f"- kind: {ref.kind.value}",
        f"  path: {ref.path}",
        f"  description: {ref.description}",
    ]


def _render_operating_model() -> str:
    return render_markdown_section(
        "Operating Model",
        (
            "- controller/DB state owns runtime truth",
            "- generated files are shared projections derived from that truth",
            "- `dispatch` is ingress, `record_checkpoint` is durable publication, "
            "and `yield | green | retry | blocked` are egress",
            "- semantic assignment handoff stays separate from exact runtime-resolved "
            "durable refs in `consumed_durable_refs`",
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
    return render_markdown_section("Task Identity", lines)


def _render_node_purpose(request: PromptRenderRequest) -> str:
    node = request.current_node
    return render_markdown_section(
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
    if request.send_mode == PromptSendMode.SAME_SESSION_CONTINUE:
        bound_turn = f"same-attempt {node_kind.value} continuation (internal dispatch id hidden)"
    else:
        bound_turn = f"current {node_kind.value} turn (internal dispatch id hidden)"
    if node_kind == NodeKind.WORKER:
        closure = "call `record_checkpoint`, then emit `green | retry | blocked`"
    else:
        closure = (
            "use control tools now, call `record_checkpoint` if the reasoning must persist, "
            "then later emit `yield` or a terminal boundary"
        )
    return render_markdown_section(
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
    return render_markdown_section("Workflow Manifest", lines)


def _render_current_assignment(request: PromptRenderRequest) -> str:
    assignment = request.assignment
    lines = [
        f"- path: {request.manifest.current_context.active_assignment_path}",
        f"- summary: {assignment.summary}",
    ]
    if assignment.instruction is not None:
        lines.append(f"- instruction: {assignment.instruction}")
    if assignment.criteria:
        lines.append("- criteria:")
        for criteria_ref in assignment.criteria:
            lines.extend(f"  {line}" for line in render_ref_without_path(criteria_ref))
    if assignment.consumes:
        lines.append("- consumes:")
        for consume_ref in assignment.consumes:
            lines.extend(f"  {line}" for line in render_ref_without_path(consume_ref))
    if assignment.produces:
        lines.append("- produces:")
        for requirement in assignment.produces:
            lines.append(f"  - slot: {requirement.slot}")
            lines.append(f"    description: {requirement.description}")
    if assignment.transient_refs:
        lines.append("- transient_refs:")
        for ref in assignment.transient_refs:
            lines.append(f"  - path: {ref.path}")
            lines.append(f"    description: {ref.description}")
    if assignment.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        for hint in assignment.task_memory_search_hints:
            lines.append(f"  - {hint}")
    return render_markdown_section("Current Assignment", lines)


def _render_latest_checkpoint_context(request: PromptRenderRequest) -> str:
    checkpoint = request.latest_checkpoint
    checkpoint_path = (
        request.manifest.current_context.latest_relevant_checkpoint_path
        or request.manifest.current_context.latest_checkpoint_path
    )
    if checkpoint is None:
        return render_markdown_section(
            "Latest Checkpoint Context",
            (
                "- path: null",
                "- no current relevant checkpoint is surfaced",
            ),
        )
    lines = [
        (f"- path: {checkpoint_path}" if checkpoint_path is not None else "- path: null"),
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
            lines.append(f"  - path: {ref.path}")
            lines.append(f"    description: {ref.description}")
    if checkpoint.task_memory_search_hints:
        lines.append("- task_memory_search_hints:")
        lines.extend(f"  - {hint}" for hint in checkpoint.task_memory_search_hints)
    return render_markdown_section("Latest Checkpoint Context", lines)


def _durable_ref_key(ref: RuntimeContextRef) -> tuple[str, str | None, int | None, str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return (ref.kind.value, None, None, str(ref.path))
    return (ref.kind.value, ref.slot, ref.version, str(ref.path))


def _turn_surfaced_durable_refs(request: PromptRenderRequest) -> tuple[RuntimeContextRef, ...]:
    checkpoint_context_path = (
        request.manifest.current_context.latest_relevant_checkpoint_path
        or request.manifest.current_context.latest_checkpoint_path
    )
    durable_refs: list[RuntimeContextRef] = []
    seen: set[tuple[str, str | None, int | None, str]] = set()
    for ref in request.manifest.current_context.current_relevant_paths:
        if isinstance(ref, EvidenceRef) and ref.kind == EvidenceKind.TRANSIENT:
            continue
        if (
            checkpoint_context_path is not None
            and isinstance(ref, NodeRuntimeFileRef)
            and ref.path == checkpoint_context_path
        ):
            continue
        key = _durable_ref_key(ref)
        if key in seen:
            continue
        seen.add(key)
        durable_refs.append(ref)
    if durable_refs:
        return tuple(durable_refs)
    return tuple((*request.assignment.criteria, *request.assignment.consumes))


def _render_consumed_durable_refs(request: PromptRenderRequest) -> str | None:
    durable_refs = _turn_surfaced_durable_refs(request)
    if not durable_refs:
        return None
    lines: list[str] = []
    for ref in durable_refs:
        lines.extend(render_ref_with_path(ref))
    return render_markdown_section("Consumed Durable Refs", lines)


def _render_transient_refs(assignment: AssignmentProjection) -> str | None:
    if not assignment.transient_refs:
        return None
    lines = ["- transient refs are optional carryover only; they are not durable truth"]
    for ref in assignment.transient_refs:
        lines.append(f"- path: {ref.path}")
        lines.append(f"  description: {ref.description}")
    return render_markdown_section("Transient Refs", lines)


def _unique_task_memory_hints(request: PromptRenderRequest) -> tuple[str, ...]:
    hints: list[str] = []
    seen: set[str] = set()
    for hint in request.assignment.task_memory_search_hints:
        if hint in seen:
            continue
        seen.add(hint)
        hints.append(hint)
    if request.latest_checkpoint is not None:
        for hint in request.latest_checkpoint.task_memory_search_hints:
            if hint in seen:
                continue
            seen.add(hint)
            hints.append(hint)
    return tuple(hints)


def _task_memory_context_refs(request: PromptRenderRequest) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []
    seen: set[tuple[str, str | None, str]] = set()
    for ref in request.manifest.current_context.current_relevant_paths:
        if not isinstance(ref, EvidenceRef):
            continue
        if ref.kind not in {EvidenceKind.WIKI, EvidenceKind.DOC}:
            continue
        key = (ref.kind.value, ref.slot, str(ref.path))
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref)
    return tuple(refs)


def _render_task_memory(request: PromptRenderRequest) -> str | None:
    hints = _unique_task_memory_hints(request)
    context_refs = _task_memory_context_refs(request)
    if not hints and not context_refs:
        return None
    lines: list[str] = []
    if hints:
        lines.append("- search hints:")
        lines.extend(f"  - {hint}" for hint in hints)
    if context_refs:
        lines.append("- surfaced curated refs:")
        for ref in context_refs:
            lines.extend(f"  {line}" for line in render_ref_with_path(ref))
    lines.append("- `context/wiki/` contains curated task-memory pages")
    lines.append("- other curated docs under `context/` are source/reference material")
    lines.append("- direct file/path search is the v1 retrieval model")
    return render_markdown_section("Task Memory", lines)


def _render_allowed_actions_now(request: PromptRenderRequest) -> str:
    node_kind = request.current_node.node_kind
    lines: list[str] = []
    if node_kind == NodeKind.WORKER:
        lines.extend(
            (
                "- call `record_checkpoint` with a progress checkpoint if later readers "
                "need intermediate reasoning before terminal closure",
                "- before `green`, `retry`, or `blocked`, call `record_checkpoint` "
                "with the terminal handoff for this attempt",
                "- close with `green`, `retry`, or `blocked` only when justified by "
                "the current assignment and its current surfaced evidence",
                "- do not use parent/root control tools from this dispatch",
                "- callback remains a write-only semantic lane and not a context-discovery helper",
            )
        )
    else:
        lines.extend(
            (
                "- tools: `assign_child`, `add_child`, `update_child`, `remove_child`, "
                "`release_green`, `release_blocked`, `record_checkpoint`",
                "- use `assign_child` with semantic `assignment_intent`, "
                "`supplemental_durable_context`, and explicit `transient_surfaces` only; "
                "do not author final durable ref metadata for the child",
                "- for structural edits, reread the current manifest first, discover "
                "valid role/policy ids through the registry read lane, and reread the "
                "regenerated manifest after the edit before deciding whether one child "
                "assignment should be staged",
                "- if exactly one child assignment is staged and the dispatch stays "
                "non-terminal, emit `yield`",
                "- if later readers must understand why that child was staged or why "
                "release is not yet legal, call `record_checkpoint` before `yield` or "
                "terminal closure",
                "- `release_green` and root `release_blocked` are terminal "
                "preconditions, not `yield` basis",
                f"- emit `green | blocked` only when this {node_kind.value} node is "
                "closing its own current assignment",
            )
        )
    return render_markdown_section("Allowed Actions Now", lines)


def _render_publication_rule() -> str:
    return render_markdown_section(
        "Publication Rule",
        (
            "- `produces` are requirements that gate successful completion",
            "- runtime authors final durable publication metadata after required outputs exist",
            "- later agents learn what happened from checkpoints plus surfaced refs, "
            "not hidden transcript memory",
            "- ordinary prompt surfaces keep artifact refs compact and path-only",
        ),
    )


def render_prompt_sections(request: PromptRenderRequest) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [
        ("operating_model", _render_operating_model()),
        ("task_identity", _render_task_identity(request)),
        ("node_purpose", _render_node_purpose(request)),
        ("current_dispatch", _render_current_dispatch(request)),
        ("workflow_manifest", _render_workflow_manifest(request)),
        ("current_assignment", _render_current_assignment(request)),
        ("latest_checkpoint_context", _render_latest_checkpoint_context(request)),
    ]
    consumed_durable_refs = _render_consumed_durable_refs(request)
    if consumed_durable_refs is not None:
        sections.append(("consumed_durable_refs", consumed_durable_refs))
    transient_refs = _render_transient_refs(request.assignment)
    if transient_refs is not None:
        sections.append(("transient_refs", transient_refs))
    task_memory = _render_task_memory(request)
    if task_memory is not None:
        sections.append(("task_memory", task_memory))
    sections.append(("allowed_actions_now", _render_allowed_actions_now(request)))
    sections.append(("publication_rule", _render_publication_rule()))
    return sections
