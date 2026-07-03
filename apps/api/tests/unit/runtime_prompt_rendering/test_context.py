from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from autoclaw.runtime import EvidenceKind, EvidenceRef, NodeKind, PromptSendMode
from autoclaw.runtime.contracts import (
    CommandRunRecord,
    CommandRunState,
    CommandRunTerminalResult,
    HumanRequestItem,
    HumanRequestItemResponse,
    HumanRequestKind,
    HumanRequestOption,
    HumanRequestRead,
    HumanRequestResolution,
    HumanRequestResolutionKind,
    HumanRequestStatus,
    HumanRequestTimeout,
    ManifestNodeProjection,
    PendingHumanRequest,
    TaskEventSource,
)
from autoclaw.runtime.prompt import render_prompt_bundle
from autoclaw.runtime.prompt.bundle import render_manifest_markdown

from .support import (
    extract_section,
    parent_request,
    worker_request,
)


def test_manifest_markdown_renders_source_disambiguated_node_instruction(
    tmp_path: Path,
) -> None:
    manifest = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT).manifest
    manifest = manifest.model_copy(
        update={
            "node_tree": (
                ManifestNodeProjection(
                    node_key="change_subtree",
                    node_kind=NodeKind.PARENT,
                    role="planning_lead",
                    policy="standard-parent",
                    description="Coordinate the implementation subtree.",
                    node_instruction="Review child evidence before assigning more work.",
                ),
            )
        }
    )

    manifest_markdown = render_manifest_markdown(manifest)

    assert "- node_instruction: Review child evidence before assigning more work." in (
        manifest_markdown
    )


def test_current_assignment_renders_reduced_claims_and_consumed_refs_keep_exact_paths(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    assignment_section = extract_section(
        bundle.full_markdown,
        "### Current Assignment",
        "### Latest Checkpoint Context",
    )
    consumed_refs_section = bundle.full_markdown.split(
        "### Consumed Durable Refs",
        maxsplit=1,
    )[1]

    assert "change_scope_report.v02.md" not in assignment_section
    assert "fix_acceptance.v01.md" not in assignment_section
    assert "version: 2" not in assignment_section
    assert "Current findings for the scoped fix." in assignment_section
    assert str(request.manifest.current_context.active_assignment_path) in assignment_section
    assert str(request.manifest.current_context.latest_checkpoint_path) not in assignment_section
    assert "    slot: fix_acceptance" in assignment_section
    assert "    description: Bounded fix acceptance criteria." in assignment_section
    assert "    - slot: fix_acceptance" not in assignment_section
    assert "    - description: Bounded fix acceptance criteria." not in assignment_section

    assert "change_scope_report.v02.md" in consumed_refs_section
    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "version: 2" in consumed_refs_section
    assert "auth-refresh-notes.md" in consumed_refs_section
    assert "attempt.scope_change.02/latest-checkpoint.md" in consumed_refs_section
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
        "### Consumed Durable Refs",
        "### Transient Refs",
    )

    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "change_scope_report.v02.md" in consumed_refs_section
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
        "### Consumed Durable Refs",
        "### Transient Refs",
    )

    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "change_scope_report.v02.md" in consumed_refs_section
    assert "version: 2" in consumed_refs_section
    assert "auth-refresh-notes.md" not in consumed_refs_section
    assert "attempt.scope_change.02/latest-checkpoint.md" not in consumed_refs_section


