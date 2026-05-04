from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointKind,
    CheckpointOutcome,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    ManifestCurrentContextProjection,
    ManifestFilesystemRootsProjection,
    ManifestProjection,
    ManifestTaskProjection,
    ManifestWorkflowProjection,
    NodeKind,
    ProduceRequirement,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    ResolvedNodeContext,
)
from app.runtime.render import render_prompt_bundle


def _sample_manifest(tmp_path: Path) -> ManifestProjection:
    runtime_path = tmp_path / "_runtime"
    attempt_path = runtime_path / "attempts" / "attempt.implement_fix.01"
    return ManifestProjection(
        active_flow_revision_id="flowrev_0001",
        generated_at=datetime.now(tz=UTC),
        task=ManifestTaskProjection(
            task_id="task_2026_0042",
            task_key="auth-refresh-hardening",
            title="Harden auth refresh flow",
            summary="Investigate and fix the auth refresh regression.",
            instruction="Stay scoped to the auth refresh failure path only.",
        ),
        workflow=ManifestWorkflowProjection(
            workflow_key="normal-parent-first-release",
            description="Execute one implementation subtree and close only after review.",
        ),
        filesystem_roots=ManifestFilesystemRootsProjection(
            workspace_path=tmp_path / "workspace",
            context_path=tmp_path / "context",
            outputs_path=tmp_path / "outputs",
            tmp_path=tmp_path / "tmp",
            runtime_path=runtime_path,
        ),
        current_context=ManifestCurrentContextProjection(
            current_node_key="implement_fix",
            owner_node_key="implement_fix",
            active_attempt_id="attempt.implement_fix.01",
            active_assignment_path=attempt_path / "assignment.md",
            latest_checkpoint_path=attempt_path / "latest-checkpoint.md",
        ),
        node_tree=(),
        dependency_index=(),
    )


def _sample_assignment(tmp_path: Path) -> AssignmentProjection:
    return AssignmentProjection(
        assignment_key="implement_fix.assign-01",
        node_key="implement_fix",
        summary="Repair the auth-refresh defect and publish the required evidence.",
        instruction="Change only the bounded auth-refresh logic and rerun scoped verification.",
        criteria=(
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="fix_acceptance",
                path=tmp_path / "context" / "criteria" / "fix_acceptance.md",
                description="Bounded fix acceptance criteria.",
            ),
        ),
        consumes=(
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=tmp_path
                / "outputs"
                / "artifacts"
                / "investigate_issue"
                / "findings_report"
                / "findings_report.v02.md",
                description="Current findings for the scoped fix.",
            ),
        ),
        produces=(
            ProduceRequirement(
                slot="change_patch",
                description="Bounded code change artifact.",
                file_hint="change_patch.diff",
            ),
            ProduceRequirement(
                slot="verification_report",
                description="Scoped verification evidence.",
                file_hint="verification_report.md",
            ),
        ),
        transient_refs=(
            EvidenceRef(
                kind=EvidenceKind.TRANSIENT,
                path=tmp_path / "tmp" / "transfers" / "implement_fix" / "repro-commands.txt",
                description="Optional repro commands from the prior attempt.",
            ),
        ),
        task_memory_search_hints=("auth refresh", "cookie rotation note"),
    )


def _sample_checkpoint(tmp_path: Path) -> CheckpointProjection:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind.TERMINAL,
        outcome=CheckpointOutcome.BLOCKED,
        handoff=CheckpointHandoff(
            summary="Browser refresh path still fails the current criteria.",
            next_step="Parent should decide whether to assign a narrower repro child.",
            risks=("Current repro is still flaky on one browser family.",),
        ),
        produced_artifacts=(
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="verification_report",
                version=2,
                path=tmp_path
                / "outputs"
                / "artifacts"
                / "implement_fix"
                / "verification_report"
                / "verification_report.v02.md",
                description="Scoped verification evidence for the current fix assignment.",
            ),
        ),
    )


def _worker_request(tmp_path: Path, *, send_mode: PromptSendMode) -> PromptRenderRequest:
    return PromptRenderRequest(
        prompt_family=PromptFamily.WORKER_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        current_node=ResolvedNodeContext(
            node_key="implement_fix",
            node_kind=NodeKind.WORKER,
            node_description="Repair the bounded auth-refresh defect.",
            role_key="engineer",
            role_revision_no=44,
            role_description="Worker for one bounded engineering assignment.",
            role_instruction="Complete only the current assignment.",
            policy_key="standard-worker",
            policy_revision_no=53,
            policy_description="Default worker behavior for bounded work.",
        ),
        manifest=_sample_manifest(tmp_path),
        assignment=_sample_assignment(tmp_path),
        latest_checkpoint=_sample_checkpoint(tmp_path),
    )


def _index(markdown: str, heading: str) -> int:
    return markdown.index(heading)


def test_render_prompt_bundle_keeps_section_order_and_omits_only_static_sections(
    tmp_path: Path,
) -> None:
    full_prompt = render_prompt_bundle(
        _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )
    same_session = render_prompt_bundle(
        _worker_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )

    ordered_headings = [
        "## Operating Model",
        "## Task Identity",
        "## Node Purpose",
        "## Current Dispatch",
        "## Workflow Manifest",
        "## Current Assignment",
        "## Latest Checkpoint Context",
        "## Consumed Durable Refs",
        "## Transient Refs",
        "## Task Memory",
        "## Allowed Actions Now",
        "## Publication Rule",
    ]
    assert [_index(full_prompt.full_markdown, heading) for heading in ordered_headings] == sorted(
        _index(full_prompt.full_markdown, heading) for heading in ordered_headings
    )
    assert "## Operating Model" not in same_session.input_text
    assert "## Task Identity" not in same_session.input_text
    assert "## Node Purpose" not in same_session.input_text
    assert "## Current Dispatch" in same_session.input_text
    assert "send mode: same_session_continue" in same_session.full_markdown
    assert same_session.full_markdown.startswith("## Operating Model")


def test_current_assignment_renders_reduced_claims_and_consumed_refs_keep_exact_paths(
    tmp_path: Path,
) -> None:
    bundle = render_prompt_bundle(_worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT))

    assignment_section = bundle.full_markdown.split("## Current Assignment", maxsplit=1)[1].split(
        "## Latest Checkpoint Context",
        maxsplit=1,
    )[0]
    consumed_refs_section = bundle.full_markdown.split(
        "## Consumed Durable Refs",
        maxsplit=1,
    )[1]

    assert "findings_report.v02.md" not in assignment_section
    assert "fix_acceptance.md" not in assignment_section
    assert "version: 2" not in assignment_section
    assert "Current findings for the scoped fix." in assignment_section

    assert "findings_report.v02.md" in consumed_refs_section
    assert "fix_acceptance.md" in consumed_refs_section
    assert "version: 2" in consumed_refs_section
