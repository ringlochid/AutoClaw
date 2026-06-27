from __future__ import annotations

from pathlib import Path

from autoclaw.runtime import (
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    ManifestCurrentContextProjection,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    ProduceRequirement,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    ResolvedNodeContext,
)

from .manifest_samples import (
    findings_report_path,
    investigation_checkpoint_path,
    sample_manifest,
)

__all__ = [
    "non_root_parent_request",
    "parent_request",
]


def parent_request(tmp_path: Path, *, send_mode: PromptSendMode) -> PromptRenderRequest:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        session_key="sess_root_dispatch_07",
        current_node=root_node_context(),
        manifest=sample_manifest(tmp_path).model_copy(
            update={"current_context": root_current_context(tmp_path)}
        ),
        assignment=root_assignment(tmp_path),
        latest_checkpoint=root_latest_checkpoint(),
    )


def non_root_parent_request(tmp_path: Path, *, send_mode: PromptSendMode) -> PromptRenderRequest:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        session_key="sess_parent_dispatch_04",
        current_node=parent_node_context(),
        manifest=sample_manifest(tmp_path).model_copy(
            update={"current_context": parent_current_context(tmp_path)}
        ),
        assignment=parent_assignment(tmp_path),
        latest_checkpoint=parent_latest_checkpoint(),
    )


def root_assignment(tmp_path: Path) -> AssignmentProjection:
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
                path=tmp_path / "_runtime" / "criteria" / "root_release_rule.md",
                description="Root completion and release criteria.",
            ),
        ),
        consumes=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=investigation_checkpoint_path(tmp_path),
                description="Latest investigation handoff for this root decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=findings_report_path(tmp_path),
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


def root_current_context(tmp_path: Path) -> ManifestCurrentContextProjection:
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
        latest_relevant_checkpoint_path=investigation_checkpoint_path(tmp_path),
        current_relevant_paths=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=investigation_checkpoint_path(tmp_path),
                description="Latest investigation handoff for this root decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="root_release_rule",
                path=tmp_path / "_runtime" / "criteria" / "root_release_rule.md",
                description="Root completion and release criteria.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=findings_report_path(tmp_path),
                description="Current investigation findings for the auth-refresh regression.",
            ),
            EvidenceRef(
                kind=EvidenceKind.TRANSIENT,
                path=tmp_path / "tmp" / "transfers" / "root" / "investigation-compare-grid.md",
                description="Optional transient comparison grid for the current root decision.",
            ),
        ),
    )


def root_latest_checkpoint() -> CheckpointProjection:
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


def parent_assignment(tmp_path: Path) -> AssignmentProjection:
    return AssignmentProjection(
        assignment_key="implementation_subtree.assign-04",
        node_key="implementation_subtree",
        summary="Coordinate the next bounded child step for the implementation subtree.",
        instruction="Use surfaced child evidence to choose the next bounded action.",
        criteria=(
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="implementation_subtree_requirements",
                path=tmp_path / "_runtime" / "criteria" / "implementation_subtree_requirements.md",
                description="Current subtree delivery requirements.",
            ),
        ),
        consumes=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=(
                    tmp_path
                    / "_runtime"
                    / "attempts"
                    / "attempt.review_change.01"
                    / "latest-checkpoint.md"
                ),
                description="Latest child checkpoint relevant to this parent decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="review_report",
                version=1,
                path=tmp_path
                / "outputs"
                / "artifacts"
                / "review_change"
                / "review_report"
                / "review_report.v01.md",
                description="Current review report surfaced for parent verification.",
            ),
        ),
        produces=(
            ProduceRequirement(
                slot="subtree_closure_report",
                description="Closure report for the current subtree assignment.",
            ),
        ),
    )


def parent_current_context(tmp_path: Path) -> ManifestCurrentContextProjection:
    return ManifestCurrentContextProjection(
        current_node_key="implementation_subtree",
        owner_node_key="implementation_subtree",
        active_attempt_id="attempt.implementation_subtree.01",
        active_assignment_path=(
            tmp_path
            / "_runtime"
            / "attempts"
            / "attempt.implementation_subtree.01"
            / "assignment.md"
        ),
        latest_checkpoint_path=(
            tmp_path
            / "_runtime"
            / "attempts"
            / "attempt.implementation_subtree.01"
            / "latest-checkpoint.md"
        ),
        latest_relevant_checkpoint_path=(
            tmp_path / "_runtime" / "attempts" / "attempt.review_change.01" / "latest-checkpoint.md"
        ),
        current_relevant_paths=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=(
                    tmp_path
                    / "_runtime"
                    / "attempts"
                    / "attempt.review_change.01"
                    / "latest-checkpoint.md"
                ),
                description="Latest child checkpoint relevant to this parent decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="review_report",
                version=1,
                path=tmp_path
                / "outputs"
                / "artifacts"
                / "review_change"
                / "review_report"
                / "review_report.v01.md",
                description="Current review report surfaced for parent verification.",
            ),
        ),
    )


def parent_latest_checkpoint() -> CheckpointProjection:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind.PROGRESS,
        handoff=CheckpointHandoff(
            summary="Review finished and current subtree evidence is ready for the next decision.",
            next_step="If more bounded work is needed, assign the next child and emit yield.",
        ),
    )


def root_node_context() -> ResolvedNodeContext:
    return ResolvedNodeContext(
        node_key="root",
        node_kind=NodeKind.ROOT,
        node_description="Coordinate the whole flow and decide the next bounded child step.",
        node_instruction="Keep planning bounded to the current task evidence.",
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


def parent_node_context() -> ResolvedNodeContext:
    return ResolvedNodeContext(
        node_key="implementation_subtree",
        node_kind=NodeKind.PARENT,
        node_description=(
            "Coordinate the implementation subtree and decide the next bounded child step."
        ),
        node_instruction="Review current child evidence before creating more work.",
        role_key="planning_lead",
        role_revision_no=12,
        role_description="Parent coordinator for one owned subtree.",
        role_instruction=(
            "Coordinate only the current owned subtree and preserve durable reasoning "
            "when it matters."
        ),
        policy_key="standard-parent-planning",
        policy_revision_no=19,
        policy_description="Default parent planning and review coordination behavior.",
        policy_instruction=(
            "Parent may release green only when the current subtree evidence makes that legal."
        ),
    )
