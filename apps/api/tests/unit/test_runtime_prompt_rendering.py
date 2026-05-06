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
from app.runtime.prompt.asset_catalog import (
    list_exact_prompt_block_assets,
    load_exact_prompt_block,
)
from app.runtime.prompt.bundle import render_prompt_bundle


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
            current_relevant_paths=(
                NodeRuntimeFileRef(
                    kind=NodeRuntimeFileKind.CHECKPOINT,
                    path=(
                        tmp_path
                        / "_runtime"
                        / "attempts"
                        / "attempt.investigate_issue.02"
                        / "latest-checkpoint.md"
                    ),
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
                    path=tmp_path
                    / "outputs"
                    / "artifacts"
                    / "investigate_issue"
                    / "findings_report"
                    / "findings_report.v02.md",
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
                path=tmp_path / "context" / "criteria" / "fix_acceptance.v01.md",
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


def _parent_request(tmp_path: Path, *, send_mode: PromptSendMode) -> PromptRenderRequest:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        current_node=ResolvedNodeContext(
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
        ),
        manifest=_sample_manifest(tmp_path).model_copy(
            update={
                "current_context": ManifestCurrentContextProjection(
                    current_node_key="root",
                    owner_node_key="root",
                    active_attempt_id="attempt.root.07",
                    active_assignment_path=(
                        tmp_path / "_runtime" / "attempts" / "attempt.root.07" / "assignment.md"
                    ),
                    latest_checkpoint_path=(
                        tmp_path
                        / "_runtime"
                        / "attempts"
                        / "attempt.root.07"
                        / "latest-checkpoint.md"
                    ),
                    current_relevant_paths=(
                        NodeRuntimeFileRef(
                            kind=NodeRuntimeFileKind.CHECKPOINT,
                            path=(
                                tmp_path
                                / "_runtime"
                                / "attempts"
                                / "attempt.investigate_issue.02"
                                / "latest-checkpoint.md"
                            ),
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
                            path=tmp_path
                            / "outputs"
                            / "artifacts"
                            / "investigate_issue"
                            / "findings_report"
                            / "findings_report.v02.md",
                            description=(
                                "Current investigation findings for the auth-refresh regression."
                            ),
                        ),
                        EvidenceRef(
                            kind=EvidenceKind.TRANSIENT,
                            path=(
                                tmp_path
                                / "tmp"
                                / "transfers"
                                / "root"
                                / "investigation-compare-grid.md"
                            ),
                            description=(
                                "Optional transient comparison grid for the current root decision."
                            ),
                        ),
                    ),
                )
            }
        ),
        assignment=AssignmentProjection(
            assignment_key="root.assign-07",
            node_key="root",
            summary="Decide the next bounded child step after the current investigation result.",
            instruction=(
                "Stay inside the current direct-child set and preserve reasoning durably "
                "when needed."
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
                    path=(
                        tmp_path
                        / "_runtime"
                        / "attempts"
                        / "attempt.investigate_issue.02"
                        / "latest-checkpoint.md"
                    ),
                    description="Latest investigation handoff for this root decision.",
                ),
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
                    description="Current investigation findings for the auth-refresh regression.",
                ),
            ),
            produces=(
                ProduceRequirement(
                    slot="root_decision_note",
                    description=(
                        "Durable decision note required when root reasoning must survive "
                        "redispatch."
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
        ),
        latest_checkpoint=CheckpointProjection(
            checkpoint_kind=CheckpointKind.PROGRESS,
            handoff=CheckpointHandoff(
                summary=(
                    "One implementation child assignment is already staged and the "
                    "current checkpoint explains why this child is next."
                ),
                next_step="If the current handoff is sufficient, emit yield.",
            ),
        ),
    )


def _index(markdown: str, heading: str) -> int:
    return markdown.index(heading)


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


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
    assert "## Consumed Durable Refs" in same_session.input_text
    assert "## Transient Refs" in same_session.input_text
    assert "## Task Memory" in same_session.input_text
    assert "## Allowed Actions Now" in same_session.input_text
    assert "send mode: same_session_continue" in same_session.full_markdown
    assert same_session.full_markdown.startswith("## Operating Model")


def test_same_session_transport_uses_exact_wrapper_asset(tmp_path: Path) -> None:
    worker_bundle = render_prompt_bundle(
        _worker_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )
    parent_bundle = render_prompt_bundle(
        _parent_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )

    wrapper_block = load_exact_prompt_block("autoclaw_same_session_continue_wrapper_v1")
    system_block = load_exact_prompt_block("autoclaw_system_block_v1")

    assert worker_bundle.instructions_text is None
    assert parent_bundle.instructions_text is None
    assert worker_bundle.input_text.startswith(wrapper_block)
    assert parent_bundle.input_text.startswith(wrapper_block)
    assert system_block not in worker_bundle.input_text
    assert system_block not in parent_bundle.input_text


def test_instructions_text_assembles_system_provider_and_worker_blocks(tmp_path: Path) -> None:
    worker_bundle = render_prompt_bundle(
        _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )
    parent_bundle = render_prompt_bundle(
        _parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )

    system_block = load_exact_prompt_block("autoclaw_system_block_v1")
    provider_block = load_exact_prompt_block("autoclaw_provider_continuity_block_v1")
    split_block = load_exact_prompt_block("autoclaw_parent_worker_split_v1")
    boundary_block = load_exact_prompt_block("runtime_boundary_rule_block_v1")
    worker_legality_block = load_exact_prompt_block("runtime_legality_block_worker_v1")
    parent_legality_block = load_exact_prompt_block("runtime_legality_block_parent_v1")

    assert worker_bundle.instructions_text is not None
    assert parent_bundle.instructions_text is not None
    normalized_worker_instructions = _normalize_whitespace(worker_bundle.instructions_text)
    normalized_parent_instructions = _normalize_whitespace(parent_bundle.instructions_text)
    worker_positions = [
        normalized_worker_instructions.index(_normalize_whitespace(system_block)),
        normalized_worker_instructions.index(_normalize_whitespace(provider_block)),
        normalized_worker_instructions.index(_normalize_whitespace(split_block)),
        normalized_worker_instructions.index(_normalize_whitespace(boundary_block)),
        normalized_worker_instructions.index(_normalize_whitespace(worker_legality_block)),
    ]
    parent_positions = [
        normalized_parent_instructions.index(_normalize_whitespace(system_block)),
        normalized_parent_instructions.index(_normalize_whitespace(provider_block)),
        normalized_parent_instructions.index(_normalize_whitespace(split_block)),
        normalized_parent_instructions.index(_normalize_whitespace(boundary_block)),
        normalized_parent_instructions.index(_normalize_whitespace(parent_legality_block)),
    ]
    assert worker_positions == sorted(worker_positions)
    assert parent_positions == sorted(parent_positions)
    assert (
        "- node description: Repair the bounded auth-refresh defect."
        in worker_bundle.instructions_text
    )
    assert (
        "- node description: Coordinate the whole flow and decide the next bounded child step."
        in parent_bundle.instructions_text
    )


def test_exact_prompt_blocks_load_from_packaged_assets_not_prompt_docs() -> None:
    assets = list_exact_prompt_block_assets()

    assert assets
    assert all(asset.asset_path.endswith(".txt") for asset in assets)
    assert all(not asset.asset_path.endswith(".md") for asset in assets)
    assert all(asset.mirror_doc.endswith(".md") for asset in assets)

    system_asset = next(asset for asset in assets if asset.id == "autoclaw_system_block_v1")
    assert system_asset.asset_path == "blocks/autoclaw_system_block_v1.txt"
    assert system_asset.mirror_doc == "prompt-pack/system-and-provider-block.md"
    assert load_exact_prompt_block(system_asset.id).startswith(
        "You are AutoClaw, a delegated node inside a controller-first runtime."
    )


def test_current_dispatch_uses_exact_worker_and_parent_boundary_wording(tmp_path: Path) -> None:
    worker_bundle = render_prompt_bundle(
        _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )
    parent_bundle = render_prompt_bundle(
        _parent_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )

    worker_dispatch = worker_bundle.full_markdown.split("## Current Dispatch", maxsplit=1)[1].split(
        "## Workflow Manifest",
        maxsplit=1,
    )[0]
    parent_dispatch = parent_bundle.input_text.split("## Current Dispatch", maxsplit=1)[1].split(
        "## Workflow Manifest",
        maxsplit=1,
    )[0]

    assert "- current bound turn: current worker turn (internal dispatch id hidden)" in (
        worker_dispatch
    )
    assert (
        "- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`"
        in (worker_dispatch)
    )
    assert "- current bound turn: same-attempt root continuation (internal dispatch id hidden)" in (
        parent_dispatch
    )
    assert (
        "- closure expectation: use control tools now, call `record_checkpoint` if the "
        "reasoning must persist, then later emit `yield` or a terminal boundary" in parent_dispatch
    )


def test_current_assignment_renders_reduced_claims_and_consumed_refs_keep_exact_paths(
    tmp_path: Path,
) -> None:
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    assignment_section = bundle.full_markdown.split("## Current Assignment", maxsplit=1)[1].split(
        "## Latest Checkpoint Context",
        maxsplit=1,
    )[0]
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
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
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

    consumed_refs_section = bundle.full_markdown.split(
        "## Consumed Durable Refs",
        maxsplit=1,
    )[1].split("## Transient Refs", maxsplit=1)[0]

    assert "fix_acceptance.v01.md" in consumed_refs_section
    assert "findings_report.v02.md" in consumed_refs_section
    assert "auth-refresh-notes.md" in consumed_refs_section
    assert "repro-commands.txt" not in consumed_refs_section


def test_task_memory_renders_assignment_hints_checkpoint_hints_and_surfaced_curated_refs(
    tmp_path: Path,
) -> None:
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    latest_checkpoint = request.latest_checkpoint
    assert latest_checkpoint is not None
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "latest_checkpoint": latest_checkpoint.model_copy(
                    update={
                        "task_memory_search_hints": (
                            "checkpoint follow-up",
                            "cookie rotation note",
                        )
                    }
                )
            }
        )
    )

    task_memory_section = bundle.full_markdown.split("## Task Memory", maxsplit=1)[1].split(
        "## Allowed Actions Now",
        maxsplit=1,
    )[0]

    assert "- search hints:" in task_memory_section
    assert "  - auth refresh" in task_memory_section
    assert "  - cookie rotation note" in task_memory_section
    assert "  - checkpoint follow-up" in task_memory_section
    assert task_memory_section.count("  - cookie rotation note") == 1
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


