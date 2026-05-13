from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.runtime.contracts import (
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
    StructuralEditPaletteProjection,
    StructuralEditPolicyProjection,
    StructuralEditRoleProjection,
)

__all__ = [
    "findings_report_path",
    "investigation_checkpoint_path",
    "sample_manifest",
]


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
        structural_edit_palette=structural_edit_palette(),
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
                    path=investigation_checkpoint_path(tmp_path),
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
                    path=findings_report_path(tmp_path),
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


def findings_report_path(tmp_path: Path) -> Path:
    return (
        tmp_path
        / "outputs"
        / "artifacts"
        / "investigate_issue"
        / "findings_report"
        / "findings_report.v02.md"
    )


def investigation_checkpoint_path(tmp_path: Path) -> Path:
    return (
        tmp_path / "_runtime" / "attempts" / "attempt.investigate_issue.02" / "latest-checkpoint.md"
    )


def structural_edit_palette() -> StructuralEditPaletteProjection:
    return StructuralEditPaletteProjection(
        roles=(
            StructuralEditRoleProjection(
                role="architect",
                allowed_node_kinds=(NodeKind.WORKER,),
                description="Run a bounded QA sweep over current implementation evidence.",
            ),
            StructuralEditRoleProjection(
                role="planning_lead",
                allowed_node_kinds=(NodeKind.PARENT, NodeKind.WORKER),
                description="Coordinate a bounded implementation or review subtree.",
            ),
        ),
        policies=(
            StructuralEditPolicyProjection(
                policy="standard-parent-planning",
                applies_to=(NodeKind.PARENT,),
                description="Default planning policy for bounded parent coordination.",
            ),
            StructuralEditPolicyProjection(
                policy="standard-review",
                applies_to=(NodeKind.WORKER,),
                description="Default review policy for worker evidence checks.",
            ),
        ),
    )
