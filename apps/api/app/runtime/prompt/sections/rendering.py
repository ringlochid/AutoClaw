from __future__ import annotations

from app.runtime.contracts import (
    EvidenceRef,
    NodeKind,
    PromptRenderRequest,
)
from app.runtime.prompt.sections.context import (
    render_consumed_durable_refs,
    render_latest_checkpoint_context,
    render_task_memory,
    render_transient_refs,
)
from app.runtime.prompt.sections.primitives import (
    render_markdown_section,
    render_ref_without_path,
)
from app.runtime.prompt.structural_edit_palette import (
    parent_root_structural_edit_palette,
    structural_edit_palette_lines,
)

NODE_TOOL_PREFIX = "autoclaw-node__"
CURRENT_ONLY_DEFINITION_LOOKUP_GUIDANCE = (
    "if the surfaced structural edit palette is still insufficient after reread, "
    f"use the current-only `{NODE_TOOL_PREFIX}search_definitions` / "
    f"`{NODE_TOOL_PREFIX}get_definition` read-only lookup lane before guessing"
)
DEFINITION_REVISION_HISTORY_EXCLUSION_GUIDANCE = (
    "do not use definition revision history as dispatched planning input"
)


def render_prompt_sections(request: PromptRenderRequest) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [
        ("operating_model", render_operating_model()),
        ("task_identity", render_task_identity(request)),
        ("node_purpose", render_node_purpose(request)),
        ("current_dispatch", render_current_dispatch(request)),
        ("workflow_manifest", render_workflow_manifest(request)),
        ("current_assignment", render_current_assignment(request)),
        ("latest_checkpoint_context", render_latest_checkpoint_context(request)),
    ]
    consumed_durable_refs = render_consumed_durable_refs(request)
    if consumed_durable_refs is not None:
        sections.append(("consumed_durable_refs", consumed_durable_refs))
    transient_refs = render_transient_refs(request.assignment)
    if transient_refs is not None:
        sections.append(("transient_refs", transient_refs))
    task_memory = render_task_memory(request)
    if task_memory is not None:
        sections.append(("task_memory", task_memory))
    sections.append(("allowed_actions_now", render_allowed_actions_now(request)))
    sections.append(("publication_rule", render_publication_rule()))
    return sections


def render_operating_model() -> str:
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


def render_task_identity(request: PromptRenderRequest) -> str:
    task = request.manifest.task
    lines = [
        f"- task key: {task.task_key}",
        f"- title: {task.title}",
        f"- summary: {task.summary}",
    ]
    if task.instruction is not None:
        lines.append(f"- task instruction: {task.instruction}")
    return render_markdown_section("Task Identity", lines)


def render_node_purpose(request: PromptRenderRequest) -> str:
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


def render_current_dispatch(request: PromptRenderRequest) -> str:
    node_kind = request.current_node.node_kind
    bound_turn = f"current {node_kind.value} turn (internal dispatch id hidden)"
    if node_kind == NodeKind.WORKER:
        closure = f"call `{_node_tool('record_checkpoint')}`, then emit `green | retry | blocked`"
    else:
        closure = (
            f"use control tools now, call `{_node_tool('record_checkpoint')}` if the "
            "reasoning must persist, then later emit `yield` or a terminal boundary"
        )
    session_key = request.session_key or "unavailable until the live node session is opened"
    return render_markdown_section(
        "Current Dispatch",
        (
            f"- current bound turn: {bound_turn}",
            f"- node kind: {node_kind.value}",
            f"- send mode: {request.send_mode.value}",
            f"- closure expectation: {closure}",
            f"- task_id for node tools: {request.task_id}",
            f"- session_key for node tools: {session_key}",
            f"- model-visible node tool ids use the `{NODE_TOOL_PREFIX}*` prefix; use the "
            "exact prefixed tool ids surfaced below when calling node tools.",
            "- When calling node tools, include the exact `task_id` and `session_key` shown "
            "here. Do not print them in normal output, checkpoint prose, or artifacts.",
        ),
    )