def test_worker_prompt_surfaces_terminal_command_run_context_without_raw_logs(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "command_run_continuation_context": CommandRunRecord(
                    run_id="command-run.task_2026_0042.01",
                    task_id=request.task_id,
                    dispatch_id="dispatch.task_2026_0042.implement_fix.01",
                    attempt_id="attempt.implement_fix.01",
                    command="pytest apps/api/tests/integration/runtime/routes -q",
                    description="Run focused command-run route tests.",
                    workdir="apps/api",
                    state=CommandRunState.FAILED,
                    created_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
                    started_at=datetime(2026, 6, 25, 12, 1, tzinfo=UTC),
                    ended_at=datetime(2026, 6, 25, 12, 5, tzinfo=UTC),
                    timeout_seconds=900,
                    latest_update="2 tests failed during collection",
                    latest_log_ref="logs/raw-output.txt",
                    terminal_result=CommandRunTerminalResult(
                        summary="2 tests failed during collection",
                        exit_code=1,
                        signal=None,
                        log_ref="logs/pytest-terminal.txt",
                    ),
                    terminal_event_source=TaskEventSource.CONTROLLER,
                )
            }
        )
    )

    command_run_section = extract_section(
        bundle.full_markdown,
        "### Command Run Continuation Context",
        "### Consumed Durable Refs",
    )

    assert "command-run.task_2026_0042.01" in command_run_section
    assert "pytest apps/api/tests/integration/runtime/routes -q" in command_run_section
    assert "Run focused command-run route tests." in command_run_section
    assert "state: failed" in command_run_section
    assert "latest_update: 2 tests failed during collection" in command_run_section
    assert "summary: 2 tests failed during collection" in command_run_section
    assert "exit_code: 1" in command_run_section
    assert "log_ref: logs/pytest-terminal.txt" in command_run_section
    assert "logs/raw-output.txt" not in command_run_section


def test_worker_prompt_surfaces_terminal_human_request_context(
    tmp_path: Path,
) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "human_request_continuation_context": HumanRequestRead(
                    request=PendingHumanRequest(
                        request_id="human-request.task_2026_0042.01",
                        task_id=request.task_id,
                        title="Review the scoped fix",
                        summary="A human review is required before the worker continues.",
                        kind=HumanRequestKind.REVIEW,
                        requester_node="root",
                        items=(
                            HumanRequestItem(
                                item_id="review_choice",
                                prompt="Should the worker proceed with the fix?",
                                options=(
                                    HumanRequestOption(id="approve", title="Approve"),
                                    HumanRequestOption(id="revise", title="Revise"),
                                ),
                                recommended_option="approve",
                            ),
                        ),
                        timeout=HumanRequestTimeout(
                            due_at=datetime(2026, 6, 25, 12, 5, tzinfo=UTC),
                            default_behavior="Proceed with the recommended review option.",
                        ),
                        suggested_human_instruction="Inspect the patch before answering.",
                        opened_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
                        status=HumanRequestStatus.RESOLVED,
                    ),
                    resolution=HumanRequestResolution(
                        request_id="human-request.task_2026_0042.01",
                        task_id=request.task_id,
                        resolution_kind=HumanRequestResolutionKind.ANSWERED,
                        item_responses=(
                            HumanRequestItemResponse(
                                item_id="review_choice",
                                selected_option="approve",
                                extra_notes="Looks good.",
                            ),
                        ),
                        resolved_at=datetime(2026, 6, 25, 12, 2, tzinfo=UTC),
                        resolved_by_actor_ref=None,
                    ),
                )
            }
        )
    )

    human_request_section = extract_section(
        bundle.full_markdown,
        "### Human Request Continuation Context",
        "### Consumed Durable Refs",
    )

    assert "human-request.task_2026_0042.01" in human_request_section
    assert "resolution_kind: answered" in human_request_section
    assert "resolved_by_actor_ref: None" in human_request_section
    assert "recommended_option: approve" in human_request_section
    assert "- id: approve" in human_request_section
    assert "- id: revise" in human_request_section
    assert "selected_option: approve" in human_request_section
    assert "timeout_default_behavior: Proceed with the recommended review option." in (
        human_request_section
    )


def test_parent_prompt_surfaces_current_decision_criteria_and_artifact_refs(
    tmp_path: Path,
) -> None:
    request = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

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

    assert "attempt.scope_change.02/latest-checkpoint.md" in checkpoint_section
    assert "root_release_rule.md" in consumed_refs_section
    assert "Root completion and release criteria." in consumed_refs_section
    assert "change_scope_report.v02.md" in consumed_refs_section
    assert "Current investigation findings for the auth-refresh regression." in (
        consumed_refs_section
    )
    assert "version: 2" in consumed_refs_section
    assert "investigation-compare-grid.md" not in consumed_refs_section
    assert "attempt.scope_change.02/latest-checkpoint.md" not in consumed_refs_section


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
        "### Consumed Durable Refs",
        "### Transient Refs",
    )

    assert "review_report.v03.md" in consumed_refs_section
    assert "Current child review report surfaced for the root decision." in consumed_refs_section
    assert "version: 3" in consumed_refs_section
