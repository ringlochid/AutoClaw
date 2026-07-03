from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .load import (
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
    RenderedPromptOutputLike,
    ResolvedNodeContext,
    render_prompt_bundle,
)
from .sample_palette import build_structural_edit_palette


def build_sample_manifest(
    tmp_path: Path,
    *,
    node_key: str,
    owner_node_key: str,
    attempt_id: str,
    latest_relevant_checkpoint_path: Path | None = None,
    current_relevant_paths: tuple[Any, ...] = (),
) -> Any:
    runtime_path = tmp_path / "_runtime"
    attempt_path = runtime_path / "attempts" / attempt_id
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
            workflow_key="reviewed-change-release",
            description="Execute one implementation subtree and close only after review.",
        ),
        filesystem_roots=ManifestFilesystemRootsProjection(
            workspace_path=tmp_path / "workspace",
            context_path=tmp_path / "context",
            outputs_path=tmp_path / "outputs",
            tmp_path=tmp_path / "tmp",
            runtime_path=runtime_path,
        ),
        structural_edit_palette=build_structural_edit_palette(),
        current_context=ManifestCurrentContextProjection(
            current_node_key=node_key,
            owner_node_key=owner_node_key,
            active_attempt_id=attempt_id,
            active_assignment_path=attempt_path / "assignment.md",
            latest_checkpoint_path=attempt_path / "latest-checkpoint.md",
            latest_relevant_checkpoint_path=latest_relevant_checkpoint_path,
            current_relevant_paths=current_relevant_paths,
        ),
        node_tree=(),
        dependency_index=(),
    )


def example_task_root() -> Path:
    return Path("C:/tasks/task_2026_0042")


def build_worker_prompt_request(tmp_path: Path, *, send_mode: Any) -> Any:
    return PromptRenderRequest(
        prompt_family=PromptFamily.WORKER_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        session_key="sess_worker_dispatch_01",
        current_node=build_worker_node_context(),
        manifest=build_worker_manifest(tmp_path),
        assignment=build_worker_assignment(tmp_path),
        latest_checkpoint=build_worker_checkpoint(),
    )


def build_worker_node_context() -> Any:
    return ResolvedNodeContext(
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
    )


def build_worker_manifest(tmp_path: Path) -> Any:
    return build_sample_manifest(
        tmp_path,
        node_key="implement_fix",
        owner_node_key="implement_fix",
        attempt_id="attempt.implement_fix.01",
        current_relevant_paths=(
            EvidenceRef(
                kind=EvidenceKind.WIKI,
                path=tmp_path / "context" / "wiki" / "auth-refresh-history.md",
                description="Curated task-memory page for earlier auth-refresh attempts.",
            ),
        ),
    )


def build_worker_assignment(tmp_path: Path) -> Any:
    return AssignmentProjection(
        assignment_key="implement_fix.assign-01",
        node_key="implement_fix",
        summary="Repair the auth-refresh defect and publish the required evidence.",
        instruction="Change only the bounded auth-refresh logic and rerun scoped verification.",
        criteria=(
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="fix_acceptance",
                path=tmp_path / "_runtime" / "criteria" / "fix_acceptance.v01.md",
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


def build_worker_checkpoint() -> Any:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind.TERMINAL,
        outcome=CheckpointOutcome.RETRY,
        handoff=CheckpointHandoff(
            summary="Prior attempt fixed the primary path but missed one recovery branch.",
            next_step="Keep the same assignment and repair the missed branch.",
        ),
        task_memory_search_hints=("recovery branch note",),
    )


def build_parent_prompt_request(tmp_path: Path, *, send_mode: Any) -> Any:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        session_key="sess_root_dispatch_07",
        current_node=build_parent_node_context(),
        manifest=build_parent_manifest(tmp_path),
        assignment=build_parent_assignment(tmp_path),
        latest_checkpoint=build_parent_checkpoint(),
    )


def build_non_root_parent_blocked_prompt_request(tmp_path: Path, *, send_mode: Any) -> Any:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        session_key="sess_parent_dispatch_03",
        current_node=build_non_root_parent_node_context(),
        manifest=build_non_root_parent_manifest(tmp_path),
        assignment=build_non_root_parent_assignment(tmp_path),
        latest_checkpoint=build_non_root_parent_blocked_checkpoint(),
    )


