from __future__ import annotations

from pathlib import Path

from autoclaw.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    EvidenceKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    PromptSendMode,
)
from autoclaw.runtime.prompt import render_prompt_bundle

from .support import (
    extract_section,
    worker_request,
)


def test_task_memory_renders_only_surfaced_curated_refs(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    task_memory_section = extract_section(
        bundle.full_markdown,
        "### Task Memory",
        "### Allowed Actions Now",
    )

    assert "task_memory_search_hints" not in task_memory_section
    assert "- search hints:" not in task_memory_section
    assert "- surfaced curated refs:" in task_memory_section
    assert "  - kind: wiki" in task_memory_section
    assert "    slot: auth_refresh_notes" in task_memory_section
    assert "    path: " in task_memory_section
    assert "auth-refresh-notes.md" in task_memory_section
    assert "    description: Curated auth refresh notes for the current fix." in (
        task_memory_section
    )
    assert "    - description: Curated auth refresh notes for the current fix." not in (
        task_memory_section
    )


def test_task_memory_is_omitted_without_surfaced_curated_refs(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    retained_refs = tuple(
        ref
        for ref in request.manifest.current_context.current_relevant_paths
        if ref.kind not in {EvidenceKind.WIKI, EvidenceKind.DOC}
    )
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "manifest": request.manifest.model_copy(
                    update={
                        "current_context": request.manifest.current_context.model_copy(
                            update={"current_relevant_paths": retained_refs}
                        )
                    }
                ),
            }
        )
    )

    assert "### Task Memory" not in bundle.input_text


def test_latest_checkpoint_context_renders_stable_checkpoint_path(tmp_path: Path) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    checkpoint_section = extract_section(
        bundle.full_markdown,
        "### Latest Checkpoint Context",
        "### Consumed Durable Refs",
    )

    assert str(request.manifest.current_context.latest_checkpoint_path) in checkpoint_section


def test_latest_checkpoint_context_prefers_latest_relevant_checkpoint_path(tmp_path: Path) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    relevant_checkpoint_path = (
        tmp_path / "_runtime" / "attempts" / "attempt.scope_change.02" / "latest-checkpoint.md"
    )
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "manifest": request.manifest.model_copy(
                    update={
                        "current_context": request.manifest.current_context.model_copy(
                            update={
                                "latest_relevant_checkpoint_path": relevant_checkpoint_path,
                            }
                        )
                    }
                ),
                "latest_checkpoint": CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Use the surfaced investigation handoff first.",
                        next_step="Carry this checkpoint forward into the current decision.",
                    ),
                ),
            }
        )
    )

    checkpoint_section = extract_section(
        bundle.full_markdown,
        "### Latest Checkpoint Context",
        "### Consumed Durable Refs",
    )
    consumed_refs_section = extract_section(
        bundle.full_markdown,
        "### Consumed Durable Refs",
        "### Transient Refs",
    )

    assert str(relevant_checkpoint_path) in checkpoint_section
    assert str(request.manifest.current_context.latest_checkpoint_path) not in checkpoint_section
    assert str(relevant_checkpoint_path) not in consumed_refs_section


def test_latest_checkpoint_context_stays_explicit_when_no_checkpoint_is_surfaced(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT).model_copy(
        update={"latest_checkpoint": None}
    )
    bundle = render_prompt_bundle(request)

    checkpoint_section = extract_section(
        bundle.full_markdown,
        "### Latest Checkpoint Context",
        "### Consumed Durable Refs",
    )

    assert "- path: null" in checkpoint_section
    assert "- no current relevant checkpoint is surfaced" in checkpoint_section


def test_assignment_consumes_support_checkpoint_refs_without_widening_current_assignment_paths(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    retry_handoff_ref = NodeRuntimeFileRef(
        kind=NodeRuntimeFileKind.CHECKPOINT,
        path=(
            tmp_path / "_runtime" / "attempts" / "attempt.implement_fix.00" / "latest-checkpoint.md"
        ),
        description="Retry handoff checkpoint for the same assignment.",
    )
    assignment = request.assignment.model_copy(
        update={
            "consumes": (
                retry_handoff_ref,
                *request.assignment.consumes,
            )
        }
    )
    manifest = request.manifest.model_copy(
        update={
            "current_context": request.manifest.current_context.model_copy(
                update={
                    "current_relevant_paths": (
                        retry_handoff_ref,
                        *request.manifest.current_context.current_relevant_paths,
                    )
                }
            )
        }
    )

    bundle = render_prompt_bundle(
        request.model_copy(update={"assignment": assignment, "manifest": manifest})
    )

    assignment_section = extract_section(
        bundle.full_markdown,
        "### Current Assignment",
        "### Latest Checkpoint Context",
    )
    consumed_refs_section = bundle.full_markdown.split(
        "### Consumed Durable Refs",
        maxsplit=1,
    )[1]

    assert "Retry handoff checkpoint" in assignment_section
    assert "attempt.implement_fix.00/latest-checkpoint.md" not in assignment_section
    assert "attempt.implement_fix.00/latest-checkpoint.md" in consumed_refs_section
