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
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    ProduceRequirement,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    ResolvedNodeContext,
)


def sample_manifest(tmp_path: Path) -> ManifestProjection:
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
            latest_relevant_checkpoint_path=None,
            current_relevant_paths=(
                NodeRuntimeFileRef(
                    kind=NodeRuntimeFileKind.CHECKPOINT,
                    path=_investigation_checkpoint_path(tmp_path),
                    description="Upstream investigation handoff for the current fix.",
                ),
                EvidenceRef(
                    kind=EvidenceKind.CRITERIA,
                    slot="fix_acceptance",
                    path=tmp_path / "context" / "criteria" / "fix_acceptance.v01.md",
                    description="Bounded fix acceptance criteria.",
                ),
                EvidenceRef(
                    kind=EvidenceKind.ARTIFACT,
                    slot="findings_report",
                    version=2,
                    path=_findings_report_path(tmp_path),
                    description="Current findings for the scoped fix.",
                ),
                EvidenceRef(
                    kind=EvidenceKind.WIKI,
                    slot="auth_refresh_notes",
                    path=tmp_path / "context" / "wiki" / "auth-refresh-notes.md",
                    description="Curated auth refresh notes for the current fix.",
                ),
                EvidenceRef(
                    kind=EvidenceKind.TRANSIENT,
                    path=tmp_path / "tmp" / "transfers" / "implement_fix" / "repro-commands.txt",
                    description="Optional repro commands from the prior attempt.",
                ),
            ),
        ),
        node_tree=(),
        dependency_index=(),
    )


def sample_assignment(tmp_path: Path) -> AssignmentProjection:
    return AssignmentProjection(
        assignment_key="implement_fix.assign-01",
        node_key="implement_fix",
        summary="Repair the auth-refresh defect and publish the required evidence.",
        instruction="Change only the bounded auth-refresh logic and rerun scoped verification.",
        criteria=(
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="fix_acceptance",
                path=tmp_path / "context" / "criteria" / "fix_acceptance.v01.md",
                description="Bounded fix acceptance criteria.",
            ),
        ),
        consumes=(
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=_findings_report_path(tmp_path),
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


def sample_checkpoint(tmp_path: Path) -> CheckpointProjection:
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


def worker_request(tmp_path: Path, *, send_mode: PromptSendMode) -> PromptRenderRequest:
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
        manifest=sample_manifest(tmp_path),
        assignment=sample_assignment(tmp_path),
        latest_checkpoint=sample_checkpoint(tmp_path),
    )


def parent_request(tmp_path: Path, *, send_mode: PromptSendMode) -> PromptRenderRequest:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        current_node=_root_node_context(),
        manifest=sample_manifest(tmp_path).model_copy(
            update={"current_context": _root_current_context(tmp_path)}
        ),
        assignment=_root_assignment(tmp_path),
        latest_checkpoint=_root_latest_checkpoint(),
    )


def _findings_report_path(tmp_path: Path) -> Path:
    return (
        tmp_path
        / "outputs"
        / "artifacts"
        / "investigate_issue"
        / "findings_report"
        / "findings_report.v02.md"
    )


def _investigation_checkpoint_path(tmp_path: Path) -> Path:
    return (
        tmp_path / "_runtime" / "attempts" / "attempt.investigate_issue.02" / "latest-checkpoint.md"
    )


def _root_assignment(tmp_path: Path) -> AssignmentProjection:
    return AssignmentProjection(
        assignment_key="root.assign-07",
        node_key="root",
        summary="Decide the next bounded child step after the current investigation result.",
        instruction=(
            "Stay inside the current direct-child set and preserve reasoning durably when needed."
        ),
        criteria=(
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="root_release_rule",
                path=tmp_path / "context" / "criteria" / "root_release_rule.md",
                description="Root completion and release criteria.",
            ),
        ),
        consumes=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=_investigation_checkpoint_path(tmp_path),
                description="Latest investigation handoff for this root decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=_findings_report_path(tmp_path),
                description="Current investigation findings for the auth-refresh regression.",
            ),
        ),
        produces=(
            ProduceRequirement(
                slot="root_decision_note",
                description=(
                    "Durable decision note required when root reasoning must survive redispatch."
                ),
            ),
        ),
        transient_refs=(
            EvidenceRef(
                kind=EvidenceKind.TRANSIENT,
                path=tmp_path / "tmp" / "transfers" / "root" / "investigation-compare-grid.md",
                description="Optional transient comparison grid for the current root decision.",
            ),
        ),
        task_memory_search_hints=("refresh token expiry branch", "cookie rotation note"),
    )


def _root_current_context(tmp_path: Path) -> ManifestCurrentContextProjection:
    return ManifestCurrentContextProjection(
        current_node_key="root",
        owner_node_key="root",
        active_attempt_id="attempt.root.07",
        active_assignment_path=(
            tmp_path / "_runtime" / "attempts" / "attempt.root.07" / "assignment.md"
        ),
        latest_checkpoint_path=(
            tmp_path / "_runtime" / "attempts" / "attempt.root.07" / "latest-checkpoint.md"
        ),
        latest_relevant_checkpoint_path=_investigation_checkpoint_path(tmp_path),
        current_relevant_paths=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=_investigation_checkpoint_path(tmp_path),
                description="Latest investigation handoff for this root decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="root_release_rule",
                path=tmp_path / "context" / "criteria" / "root_release_rule.md",
                description="Root completion and release criteria.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=_findings_report_path(tmp_path),
                description="Current investigation findings for the auth-refresh regression.",
            ),
            EvidenceRef(
                kind=EvidenceKind.TRANSIENT,
                path=tmp_path / "tmp" / "transfers" / "root" / "investigation-compare-grid.md",
                description="Optional transient comparison grid for the current root decision.",
            ),
        ),
    )


def _root_latest_checkpoint() -> CheckpointProjection:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind.PROGRESS,
        handoff=CheckpointHandoff(
            summary=(
                "One implementation child assignment is already staged and the "
                "current checkpoint explains why this child is next."
            ),
            next_step="If the current handoff is sufficient, emit yield.",
        ),
    )


def _root_node_context() -> ResolvedNodeContext:
    return ResolvedNodeContext(
        node_key="root",
        node_kind=NodeKind.ROOT,
        node_description="Coordinate the whole flow and decide the next bounded child step.",
        role_key="planning_lead",
        role_revision_no=12,
        role_description="Parent/root coordinator for one owned subtree.",
        role_instruction=(
            "Coordinate only the current owned subtree and preserve durable reasoning "
            "when it matters."
        ),
        policy_key="standard-root-planning",
        policy_revision_no=8,
        policy_description="Default root planning and closure behavior.",
        policy_instruction=(
            "Root owns final closure and may use `release_green` or "
            "`release_blocked` only when current evidence makes that legal."
        ),
    )