def render_workflow_manifest(request: PromptRenderRequest) -> str:
    context = request.manifest.current_context
    lines = [
        f"- path: {request.manifest.filesystem_roots.runtime_path / 'workflow-manifest.md'}",
        "- description: whole-workflow visible contract for the current task",
        f"- current node anchor: {context.current_node_key}",
    ]
    palette = parent_root_structural_edit_palette(
        node_kind=request.current_node.node_kind,
        palette=request.manifest.structural_edit_palette,
    )
    if palette is not None:
        lines.extend(structural_edit_palette_lines(palette))
    for ref in context.current_relevant_paths:
        if isinstance(ref, EvidenceRef):
            lines.append(f"- surfaced path: {ref.path}")
        else:
            lines.append(f"- surfaced runtime file: {ref.path}")
    return render_markdown_section("Workflow Manifest", lines)


def render_current_assignment(request: PromptRenderRequest) -> str:
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


def render_allowed_actions_now(request: PromptRenderRequest) -> str:
    node_kind = request.current_node.node_kind
    lines: list[str] = []
    if node_kind == NodeKind.WORKER:
        lines.extend(
            (
                f"- call `{_node_tool('record_checkpoint')}` with a progress checkpoint if "
                "later readers need intermediate reasoning before terminal closure",
                f"- before `green`, `retry`, or `blocked`, call "
                f"`{_node_tool('record_checkpoint')}` with the terminal handoff for this "
                "attempt",
                "- close with `green`, `retry`, or `blocked` only when justified by "
                "the current assignment and its current surfaced evidence",
                "- do not use parent/root control tools from this dispatch",
                "- callback remains a write-only semantic lane and not a context-discovery helper",
            )
        )
    else:
        tool_line = (
            f"- tools: `{_node_tool('assign_child')}`, `{_node_tool('add_child')}`, "
            f"`{_node_tool('update_child')}`, `{_node_tool('remove_child')}`, "
            f"`{_node_tool('release_green')}`, `{_node_tool('record_checkpoint')}`"
        )
        if node_kind == NodeKind.ROOT:
            tool_line = (
                f"- tools: `{_node_tool('assign_child')}`, `{_node_tool('add_child')}`, "
                f"`{_node_tool('update_child')}`, `{_node_tool('remove_child')}`, "
                f"`{_node_tool('release_green')}`, `{_node_tool('release_blocked')}`, "
                f"`{_node_tool('record_checkpoint')}`"
            )
        blocked_fallback = (
            "a legal blocked path"
            if node_kind == NodeKind.ROOT
            else "a legal checkpoint or current-node boundary"
        )
        closure_line = (
            f"- emit `green` only when this {node_kind.value} node is closing its own "
            "current assignment"
        )
        if node_kind == NodeKind.ROOT:
            closure_line = (
                f"- emit `green` only when this {node_kind.value} node is closing its own "
                "current assignment; emit `blocked` only for root whole-flow terminal "
                "closure after committed `release_blocked`"
            )
        lines.extend(
            (
                tool_line,
                f"- use `{_node_tool('assign_child')}` with semantic `assignment_intent`, "
                "`supplemental_durable_context`, and explicit `transient_surfaces` only; "
                "do not author final durable ref metadata for the child",
                "- for structural edits, reread the current manifest first, start "
                "with role/policy names from the surfaced structural edit palette in "
                "this prompt or manifest, and reread the regenerated manifest after "
                "the edit before deciding whether one child assignment should be staged",
                f"- {CURRENT_ONLY_DEFINITION_LOOKUP_GUIDANCE}",
                "- if the needed role/policy name is still not surfaced after "
                "palette reread and current-only lookup, do not guess it; "
                f"checkpoint the gap or choose {blocked_fallback}",
                f"- {DEFINITION_REVISION_HISTORY_EXCLUSION_GUIDANCE}",
                "- if exactly one child assignment is staged and the dispatch stays "
                "non-terminal, emit `yield`",
                "- if later readers must understand why that child was staged or why "
                f"release is not yet legal, call `{_node_tool('record_checkpoint')}` "
                "before `yield` or terminal closure",
                f"- `{_node_tool('release_green')}` and root "
                f"`{_node_tool('release_blocked')}` are terminal preconditions, not `yield` "
                "basis",
                closure_line,
            )
        )
    return render_markdown_section("Allowed Actions Now", lines)


def render_publication_rule() -> str:
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


def _node_tool(tool_name: str) -> str:
    return f"{NODE_TOOL_PREFIX}{tool_name}"
