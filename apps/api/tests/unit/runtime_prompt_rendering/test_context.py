from __future__ import annotations

from pathlib import Path

from app.runtime.contracts import EvidenceKind, EvidenceRef, PromptSendMode
from app.runtime.prompt.bundle import render_prompt_bundle

from .support import (
    extract_section,
    parent_request,
    worker_request,
)


def test_current_assignment_renders_reduced_claims_and_consumed_refs_keep_exact_paths(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    assignment_section = extract_section(
        bundle.full_markdown,
        "## Current Assignment",
        "## Latest Checkpoint Context",
    )
    consumed_refs_section = bundle.full_markdown.split(
        "## Consumed Durable Refs",
        maxsplit=1,
    )[1]

    assert "findings_report.v02.md" not in assignment_section
    assert "fix_acceptance.v01.md" not in assignment_section
    assert "version: 2" not in assignment_section
    assert "Current findings for the scoped fix." in assignment_section
    assert str(request.manifest.current_context.active_assignment_path) in assignment_section
    assert str(request.manifest.current_context.latest_checkpoint_path) not in assignment_section
    assert "    slot: fix_acceptance" in assignment_section
    assert "    description: Bounded fix acceptance criteria." in assignment_section
    assert "    - slot: fix_acceptance" not in assignment_section
    assert "    - description: Bounded fix acceptance criteria." not in assignment_section

    assert "findings_report.v02.md" in consumed_refs_section
    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "version: 2" in consumed_refs_section
    assert "auth-refresh-notes.md" in consumed_refs_section
    assert "attempt.investigate_issue.02/latest-checkpoint.md" in consumed_refs_section
    assert "  slot: fix_acceptance" in consumed_refs_section
    assert "  description: Bounded fix acceptance criteria." in consumed_refs_section
    assert "  - slot: fix_acceptance" not in consumed_refs_section
    assert "  - description: Bounded fix acceptance criteria." not in consumed_refs_section


def test_consumed_durable_refs_follow_turn_surface_not_only_assignment_claims(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "assignment": request.assignment.model_copy(
                    update={
                        "criteria": (),
                        "consumes": (),
                    }
                )
            }
        )
    )

    consumed_refs_section = extract_section(
        bundle.full_markdown,
        "## Consumed Durable Refs",
        "## Transient Refs",
    )

    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "findings_report.v02.md" in consumed_refs_section
    assert "auth-refresh-notes.md" in consumed_refs_section
    assert "repro-commands.txt" not in consumed_refs_section


def test_worker_prompt_keeps_consumed_durable_refs_when_turn_surface_is_empty(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "manifest": request.manifest.model_copy(
                    update={
                        "current_context": request.manifest.current_context.model_copy(
                            update={"current_relevant_paths": ()}
                        )
                    }
                )
            }
        )
    )

    consumed_refs_section = extract_section(
        bundle.full_markdown,
        "## Consumed Durable Refs",
        "## Transient Refs",
    )

    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "findings_report.v02.md" in consumed_refs_section
    assert "version: 2" in consumed_refs_section
    assert "auth-refresh-notes.md" not in consumed_refs_section
    assert "attempt.investigate_issue.02/latest-checkpoint.md" not in consumed_refs_section


def test_parent_prompt_surfaces_current_decision_criteria_and_artifact_refs(
    tmp_path: Path,
) -> None:
    request = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    checkpoint_section = extract_section(
        bundle.full_markdown,
        "## Latest Checkpoint Context",
        "## Consumed Durable Refs",
    )
    consumed_refs_section = extract_section(
        bundle.full_markdown,
        "## Consumed Durable Refs",
        "## Transient Refs",
    )

    assert "attempt.investigate_issue.02/latest-checkpoint.md" in checkpoint_section
    assert "root_release_rule.md" in consumed_refs_section
    assert "Root completion and release criteria." in consumed_refs_section
    assert "findings_report.v02.md" in consumed_refs_section
    assert "Current investigation findings for the auth-refresh regression." in (
        consumed_refs_section
    )
    assert "version: 2" in consumed_refs_section
    assert "investigation-compare-grid.md" not in consumed_refs_section
    assert "attempt.investigate_issue.02/latest-checkpoint.md" not in consumed_refs_section


def test_parent_prompt_surfaces_current_child_artifact_refs_from_manifest_context(
    tmp_path: Path,
) -> None:
    request = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    child_artifact_ref = EvidenceRef(
        kind=EvidenceKind.ARTIFACT,
        slot="review_report",
        version=3,
        path=tmp_path
        / "outputs"
        / "artifacts"
        / "review_change"
        / "review_report"
        / "review_report.v03.md",
        description="Current child review report surfaced for the root decision.",
    )
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "assignment": request.assignment.model_copy(update={"consumes": ()}),
                "manifest": request.manifest.model_copy(
                    update={
                        "current_context": request.manifest.current_context.model_copy(
                            update={
                                "current_relevant_paths": (
                                    *request.manifest.current_context.current_relevant_paths,
                                    child_artifact_ref,
                                )
                            }
                        )
                    }
                ),
            }
        )
    )

    consumed_refs_section = extract_section(
        bundle.full_markdown,
        "## Consumed Durable Refs",
        "## Transient Refs",
    )

    assert "review_report.v03.md" in consumed_refs_section
    assert "Current child review report surfaced for the root decision." in consumed_refs_section
    assert "version: 3" in consumed_refs_section
