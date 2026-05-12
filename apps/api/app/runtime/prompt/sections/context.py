from __future__ import annotations

from pathlib import Path

from app.runtime.contracts import (
    AssignmentProjection,
    EvidenceKind,
    EvidenceRef,
    NodeRuntimeFileRef,
    PromptFamily,
    PromptRenderRequest,
    RuntimeContextRef,
)
from app.runtime.prompt.sections.primitives import (
    render_markdown_section,
    render_ref_with_path,
)


def latest_checkpoint_context_path(request: PromptRenderRequest) -> Path | None:
    return (
        request.manifest.current_context.latest_relevant_checkpoint_path
        or request.manifest.current_context.latest_checkpoint_path
    )


def render_latest_checkpoint_context(request: PromptRenderRequest) -> str:
    checkpoint = request.latest_checkpoint
    checkpoint_path = latest_checkpoint_context_path(request)
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


def render_consumed_durable_refs(request: PromptRenderRequest) -> str | None:
    durable_refs = consumed_durable_refs_for_turn(request)
    if not durable_refs:
        if request.prompt_family == PromptFamily.WORKER_DISPATCH:
            return render_markdown_section(
                "Consumed Durable Refs",
                ("- no current durable refs are surfaced for this turn",),
            )
        return None
    lines: list[str] = []
    for ref in durable_refs:
        lines.extend(render_ref_with_path(ref))
    return render_markdown_section("Consumed Durable Refs", lines)


def render_transient_refs(assignment: AssignmentProjection) -> str | None:
    if not assignment.transient_refs:
        return None
    lines = ["- transient refs are optional carryover only; they are not durable truth"]
    for ref in assignment.transient_refs:
        lines.append(f"- path: {ref.path}")
        lines.append(f"  description: {ref.description}")
    return render_markdown_section("Transient Refs", lines)


def render_task_memory(request: PromptRenderRequest) -> str | None:
    hints = unique_task_memory_hints(request)
    context_refs = task_memory_context_refs(request)
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


def consumed_durable_refs_for_turn(
    request: PromptRenderRequest,
) -> tuple[RuntimeContextRef, ...]:
    checkpoint_context_path = latest_checkpoint_context_path(request)
    durable_refs: list[RuntimeContextRef] = []
    seen: set[tuple[str, str | None, int | None, str]] = set()
    for ref in consumed_durable_ref_candidates(request):
        if is_transient_runtime_context_ref(ref):
            continue
        if is_rendered_checkpoint_context_ref(ref, checkpoint_context_path):
            continue
        key = durable_ref_key(ref)
        if key in seen:
            continue
        seen.add(key)
        durable_refs.append(ref)
    return tuple(durable_refs)


def consumed_durable_ref_candidates(
    request: PromptRenderRequest,
) -> tuple[RuntimeContextRef, ...]:
    return (
        *request.assignment.criteria,
        *request.assignment.consumes,
        *request.manifest.current_context.current_relevant_paths,
    )


def durable_ref_key(ref: RuntimeContextRef) -> tuple[str, str | None, int | None, str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return (ref.kind.value, None, None, str(ref.path))
    return (ref.kind.value, ref.slot, ref.version, str(ref.path))


def is_rendered_checkpoint_context_ref(
    ref: RuntimeContextRef,
    checkpoint_context_path: Path | None,
) -> bool:
    return (
        checkpoint_context_path is not None
        and isinstance(ref, NodeRuntimeFileRef)
        and ref.path == checkpoint_context_path
    )


def is_transient_runtime_context_ref(ref: RuntimeContextRef) -> bool:
    return isinstance(ref, EvidenceRef) and ref.kind == EvidenceKind.TRANSIENT


def task_memory_context_refs(request: PromptRenderRequest) -> tuple[EvidenceRef, ...]:
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


def unique_task_memory_hints(request: PromptRenderRequest) -> tuple[str, ...]:
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