def test_task_memory_can_render_from_surfaced_curated_refs_without_assignment_hints(
    tmp_path: Path,
) -> None:
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    latest_checkpoint = request.latest_checkpoint
    assert latest_checkpoint is not None
    bundle = render_prompt_bundle(
        request.model_copy(
            update={
                "assignment": request.assignment.model_copy(
                    update={"task_memory_search_hints": ()}
                ),
                "latest_checkpoint": latest_checkpoint.model_copy(
                    update={"task_memory_search_hints": ()}
                ),
            }
        )
    )

    task_memory_section = bundle.full_markdown.split("## Task Memory", maxsplit=1)[1].split(
        "## Allowed Actions Now",
        maxsplit=1,
    )[0]

    assert "- search hints:" not in task_memory_section
    assert "- surfaced curated refs:" in task_memory_section
    assert "auth-refresh-notes.md" in task_memory_section


def test_latest_checkpoint_context_renders_stable_checkpoint_path(tmp_path: Path) -> None:
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    checkpoint_section = bundle.full_markdown.split(
        "## Latest Checkpoint Context",
        maxsplit=1,
    )[1].split("## Consumed Durable Refs", maxsplit=1)[0]

    assert str(request.manifest.current_context.latest_checkpoint_path) in checkpoint_section


def test_latest_checkpoint_context_stays_explicit_when_no_checkpoint_is_surfaced(
    tmp_path: Path,
) -> None:
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT).model_copy(
        update={"latest_checkpoint": None}
    )
    bundle = render_prompt_bundle(request)

    checkpoint_section = bundle.full_markdown.split(
        "## Latest Checkpoint Context",
        maxsplit=1,
    )[1].split("## Consumed Durable Refs", maxsplit=1)[0]

    assert "- path: null" in checkpoint_section
    assert "- no current relevant checkpoint is surfaced" in checkpoint_section


def test_assignment_consumes_support_checkpoint_refs_without_widening_current_assignment_paths(
    tmp_path: Path,
) -> None:
    request = _worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
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

    assignment_section = bundle.full_markdown.split("## Current Assignment", maxsplit=1)[1].split(
        "## Latest Checkpoint Context",
        maxsplit=1,
    )[0]
    consumed_refs_section = bundle.full_markdown.split(
        "## Consumed Durable Refs",
        maxsplit=1,
    )[1]

    assert "Retry handoff checkpoint" in assignment_section
    assert "attempt.implement_fix.00/latest-checkpoint.md" not in assignment_section
    assert "attempt.implement_fix.00/latest-checkpoint.md" in consumed_refs_section