def build_parent_node_context() -> Any:
    return ResolvedNodeContext(
        node_key="root",
        node_kind=NodeKind.ROOT,
        node_description="Coordinate the whole flow and decide the next bounded child step.",
        role_key="root_planning_lead",
        role_revision_no=41,
        role_description="Root coordinator for the whole task.",
        role_instruction="Choose the next bounded child step and close only when release is legal.",
        policy_key="standard-root-planning",
        policy_revision_no=51,
        policy_description="Default root planning and closure behavior.",
        policy_instruction=(
            "Root owns final closure and may use release tools only when current "
            "evidence makes that legal."
        ),
    )


def build_non_root_parent_node_context() -> Any:
    return ResolvedNodeContext(
        node_key="triage_recovery",
        node_kind=NodeKind.PARENT,
        node_description=(
            "Coordinate the recovery subtree and return control upward when the "
            "current parent assignment cannot continue."
        ),
        role_key="planning_lead",
        role_revision_no=42,
        role_description="Parent coordinator for scoped recovery planning.",
        role_instruction=(
            "Either stage one bounded child assignment or close this parent node "
            "with a terminal checkpoint."
        ),
        policy_key="standard-parent-planning",
        policy_revision_no=52,
        policy_description="Default parent planning and escalation behavior.",
        policy_instruction="Use root-only release tools only when the current node is root.",
    )


def build_parent_manifest(tmp_path: Path) -> Any:
    latest_checkpoint_path = (
        tmp_path / "_runtime" / "attempts" / "attempt.investigate_issue.02" / "latest-checkpoint.md"
    )
    return build_sample_manifest(
        tmp_path,
        node_key="root",
        owner_node_key="root",
        attempt_id="attempt.root.07",
        latest_relevant_checkpoint_path=latest_checkpoint_path,
        current_relevant_paths=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=latest_checkpoint_path,
                description="Latest investigation handoff for this root decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.WIKI,
                path=tmp_path / "context" / "wiki" / "cookie-rotation-note.md",
                description="Curated task-memory note about cookie rotation.",
            ),
        ),
    )


def build_non_root_parent_manifest(tmp_path: Path) -> Any:
    latest_checkpoint_path = (
        tmp_path / "_runtime" / "attempts" / "attempt.triage_recovery.03" / "latest-checkpoint.md"
    )
    child_checkpoint_path = (
        tmp_path / "_runtime" / "attempts" / "attempt.repro_fixture.02" / "latest-checkpoint.md"
    )
    return build_sample_manifest(
        tmp_path,
        node_key="triage_recovery",
        owner_node_key="triage_recovery",
        attempt_id="attempt.triage_recovery.03",
        latest_relevant_checkpoint_path=latest_checkpoint_path,
        current_relevant_paths=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=child_checkpoint_path,
                description="Latest child checkpoint proving the recovery branch is blocked.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="repro_report",
                version=3,
                path=tmp_path
                / "outputs"
                / "artifacts"
                / "repro_fixture"
                / "repro_report"
                / "repro_report.v03.md",
                description="Current repro evidence showing the parent cannot continue.",
            ),
        ),
    )


def build_parent_assignment(tmp_path: Path) -> Any:
    checkpoint_path = (
        tmp_path / "_runtime" / "attempts" / "attempt.investigate_issue.02" / "latest-checkpoint.md"
    )
    findings_path = (
        tmp_path
        / "outputs"
        / "artifacts"
        / "investigate_issue"
        / "findings_report"
        / "findings_report.v02.md"
    )
    return AssignmentProjection(
        assignment_key="root.assign-07",
        node_key="root",
        summary="Decide the next bounded child step after the current investigation result.",
        instruction=(
            "Stay inside the current owned subtree and preserve reasoning durably when needed."
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
                path=checkpoint_path,
                description="Latest investigation handoff for this root decision.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="findings_report",
                version=2,
                path=findings_path,
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


def build_non_root_parent_assignment(tmp_path: Path) -> Any:
    child_checkpoint_path = (
        tmp_path / "_runtime" / "attempts" / "attempt.repro_fixture.02" / "latest-checkpoint.md"
    )
    repro_report_path = (
        tmp_path
        / "outputs"
        / "artifacts"
        / "repro_fixture"
        / "repro_report"
        / "repro_report.v03.md"
    )
    return AssignmentProjection(
        assignment_key="triage_recovery.assign-03",
        node_key="triage_recovery",
        summary=(
            "Decide whether the recovery subtree can continue after the latest child evidence."
        ),
        instruction=(
            "If no bounded child assignment can move the recovery branch forward, publish "
            "a terminal blocked checkpoint and close this parent node with blocked."
        ),
        criteria=(
            EvidenceRef(
                kind=EvidenceKind.CRITERIA,
                slot="parent_blocked_rule",
                path=tmp_path / "_runtime" / "criteria" / "parent_blocked_rule.md",
                description="Parent blocked escalation criteria.",
            ),
        ),
        consumes=(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=child_checkpoint_path,
                description="Latest child checkpoint proving the recovery branch is blocked.",
            ),
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot="repro_report",
                version=3,
                path=repro_report_path,
                description="Current repro evidence showing the parent cannot continue.",
            ),
        ),
        produces=(
            ProduceRequirement(
                slot="parent_handoff",
                description="Durable parent handoff if this node closes blocked.",
                file_hint="parent_handoff.md",
            ),
        ),
        task_memory_search_hints=("recovery fixture ownership", "blocked parent handoff"),
    )


