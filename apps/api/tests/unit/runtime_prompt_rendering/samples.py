from __future__ import annotations

from pathlib import Path

from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointKind,
    CheckpointOutcome,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    NodeKind,
    ProduceRequirement,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    ResolvedNodeContext,
)

from .manifest_samples import (
    findings_report_path,
    sample_manifest,
)
from .planning_samples import (
    non_root_parent_request,
    parent_request,
)

__all__ = [
    "non_root_parent_request",
    "parent_request",
    "sample_assignment",
    "sample_checkpoint",
    "sample_manifest",
    "worker_request",
]


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
                path=findings_report_path(tmp_path),
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
        session_key="sess_worker_dispatch_01",
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