def build_parent_checkpoint() -> Any:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind.PROGRESS,
        handoff=CheckpointHandoff(
            summary=(
                "One implementation child assignment is already staged and the "
                "current checkpoint explains why this child is next."
            ),
            next_step="If the handoff is sufficient, emit yield.",
        ),
        task_memory_search_hints=("refresh token expiry branch",),
    )


def build_non_root_parent_blocked_checkpoint() -> Any:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind.TERMINAL,
        outcome=CheckpointOutcome.BLOCKED,
        handoff=CheckpointHandoff(
            summary=(
                "The recovery subtree cannot continue because the remaining fixture "
                "ownership sits outside this parent node."
            ),
            next_step=(
                "Return control to the root parent with a blocked handoff; do not use "
                "root-only release_blocked from this non-root parent dispatch."
            ),
            blockers=("fixture owner decision is outside the current parent scope",),
        ),
        task_memory_search_hints=("blocked parent handoff",),
    )


def render_live_prompt_outputs() -> dict[str, RenderedPromptOutputLike]:
    tmp_path = example_task_root()
    return {
        "worker_dispatch_prompt": render_prompt_bundle(
            build_worker_prompt_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
        ),
        "parent_root_dispatch_prompt": render_prompt_bundle(
            build_parent_prompt_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
        ),
        "parent_root_dispatch_prompt_non_root_blocked": render_prompt_bundle(
            build_non_root_parent_blocked_prompt_request(
                tmp_path,
                send_mode=PromptSendMode.FULL_PROMPT,
            )
        ),
    }


def render_blocked_ending_sketch() -> str:
    return "\n".join(
        [
            "## Latest Checkpoint Context",
            "- path: C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/"
            "latest-checkpoint.md",
            "- checkpoint_kind: progress",
            "- outcome: null",
            "- summary: the bounded code change landed, but the final browser fixture "
            "still fails for reasons outside the current writable scope",
            "- next_step: decide whether the remaining failure is retriable within "
            "the same assignment or whether the current attempt should end blocked",
            "- blockers:",
            "  - browser fixture ownership is outside the current assignment scope",
            "",
            "## Consumed Durable Refs",
            "- kind: artifact",
            "  slot: verification_report",
            "  version: 2",
            "  path: C:/tasks/task_2026_0042/outputs/artifacts/implement_fix/"
            "verification_report/verification_report.v02.md",
            "  description: latest verification evidence showing the remaining "
            "out-of-scope failure",
            "",
            "## Allowed Actions Now",
            "- if a later attempt on the same assignment is still justified, call "
            "`record_checkpoint` with `checkpoint_kind: terminal` and `outcome: retry`, "
            "then emit `retry`",
            "- if the current assignment cannot continue without out-of-scope help, "
            "call `record_checkpoint` with `checkpoint_kind: terminal` and "
            "`outcome: blocked`, then emit `blocked`",
            "- do not rely on transcript memory to explain the unresolved state",
            "",
            "## Publication Rule",
            "- terminal closure still requires checkpoint handoff through `record_checkpoint`",
            "- already-published outputs stay durable evidence; `blocked` does not erase them",
        ]
    )


def render_generated_example_bodies() -> dict[str, str]:
    prompt_outputs = render_live_prompt_outputs()
    return {
        "parent_root_dispatch_prompt": prompt_outputs["parent_root_dispatch_prompt"].full_markdown,
        "parent_root_dispatch_prompt non-root blocked closure": prompt_outputs[
            "parent_root_dispatch_prompt_non_root_blocked"
        ].full_markdown,
        "worker_dispatch_prompt": prompt_outputs["worker_dispatch_prompt"].full_markdown,
        "worker_dispatch_prompt blocked-ending sketch": render_blocked_ending_sketch(),
    }
