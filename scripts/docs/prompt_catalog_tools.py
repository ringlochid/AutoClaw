from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
APPS_API_ROOT = ROOT / "apps" / "api"
if str(APPS_API_ROOT) not in sys.path:
    sys.path.insert(0, str(APPS_API_ROOT))


class ExactPromptBlockAssetLike(Protocol):
    id: str
    asset_path: str
    mirror_doc: str


class RenderedPromptBundleLike(Protocol):
    full_markdown: str
    input_text: str
    instructions_text: str | None


ListExactPromptBlockAssets = Callable[[], tuple[ExactPromptBlockAssetLike, ...]]
GetExactPromptBlockAsset = Callable[[str], ExactPromptBlockAssetLike]
LoadExactPromptBlock = Callable[[str], str]
LiveInstructionBlockInventory = Callable[[], dict[str, dict[str, tuple[str, ...]]]]
PromptFamilyForNodeKind = Callable[[Any], Any]
RenderPromptBundle = Callable[[Any], RenderedPromptBundleLike]


def _load_runtime_attr(module_name: str, attr_name: str) -> Any:
    return getattr(import_module(module_name), attr_name)


AssignmentProjection: Any = _load_runtime_attr("app.runtime.contracts", "AssignmentProjection")
CheckpointHandoff: Any = _load_runtime_attr("app.runtime.contracts", "CheckpointHandoff")
CheckpointKind: Any = _load_runtime_attr("app.runtime.contracts", "CheckpointKind")
CheckpointOutcome: Any = _load_runtime_attr("app.runtime.contracts", "CheckpointOutcome")
CheckpointProjection: Any = _load_runtime_attr("app.runtime.contracts", "CheckpointProjection")
EvidenceKind: Any = _load_runtime_attr("app.runtime.contracts", "EvidenceKind")
EvidenceRef: Any = _load_runtime_attr("app.runtime.contracts", "EvidenceRef")
ManifestCurrentContextProjection: Any = _load_runtime_attr(
    "app.runtime.contracts",
    "ManifestCurrentContextProjection",
)
ManifestFilesystemRootsProjection: Any = _load_runtime_attr(
    "app.runtime.contracts",
    "ManifestFilesystemRootsProjection",
)
ManifestProjection: Any = _load_runtime_attr("app.runtime.contracts", "ManifestProjection")
ManifestTaskProjection: Any = _load_runtime_attr(
    "app.runtime.contracts",
    "ManifestTaskProjection",
)
ManifestWorkflowProjection: Any = _load_runtime_attr(
    "app.runtime.contracts",
    "ManifestWorkflowProjection",
)
NodeKind: Any = _load_runtime_attr("app.runtime.contracts", "NodeKind")
NodeRuntimeFileKind: Any = _load_runtime_attr("app.runtime.contracts", "NodeRuntimeFileKind")
NodeRuntimeFileRef: Any = _load_runtime_attr("app.runtime.contracts", "NodeRuntimeFileRef")
PROMPT_FAMILY_NODE_KINDS: Any = _load_runtime_attr(
    "app.runtime.contracts",
    "PROMPT_FAMILY_NODE_KINDS",
)
ProduceRequirement: Any = _load_runtime_attr("app.runtime.contracts", "ProduceRequirement")
PromptFamily: Any = _load_runtime_attr("app.runtime.contracts", "PromptFamily")
PromptRenderRequest: Any = _load_runtime_attr("app.runtime.contracts", "PromptRenderRequest")
PromptSendMode: Any = _load_runtime_attr("app.runtime.contracts", "PromptSendMode")
RenderedPromptBundle: Any = _load_runtime_attr("app.runtime.contracts", "RenderedPromptBundle")
ResolvedNodeContext: Any = _load_runtime_attr("app.runtime.contracts", "ResolvedNodeContext")
prompt_family_for_node_kind = cast(
    PromptFamilyForNodeKind,
    _load_runtime_attr("app.runtime.contracts", "prompt_family_for_node_kind"),
)
get_exact_prompt_block_asset = cast(
    GetExactPromptBlockAsset,
    _load_runtime_attr("app.runtime.prompt.asset_catalog", "get_exact_prompt_block_asset"),
)
list_exact_prompt_block_assets = cast(
    ListExactPromptBlockAssets,
    _load_runtime_attr("app.runtime.prompt.asset_catalog", "list_exact_prompt_block_assets"),
)
load_exact_prompt_block = cast(
    LoadExactPromptBlock,
    _load_runtime_attr("app.runtime.prompt.asset_catalog", "load_exact_prompt_block"),
)
live_instruction_block_inventory = cast(
    LiveInstructionBlockInventory,
    _load_runtime_attr("app.runtime.prompt.instructions", "live_instruction_block_inventory"),
)
render_prompt_bundle = cast(
    RenderPromptBundle,
    _load_runtime_attr("app.runtime.prompt.bundle", "render_prompt_bundle"),
)

PROMPT_LAYER_ROOT = ROOT / "docs" / "redesign" / "prompt-layer"
PROMPT_ASSET_ROOT = ROOT / "apps" / "api" / "app" / "runtime" / "prompt" / "assets"
PROMPT_ASSET_DISPLAY_ROOT = PROMPT_ASSET_ROOT.relative_to(ROOT).as_posix()
CATALOG_PATH = PROMPT_LAYER_ROOT / "prompt-catalog.yaml"
INVENTORY_PATH = PROMPT_LAYER_ROOT / "generated" / "inventory.md"
EXAMPLES_PATH = PROMPT_LAYER_ROOT / "generated" / "rendered-examples.md"
COMPOSITION_PATH = PROMPT_LAYER_ROOT / "composition-example.md"

SECTION_HEADINGS = {
    "operating_model": "Operating Model",
    "task_identity": "Task Identity",
    "node_purpose": "Node Purpose",
    "current_dispatch": "Current Dispatch",
    "workflow_manifest": "Workflow Manifest",
    "current_assignment": "Current Assignment",
    "latest_checkpoint_context": "Latest Checkpoint Context",
    "consumed_durable_refs": "Consumed Durable Refs",
    "transient_refs": "Transient Refs",
    "task_memory": "Task Memory",
    "allowed_actions_now": "Allowed Actions Now",
    "publication_rule": "Publication Rule",
}

CANONICAL_SEND_MODE_IDS = [
    "full_prompt",
    "same_session_continue",
]

LIVE_PROMPT_SURFACE_PATHS = [
    PROMPT_LAYER_ROOT / "README.md",
    PROMPT_LAYER_ROOT / "INDEX.md",
    PROMPT_LAYER_ROOT / "contract.md",
    PROMPT_LAYER_ROOT / "source-and-sections.md",
    PROMPT_LAYER_ROOT / "field-renderers.md",
    PROMPT_LAYER_ROOT / "render-and-persistence.md",
    PROMPT_LAYER_ROOT / "machine-contract.md",
    PROMPT_LAYER_ROOT / "legality-and-coverage.md",
    PROMPT_LAYER_ROOT / "prompt-resource-usage-appendix.md",
    COMPOSITION_PATH,
    PROMPT_LAYER_ROOT / "generated" / "README.md",
    INVENTORY_PATH,
    EXAMPLES_PATH,
    PROMPT_LAYER_ROOT / "prompt-pack" / "README.md",
    PROMPT_LAYER_ROOT / "prompt-pack" / "runtime-rule-blocks.md",
    PROMPT_LAYER_ROOT / "prompt-pack" / "system-and-provider-block.md",
    PROMPT_LAYER_ROOT / "prompt-pack" / "validation-and-reject-blocks.md",
    CATALOG_PATH,
]

EXPECTED_CLOSURE_MODES = {
    "worker_dispatch_prompt": ["green", "retry", "blocked"],
    "parent_root_dispatch_prompt": ["yield", "green", "blocked"],
}

GENERATED_EXAMPLE_SCENARIOS = {
    "parent_root_dispatch_prompt": [
        "current node: `root`",
        "send mode: `full_prompt`",
        "current lineage: root decides the next bounded child step from current surfaced evidence",
        "representative surfaced refs include a child checkpoint and curated wiki memory",
    ],
    "worker_dispatch_prompt": [
        "current node: `implement_fix`",
        "send mode: `full_prompt`",
        "current lineage: retry created a new attempt on the same assignment",
        "durable reminder: read the prior terminal checkpoint as retry handoff",
        "representative surfaced refs include curated wiki memory and checkpoint hints",
    ],
    "worker_dispatch_prompt same_session_continue": [
        "current node: `implement_fix`",
        "send mode: `same_session_continue`",
        "same attempt remains current, so only the inline static sections are omitted",
        "renderer compatibility example only; live dispatch opening still defaults "
        "to `full_prompt` on the current tree",
    ],
    "parent_root_dispatch_prompt same_session_continue": [
        "current node: `root`",
        "send mode: `same_session_continue`",
        "same parent/root attempt remains current, so only the inline static sections are omitted",
        "renderer compatibility example only; live dispatch opening still defaults "
        "to `full_prompt` on the current tree",
    ],
    "worker_dispatch_prompt blocked-ending sketch": [
        "current node: `implement_fix`",
        "send mode: `full_prompt`",
        "current attempt: still open",
        "current question: should the node end `blocked` or `retry`",
    ],
}


def load_catalog() -> dict[str, Any]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("prompt catalog must be a mapping")
    return data


def _as_string_list(
    value: Any,
    *,
    field_name: str,
    errors: list[str],
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{field_name} must be a list")
        return []
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            errors.append(f"{field_name} entries must be strings")
            return []
        items.append(item)
    if not allow_empty and not items:
        errors.append(f"{field_name} must be non-empty")
    if len(items) != len(set(items)):
        errors.append(f"{field_name} contains duplicates")
    return items


def _owner_doc_paths(owner_docs: list[str]) -> list[Path]:
    return [PROMPT_LAYER_ROOT / owner_doc for owner_doc in owner_docs]


def _extract_markdown_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    capture = False
    in_code_block = False
    collected: list[str] = []
    for line in lines:
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.strip().startswith("```"):
            in_code_block = not in_code_block
        if capture and line.startswith("## ") and not in_code_block:
            break
        if capture:
            collected.append(line)
    if not capture:
        return None
    return "\n".join(collected)


def _extract_first_text_code_block(section: str) -> str | None:
    lines = section.splitlines()
    in_code_block = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_code_block:
            if stripped == "```text":
                in_code_block = True
            continue
        if stripped == "```":
            return "\n".join(collected).strip("\n")
        collected.append(line)
    return None


def _extract_exact_block_text_from_mirror_doc(path: Path, block_id: str) -> str:
    heading = f"## `{block_id}`"
    section = _extract_markdown_section(path.read_text(encoding="utf-8"), heading)
    if section is None:
        raise ValueError(f"missing exact block heading {block_id} in {path}")
    code_block = _extract_first_text_code_block(section)
    if code_block is None:
        raise ValueError(f"missing exact block code fence {block_id} in {path}")
    return code_block


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _sample_manifest(
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


def _example_task_root() -> Path:
    return Path("C:/tasks/task_2026_0042")


def _sample_worker_request(tmp_path: Path, *, send_mode: Any) -> Any:
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
        manifest=_sample_manifest(
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
        ),
        assignment=AssignmentProjection(
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
            ),
            transient_refs=(
                EvidenceRef(
                    kind=EvidenceKind.TRANSIENT,
                    path=tmp_path / "tmp" / "transfers" / "implement_fix" / "repro-commands.txt",
                    description="Optional repro commands from the prior attempt.",
                ),
            ),
            task_memory_search_hints=("auth refresh", "cookie rotation note"),
        ),
        latest_checkpoint=CheckpointProjection(
            checkpoint_kind=CheckpointKind.TERMINAL,
            outcome=CheckpointOutcome.RETRY,
            handoff=CheckpointHandoff(
                summary="Prior attempt fixed the primary path but missed one recovery branch.",
                next_step="Keep the same assignment and repair the missed branch.",
            ),
            task_memory_search_hints=("recovery branch note",),
        ),
    )


def _sample_parent_request(tmp_path: Path, *, send_mode: Any) -> Any:
    return PromptRenderRequest(
        prompt_family=PromptFamily.PARENT_ROOT_DISPATCH,
        send_mode=send_mode,
        task_id="task_2026_0042",
        current_node=ResolvedNodeContext(
            node_key="root",
            node_kind=NodeKind.ROOT,
            node_description="Coordinate the whole flow and decide the next bounded child step.",
            role_key="root_planning_lead",
            role_revision_no=41,
            role_description="Root coordinator for the whole task.",
            role_instruction=(
                "Choose the next bounded child step and close only when release is legal."
            ),
            policy_key="standard-root-planning",
            policy_revision_no=51,
            policy_description="Default root planning and closure behavior.",
            policy_instruction=(
                "Root owns final closure and may use release tools only when current "
                "evidence makes that legal."
            ),
        ),
        manifest=_sample_manifest(
            tmp_path,
            node_key="root",
            owner_node_key="root",
            attempt_id="attempt.root.07",
            latest_relevant_checkpoint_path=(
                tmp_path
                / "_runtime"
                / "attempts"
                / "attempt.investigate_issue.02"
                / "latest-checkpoint.md"
            ),
            current_relevant_paths=(
                NodeRuntimeFileRef(
                    kind=NodeRuntimeFileKind.CHECKPOINT,
                    path=tmp_path
                    / "_runtime"
                    / "attempts"
                    / "attempt.investigate_issue.02"
                    / "latest-checkpoint.md",
                    description="Latest investigation handoff for this root decision.",
                ),
                EvidenceRef(
                    kind=EvidenceKind.WIKI,
                    path=tmp_path / "context" / "wiki" / "cookie-rotation-note.md",
                    description="Curated task-memory note about cookie rotation.",
                ),
            ),
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
                    path=tmp_path
                    / "_runtime"
                    / "attempts"
                    / "attempt.investigate_issue.02"
                    / "latest-checkpoint.md",
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
                next_step="If the handoff is sufficient, emit yield.",
            ),
            task_memory_search_hints=("refresh token expiry branch",),
        ),
    )


def _render_live_prompt_bundles() -> dict[str, RenderedPromptBundleLike]:
    tmp_path = _example_task_root()
    return {
        "worker_dispatch_prompt": render_prompt_bundle(
            _sample_worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
        ),
        "parent_root_dispatch_prompt": render_prompt_bundle(
            _sample_parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
        ),
        "worker_dispatch_prompt same_session_continue": render_prompt_bundle(
            _sample_worker_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
        ),
        "parent_root_dispatch_prompt same_session_continue": render_prompt_bundle(
            _sample_parent_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
        ),
    }


def _render_blocked_ending_sketch() -> str:
    return "\n".join(
        [
            "## Latest Checkpoint Context",
            "- path: "
            "C:/tasks/task_2026_0042/_runtime/attempts/attempt.implement_fix.11/"
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


def _render_generated_example_bodies() -> dict[str, str]:
    bundles = _render_live_prompt_bundles()
    return {
        "parent_root_dispatch_prompt": bundles["parent_root_dispatch_prompt"].full_markdown,
        "worker_dispatch_prompt": bundles["worker_dispatch_prompt"].full_markdown,
        "worker_dispatch_prompt same_session_continue": bundles[
            "worker_dispatch_prompt same_session_continue"
        ].input_text,
        "parent_root_dispatch_prompt same_session_continue": bundles[
            "parent_root_dispatch_prompt same_session_continue"
        ].input_text,
        "worker_dispatch_prompt blocked-ending sketch": _render_blocked_ending_sketch(),
    }


def _validate_live_renderer_alignment(errors: list[str]) -> None:
    bundles = _render_live_prompt_bundles()
    worker_bundle = bundles["worker_dispatch_prompt"]
    parent_bundle = bundles["parent_root_dispatch_prompt"]
    same_session_bundle = bundles["parent_root_dispatch_prompt same_session_continue"]
    system_block = load_exact_prompt_block("autoclaw_system_block_v1")
    provider_block = load_exact_prompt_block("autoclaw_provider_continuity_block_v1")
    split_block = load_exact_prompt_block("autoclaw_parent_worker_split_v1")
    boundary_block = load_exact_prompt_block("runtime_boundary_rule_block_v1")
    worker_legality_block = load_exact_prompt_block("runtime_legality_block_worker_v1")
    parent_legality_block = load_exact_prompt_block("runtime_legality_block_parent_v1")
    wrapper_block = load_exact_prompt_block("autoclaw_same_session_continue_wrapper_v1")

    for bundle, legality_block, name in (
        (worker_bundle, worker_legality_block, "worker"),
        (parent_bundle, parent_legality_block, "parent"),
    ):
        if bundle.instructions_text is None:
            errors.append(f"live {name} instructions_text is unexpectedly null for full_prompt")
            continue
        try:
            normalized_instructions = _normalize_whitespace(bundle.instructions_text)
            positions = [
                normalized_instructions.index(_normalize_whitespace(system_block)),
                normalized_instructions.index(_normalize_whitespace(provider_block)),
                normalized_instructions.index(_normalize_whitespace(split_block)),
                normalized_instructions.index(_normalize_whitespace(boundary_block)),
                normalized_instructions.index(_normalize_whitespace(legality_block)),
            ]
            if positions != sorted(positions):
                errors.append(
                    f"live {name} instructions_text renders exact blocks out of canonical order"
                )
        except ValueError as exc:
            errors.append(f"live {name} instructions_text is missing an exact block: {exc}")

    worker_instructions = worker_bundle.instructions_text
    if worker_instructions is None:
        errors.append("live worker instructions_text is unexpectedly null for full_prompt")
        return
    if "- node description: Repair the bounded auth-refresh defect." not in worker_instructions:
        errors.append("live worker instructions_text is missing current node description guidance")
    if _normalize_whitespace(
        "Before `green`, `retry`, or `blocked`, call `record_checkpoint` with the "
        "terminal handoff for this attempt."
    ) not in _normalize_whitespace(worker_instructions):
        errors.append(
            "live worker instructions_text is missing the terminal checkpoint-before-boundary rule"
        )
    if same_session_bundle.instructions_text is not None:
        errors.append("live same_session_continue instructions_text should be null")
    if not same_session_bundle.input_text.startswith(wrapper_block):
        errors.append("live same_session_continue input is missing the exact wrapper prefix")
    if "## Operating Model" in same_session_bundle.input_text:
        errors.append(
            "live same_session_continue input still includes the static Operating Model section"
        )
    for heading in (
        "## Current Dispatch",
        "## Workflow Manifest",
        "## Current Assignment",
        "## Latest Checkpoint Context",
        "## Consumed Durable Refs",
        "## Transient Refs",
        "## Task Memory",
        "## Allowed Actions Now",
        "## Publication Rule",
    ):
        if heading not in same_session_bundle.input_text:
            errors.append(
                f"live same_session_continue input is missing non-static section `{heading}`"
            )

    assignment_section = worker_bundle.full_markdown.split("## Current Assignment", maxsplit=1)[
        1
    ].split(
        "## Latest Checkpoint Context",
        maxsplit=1,
    )[0]
    subsection: str | None = None
    for line in assignment_section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- criteria:"):
            subsection = "criteria"
            continue
        if stripped.startswith("- consumes:"):
            subsection = "consumes"
            continue
        if stripped.startswith("- produces:"):
            subsection = "produces"
            continue
        if stripped.startswith("- transient_refs:") or stripped.startswith(
            "- task_memory_search_hints:"
        ):
            subsection = None
            continue
        if subsection in {"criteria", "consumes", "produces"} and (
            stripped.startswith("- path:")
            or stripped.startswith("path:")
            or stripped.startswith("- version:")
            or stripped.startswith("version:")
        ):
            errors.append(
                "live Current Assignment still leaks path/version metadata into reduced "
                "durable claims"
            )
            break


def _validate_live_prompt_surface_paths(errors: list[str], *, skip_inventory: bool = False) -> None:
    for path in LIVE_PROMPT_SURFACE_PATHS:
        if skip_inventory and path == INVENTORY_PATH:
            continue
        text = path.read_text(encoding="utf-8")
        if "lock_next/" in text or "lock_next\\" in text:
            errors.append(
                f"{path.relative_to(ROOT)} still routes live prompt semantics to lock_next/"
            )


def _validate_current_assignment_examples(
    errors: list[str], *, skip_generated_examples: bool = False
) -> None:
    example_paths = [PROMPT_LAYER_ROOT / "field-renderers.md", COMPOSITION_PATH]
    if not skip_generated_examples:
        example_paths.insert(1, EXAMPLES_PATH)
    for path in example_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        in_current_assignment = False
        subsection: str | None = None
        criteria_entry_has_kind = False
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped in {"Current Assignment", "## Current Assignment"}:
                in_current_assignment = True
                subsection = None
                criteria_entry_has_kind = False
                continue
            if not in_current_assignment:
                continue
            if stripped in SECTION_HEADINGS.values() and stripped != "Current Assignment":
                in_current_assignment = False
                subsection = None
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("## ") or stripped == "```":
                in_current_assignment = False
                subsection = None
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- criteria:"):
                subsection = "criteria"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- consumes:"):
                subsection = "consumes"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- produces:"):
                subsection = "produces"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- transient_refs:"):
                subsection = "transient_refs"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- task_memory_search_hints:"):
                subsection = "task_memory_search_hints"
                criteria_entry_has_kind = False
                continue
            if subsection == "criteria" and stripped == "- kind: criteria":
                criteria_entry_has_kind = True
                continue
            if (
                subsection == "criteria"
                and (stripped.startswith("- slot:") or stripped.startswith("slot:"))
                and not criteria_entry_has_kind
            ):
                errors.append(
                    f"{path.relative_to(ROOT)} is missing `kind: criteria` in Current Assignment "
                    f"`criteria` at line {line_number}"
                )
            if subsection in {"criteria", "consumes", "produces"} and (
                stripped.startswith("path:") or stripped.startswith("version:")
            ):
                leaked_field = stripped.split(":", 1)[0]
                errors.append(
                    f"{path.relative_to(ROOT)} leaks `{leaked_field}` into "
                    f"Current Assignment `{subsection}` at line {line_number}"
                )


def _validate_assignment_and_checkpoint_path_lines(
    errors: list[str], *, skip_generated_examples: bool = False
) -> None:
    section_specs = [
        (PROMPT_LAYER_ROOT / "source-and-sections.md", "Current Assignment", "- path:"),
        (PROMPT_LAYER_ROOT / "field-renderers.md", "Current Assignment", "- path:"),
        (COMPOSITION_PATH, "Current Assignment", "- path:"),
        (PROMPT_LAYER_ROOT / "field-renderers.md", "Latest Checkpoint Context", "- path:"),
        (COMPOSITION_PATH, "Latest Checkpoint Context", "- path:"),
    ]
    if not skip_generated_examples:
        section_specs.insert(2, (EXAMPLES_PATH, "Current Assignment", "- path:"))
        section_specs.insert(5, (EXAMPLES_PATH, "Latest Checkpoint Context", "- path:"))
    for path, section_heading, required_prefix in section_specs:
        lines = path.read_text(encoding="utf-8").splitlines()
        in_section = False
        saw_required_line = False
        saw_section = False
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped in {section_heading, f"## {section_heading}"}:
                saw_section = True
                in_section = True
                saw_required_line = False
                continue
            if not in_section:
                continue
            if stripped in SECTION_HEADINGS.values() and stripped != section_heading:
                if not saw_required_line:
                    errors.append(
                        f"{path.relative_to(ROOT)} section `{section_heading}` is "
                        f"missing a `{required_prefix}` line before line {line_number}"
                    )
                in_section = False
                continue
            if stripped.startswith("## ") or stripped == "```":
                if not saw_required_line:
                    errors.append(
                        f"{path.relative_to(ROOT)} section `{section_heading}` is "
                        f"missing a `{required_prefix}` line before line {line_number}"
                    )
                in_section = False
                continue
            if stripped.startswith(required_prefix):
                saw_required_line = True
        if saw_section and in_section and not saw_required_line:
            errors.append(
                f"{path.relative_to(ROOT)} section `{section_heading}` is missing a "
                f"`{required_prefix}` line"
            )


def _validate_exact_block_asset_mirrors(errors: list[str]) -> None:
    for asset in list_exact_prompt_block_assets():
        mirror_path = PROMPT_LAYER_ROOT / asset.mirror_doc
        if not mirror_path.exists():
            errors.append(
                f"missing mirror doc for exact prompt block `{asset.id}`: {asset.mirror_doc}"
            )
            continue
        try:
            mirror_text = _extract_exact_block_text_from_mirror_doc(mirror_path, asset.id)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        asset_text = load_exact_prompt_block(asset.id)
        if mirror_text != asset_text:
            errors.append(
                "exact prompt block mirror drift: "
                f"{mirror_path.relative_to(ROOT)} no longer matches "
                f"{PROMPT_ASSET_ROOT.relative_to(ROOT) / asset.asset_path}"
            )


def _validate_live_prompt_family_node_kind_alignment(
    data: dict[str, Any],
    errors: list[str],
) -> None:
    live_mapping = PROMPT_FAMILY_NODE_KINDS
    if not isinstance(live_mapping, dict):
        errors.append("live prompt family/node kind mapping must be a mapping")
        return

    catalog_mapping: dict[str, tuple[str, ...]] = {}
    for family in data.get("prompt_families", []):
        if not isinstance(family, dict):
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            continue
        catalog_mapping[family_id] = tuple(
            _as_string_list(
                family.get("node_kinds"),
                field_name=f"{family_id}.node_kinds",
                errors=errors,
            )
        )

    normalized_live_mapping: dict[str, tuple[str, ...]] = {}
    for prompt_family, node_kinds in live_mapping.items():
        family_id = getattr(prompt_family, "value", None)
        if not isinstance(family_id, str):
            errors.append("live prompt family/node kind mapping contains a non-enum family key")
            continue
        if not isinstance(node_kinds, tuple):
            if isinstance(node_kinds, list):
                node_kinds = tuple(node_kinds)
            else:
                errors.append(
                    f"live prompt family/node kind mapping for `{family_id}` must be a sequence"
                )
                continue
        normalized_node_kinds: list[str] = []
        for node_kind in node_kinds:
            node_kind_id = getattr(node_kind, "value", None)
            if not isinstance(node_kind_id, str):
                errors.append(
                    f"live prompt family/node kind mapping for `{family_id}` contains "
                    "a non-enum node kind"
                )
                normalized_node_kinds = []
                break
            normalized_node_kinds.append(node_kind_id)
        if not normalized_node_kinds:
            continue
        normalized_live_mapping[family_id] = tuple(normalized_node_kinds)

    for family_id, live_node_kinds in normalized_live_mapping.items():
        catalog_node_kinds = catalog_mapping.get(family_id)
        if catalog_node_kinds is None:
            errors.append(
                f"prompt catalog is missing live prompt family `{family_id}` for node-kind audit"
            )
            continue
        if catalog_node_kinds != live_node_kinds:
            errors.append(
                f"{family_id}.node_kinds must match live runtime mapping "
                f"{list(live_node_kinds)}, found {list(catalog_node_kinds)}"
            )

    for node_kind in NodeKind:
        node_kind_id = getattr(node_kind, "value", None)
        if not isinstance(node_kind_id, str):
            errors.append("live NodeKind enum contains a non-string value")
            continue
        live_family = prompt_family_for_node_kind(node_kind)
        live_family_id = getattr(live_family, "value", None)
        if not isinstance(live_family_id, str):
            errors.append(
                f"live prompt_family_for_node_kind returned a non-enum family for `{node_kind_id}`"
            )
            continue
        catalog_family_ids = sorted(
            family_id
            for family_id, node_kinds in catalog_mapping.items()
            if node_kind_id in node_kinds
        )
        if catalog_family_ids != [live_family_id]:
            errors.append(
                f"catalog node-kind routing drift for `{node_kind_id}`: expected only "
                f"`{live_family_id}`, found {catalog_family_ids or ['<none>']}"
            )


def _validate_live_instruction_block_consumption(
    data: dict[str, Any],
    errors: list[str],
) -> None:
    inventory = live_instruction_block_inventory()
    if not isinstance(inventory, dict):
        errors.append("live instruction block inventory must be a mapping")
        return

    for family in data.get("prompt_families", []):
        if not isinstance(family, dict):
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            continue
        family_inventory = inventory.get(family_id)
        if not isinstance(family_inventory, dict):
            errors.append(f"live instruction block inventory is missing family `{family_id}`")
            continue

        consumed_block_ids: set[str] = set()
        for send_mode_id in CANONICAL_SEND_MODE_IDS:
            raw_block_ids = family_inventory.get(send_mode_id)
            if not isinstance(raw_block_ids, tuple):
                if isinstance(raw_block_ids, list):
                    raw_block_ids = tuple(raw_block_ids)
                else:
                    errors.append(
                        "live instruction block inventory must expose "
                        f"`{family_id}` / `{send_mode_id}` as a sequence of block ids"
                    )
                    continue
            invalid_block_ids = [
                block_id for block_id in raw_block_ids if not isinstance(block_id, str)
            ]
            if invalid_block_ids:
                errors.append(
                    "live instruction block inventory contains non-string block ids for "
                    f"`{family_id}` / `{send_mode_id}`"
                )
                continue
            consumed_block_ids.update(raw_block_ids)

        family_exact_blocks = family.get("exact_blocks")
        if not isinstance(family_exact_blocks, dict):
            continue

        listed_block_ids: set[str] = set()
        for block_bucket, block_ids in family_exact_blocks.items():
            if not isinstance(block_bucket, str):
                continue
            listed_block_ids.update(
                _as_string_list(
                    block_ids,
                    field_name=f"{family_id}.exact_blocks.{block_bucket}",
                    errors=errors,
                    allow_empty=True,
                )
            )

        unconsumed_block_ids = sorted(listed_block_ids - consumed_block_ids)
        if not unconsumed_block_ids:
            continue
        consumed_display = ", ".join(sorted(consumed_block_ids)) or "<none>"
        errors.append(
            f"{family_id}.exact_blocks lists blocks with no live instruction assembly path: "
            f"{', '.join(unconsumed_block_ids)}; live instruction blocks: {consumed_display}"
        )


def _validate_generated_example_parity(errors: list[str]) -> None:
    rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
    for heading, expected_text in _render_generated_example_bodies().items():
        section = _extract_markdown_section(rendered_examples_text, f"## `{heading}`")
        if section is None:
            errors.append(f"generated/rendered-examples.md is missing section `## `{heading}``")
            continue
        actual_text = _extract_first_text_code_block(section)
        if actual_text is None:
            errors.append(
                "generated/rendered-examples.md section "
                f"`## `{heading}`` is missing a text code block"
            )
            continue
        if actual_text.strip() != expected_text.strip():
            errors.append(
                f"generated/rendered-examples.md drifted from live renderer output for `{heading}`"
            )


def _validate_same_session_examples(
    data: dict[str, Any], errors: list[str], *, skip_generated_examples: bool = False
) -> None:
    dynamic_headings = [
        f"## {SECTION_HEADINGS[section_id]}"
        for section_id in data.get("section_order", [])
        if section_id not in data.get("static_sections", [])
    ]
    if not skip_generated_examples:
        rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
        same_session_examples = [
            example
            for example in data.get("generated_examples", [])
            if isinstance(example, dict) and example.get("send_mode") == "same_session_continue"
        ]
        for example in same_session_examples:
            heading = example.get("rendered_heading")
            if not isinstance(heading, str):
                continue
            section = _extract_markdown_section(rendered_examples_text, f"## `{heading}`")
            if section is None:
                errors.append(f"generated/rendered-examples.md is missing section `## `{heading}``")
                continue
            for heading_text in dynamic_headings:
                if heading_text not in section:
                    errors.append(
                        "generated/rendered-examples.md same-session example "
                        f"`{heading}` is missing non-static section `{heading_text}`"
                    )

    composition_text = COMPOSITION_PATH.read_text(encoding="utf-8")
    composition_headings = [
        "## Exact assembly: `worker_dispatch_prompt` `same_session_continue`",
        "## Exact assembly: `parent_root_dispatch_prompt` `same_session_continue`",
    ]
    for heading in composition_headings:
        section = _extract_markdown_section(composition_text, heading)
        if section is None:
            errors.append(f"composition-example.md is missing section `{heading}`")
            continue
        for heading_text in dynamic_headings:
            if heading_text not in section:
                errors.append(
                    "composition-example.md same-session example "
                    f"`{heading}` is missing non-static section `{heading_text}`"
                )


def _validate_catalog(data: dict[str, Any], *, skip_inventory_checks: bool = False) -> list[str]:
    errors: list[str] = []

    if data.get("version") != 1:
        errors.append("catalog version must be 1")

    owner_docs = _as_string_list(data.get("owner_docs"), field_name="owner_docs", errors=errors)
    for owner_doc_path in _owner_doc_paths(owner_docs):
        if not owner_doc_path.exists():
            errors.append(f"owner doc is missing: {owner_doc_path.relative_to(ROOT)}")

    section_order = _as_string_list(
        data.get("section_order"),
        field_name="section_order",
        errors=errors,
    )
    unknown_sections = [section for section in section_order if section not in SECTION_HEADINGS]
    if unknown_sections:
        errors.append(f"unknown section ids: {', '.join(unknown_sections)}")

    static_sections = _as_string_list(
        data.get("static_sections"),
        field_name="static_sections",
        errors=errors,
        allow_empty=True,
    )
    for section in static_sections:
        if section not in section_order:
            errors.append(f"static section `{section}` is not in section_order")

    send_modes = data.get("send_modes")
    if not isinstance(send_modes, list) or not send_modes:
        errors.append("send_modes must be a non-empty list of mappings")
        send_modes = []
    send_mode_ids: list[str] = []
    for index, send_mode in enumerate(send_modes):
        prefix = f"send_modes[{index}]"
        if not isinstance(send_mode, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        send_mode_id = send_mode.get("id")
        if not isinstance(send_mode_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        send_mode_ids.append(send_mode_id)
    if len(send_mode_ids) != len(set(send_mode_ids)):
        errors.append("send mode ids contain duplicates")
    if send_mode_ids != CANONICAL_SEND_MODE_IDS:
        errors.append("send mode ids must be exactly [full_prompt, same_session_continue] in order")

    exact_blocks = data.get("exact_blocks")
    if not isinstance(exact_blocks, list) or not exact_blocks:
        errors.append("exact_blocks must be a non-empty list")
        exact_blocks = []
    exact_prompt_assets = {asset.id: asset for asset in list_exact_prompt_block_assets()}
    exact_block_ids: list[str] = []
    for index, block in enumerate(exact_blocks):
        prefix = f"exact_blocks[{index}]"
        if not isinstance(block, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        block_id = block.get("id")
        owner_file = block.get("owner_file")
        role = block.get("role")
        purpose = block.get("purpose")
        if not isinstance(block_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        exact_block_ids.append(block_id)
        if not isinstance(owner_file, str):
            errors.append(f"{prefix}.owner_file must be a string")
        else:
            owner_path = PROMPT_LAYER_ROOT / owner_file
            if not owner_path.exists():
                errors.append(f"{prefix}.owner_file is missing: {owner_path.relative_to(ROOT)}")
            elif block_id not in owner_path.read_text(encoding="utf-8"):
                errors.append(f"{prefix}.owner_file does not mention `{block_id}`")
        asset = exact_prompt_assets.get(block_id)
        if asset is None:
            errors.append(
                f"{prefix}.id is missing from app-owned prompt assets under "
                f"{PROMPT_ASSET_ROOT.relative_to(ROOT)}"
            )
        elif owner_file != asset.mirror_doc:
            errors.append(
                f"{prefix}.owner_file must match packaged prompt asset mirror doc "
                f"`{asset.mirror_doc}`"
            )
        if not isinstance(role, str):
            errors.append(f"{prefix}.role must be a string")
        if not isinstance(purpose, str):
            errors.append(f"{prefix}.purpose must be a string")
    if len(exact_block_ids) != len(set(exact_block_ids)):
        errors.append("exact block ids contain duplicates")
    extra_asset_ids = sorted(set(exact_prompt_assets) - set(exact_block_ids))
    if extra_asset_ids:
        errors.append(
            "app-owned prompt assets are missing from prompt-catalog.yaml exact_blocks: "
            + ", ".join(extra_asset_ids)
        )

    generated_artifacts = data.get("generated_artifacts")
    if not isinstance(generated_artifacts, list) or not generated_artifacts:
        errors.append("generated_artifacts must be a non-empty list")
        generated_artifacts = []
    generated_artifact_ids: list[str] = []
    for index, artifact in enumerate(generated_artifacts):
        prefix = f"generated_artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        artifact_id = artifact.get("id")
        artifact_path = artifact.get("path")
        if not isinstance(artifact_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        generated_artifact_ids.append(artifact_id)
        if not isinstance(artifact_path, str):
            errors.append(f"{prefix}.path must be a string")
        else:
            resolved_path = PROMPT_LAYER_ROOT / artifact_path
            if not resolved_path.exists():
                errors.append(f"{prefix}.path is missing: {resolved_path.relative_to(ROOT)}")
    if len(generated_artifact_ids) != len(set(generated_artifact_ids)):
        errors.append("generated artifact ids contain duplicates")

    generated_examples = data.get("generated_examples")
    if not isinstance(generated_examples, list) or not generated_examples:
        errors.append("generated_examples must be a non-empty list")
        generated_examples = []
    generated_example_ids: list[str] = []
    generated_example_records: list[dict[str, str]] = []
    for index, example in enumerate(generated_examples):
        prefix = f"generated_examples[{index}]"
        if not isinstance(example, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        example_id = example.get("id")
        family = example.get("family")
        send_mode = example.get("send_mode")
        rendered_heading = example.get("rendered_heading")
        source_file = example.get("source_file")
        if not isinstance(example_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        generated_example_ids.append(example_id)
        if not isinstance(rendered_heading, str):
            errors.append(f"{prefix}.rendered_heading must be a string")
            rendered_heading = ""
        if not isinstance(family, str):
            errors.append(f"{prefix}.family must be a string")
            family = ""
        if not isinstance(send_mode, str):
            errors.append(f"{prefix}.send_mode must be a string")
            send_mode = ""
        elif send_mode not in send_mode_ids:
            errors.append(f"{prefix}.send_mode uses unknown send mode `{send_mode}`")
        if not isinstance(source_file, str):
            errors.append(f"{prefix}.source_file must be a string")
        else:
            source_path = PROMPT_LAYER_ROOT / source_file
            if not source_path.exists():
                errors.append(f"{prefix}.source_file is missing: {source_path.relative_to(ROOT)}")
        generated_example_records.append(
            {
                "id": example_id,
                "family": family,
                "send_mode": send_mode,
                "rendered_heading": rendered_heading,
            }
        )
    if len(generated_example_ids) != len(set(generated_example_ids)):
        errors.append("generated example ids contain duplicates")

    validation_references = data.get("validation_references")
    if not isinstance(validation_references, list) or not validation_references:
        errors.append("validation_references must be a non-empty list")
        validation_references = []
    validation_reference_ids: list[str] = []
    for index, reference in enumerate(validation_references):
        prefix = f"validation_references[{index}]"
        if not isinstance(reference, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        reference_id = reference.get("id")
        owner_ref_docs = reference.get("owner_docs")
        if not isinstance(reference_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        validation_reference_ids.append(reference_id)
        owner_doc_list = _as_string_list(
            owner_ref_docs,
            field_name=f"{prefix}.owner_docs",
            errors=errors,
            allow_empty=False,
        )
        for owner_doc in owner_doc_list:
            owner_path = (PROMPT_LAYER_ROOT / owner_doc).resolve()
            if not owner_path.exists():
                errors.append(
                    f"{prefix}.owner_docs entry is missing: {owner_path.relative_to(ROOT)}"
                )
    if len(validation_reference_ids) != len(set(validation_reference_ids)):
        errors.append("validation reference ids contain duplicates")

    prompt_families = data.get("prompt_families")
    if not isinstance(prompt_families, list) or not prompt_families:
        errors.append("prompt_families must be a non-empty list")
        prompt_families = []
    family_ids: list[str] = []
    for index, family in enumerate(prompt_families):
        prefix = f"prompt_families[{index}]"
        if not isinstance(family, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        family_ids.append(family_id)

        _as_string_list(
            family.get("node_kinds"),
            field_name=f"{family_id}.node_kinds",
            errors=errors,
        )

        allowed_send_modes = _as_string_list(
            family.get("allowed_send_modes"),
            field_name=f"{family_id}.allowed_send_modes",
            errors=errors,
        )
        for send_mode in allowed_send_modes:
            if send_mode not in send_mode_ids:
                errors.append(
                    f"{family_id}.allowed_send_modes contains unknown send mode `{send_mode}`"
                )

        required_sections = _as_string_list(
            family.get("required_sections"),
            field_name=f"{family_id}.required_sections",
            errors=errors,
        )
        for section in required_sections:
            if section not in section_order:
                errors.append(f"{family_id}.required_sections contains unknown section `{section}`")

        conditional_sections = family.get("conditionally_required_sections")
        if not isinstance(conditional_sections, list):
            errors.append(f"{family_id}.conditionally_required_sections must be a list")
            conditional_sections = []
        for conditional_index, conditional in enumerate(conditional_sections):
            conditional_prefix = f"{family_id}.conditionally_required_sections[{conditional_index}]"
            if not isinstance(conditional, dict):
                errors.append(f"{conditional_prefix} must be a mapping")
                continue
            conditional_section = conditional.get("section")
            when = conditional.get("when")
            if not isinstance(conditional_section, str):
                errors.append(f"{conditional_prefix}.section must be a string")
            elif conditional_section not in section_order:
                errors.append(
                    f"{conditional_prefix}.section is not in section_order: {conditional_section}"
                )
            if not isinstance(when, str):
                errors.append(f"{conditional_prefix}.when must be a string")

        _as_string_list(
            family.get("closure_modes"),
            field_name=f"{family_id}.closure_modes",
            errors=errors,
        )
        expected_closure_modes = EXPECTED_CLOSURE_MODES.get(family_id)
        if expected_closure_modes is not None:
            actual_closure_modes = family.get("closure_modes")
            if actual_closure_modes != expected_closure_modes:
                errors.append(
                    f"{family_id}.closure_modes must be exactly "
                    f"{expected_closure_modes}, found {actual_closure_modes}"
                )

        family_exact_blocks = family.get("exact_blocks")
        if not isinstance(family_exact_blocks, dict):
            errors.append(f"{family_id}.exact_blocks must be a mapping")
        else:
            for block_bucket, block_ids in family_exact_blocks.items():
                normalized_ids = _as_string_list(
                    block_ids,
                    field_name=f"{family_id}.exact_blocks.{block_bucket}",
                    errors=errors,
                )
                for block_id in normalized_ids:
                    if block_id not in exact_block_ids:
                        errors.append(
                            f"{family_id}.exact_blocks.{block_bucket} "
                            f"references unknown block `{block_id}`"
                        )

        family_generated_examples = _as_string_list(
            family.get("generated_examples"),
            field_name=f"{family_id}.generated_examples",
            errors=errors,
        )
        for example_id in family_generated_examples:
            if example_id not in generated_example_ids:
                errors.append(
                    f"{family_id}.generated_examples references unknown example `{example_id}`"
                )

    if len(family_ids) != len(set(family_ids)):
        errors.append("prompt family ids contain duplicates")
    if sorted(family_ids) != ["parent_root_dispatch_prompt", "worker_dispatch_prompt"]:
        errors.append(
            "prompt family ids must be exactly "
            "parent_root_dispatch_prompt and worker_dispatch_prompt"
        )

    rules = _as_string_list(data.get("rules"), field_name="rules", errors=errors)
    validator_checks = _as_string_list(
        data.get("validator_checks"),
        field_name="validator_checks",
        errors=errors,
    )
    if (
        rules
        and "same_session_continue is a transport-only optimization inside the same attempt"
        not in rules
    ):
        errors.append("rules is missing the same_session_continue transport-only rule")
    if (
        validator_checks
        and "freeze exactly two canonical dispatch prompt families" not in validator_checks
    ):
        errors.append("validator_checks is missing the canonical prompt-family freeze rule")

    if not skip_inventory_checks:
        inventory_text = INVENTORY_PATH.read_text(encoding="utf-8")
        for family_id in family_ids:
            if family_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing prompt family `{family_id}`")
        for send_mode_id in send_mode_ids:
            if send_mode_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing send mode `{send_mode_id}`")
        for block_id in exact_block_ids:
            if block_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing exact block `{block_id}`")
        for artifact in generated_artifacts:
            artifact_id = artifact.get("id")
            if isinstance(artifact_id, str) and artifact_id not in inventory_text:
                errors.append(
                    f"generated/inventory.md is missing generated artifact `{artifact_id}`"
                )
        for example_id in generated_example_ids:
            if example_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing generated example `{example_id}`")

    if not skip_inventory_checks:
        rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
        for example in generated_example_records:
            heading = example["rendered_heading"]
            family = example["family"]
            send_mode = example["send_mode"]
            if heading and heading in rendered_examples_text:
                continue
            if family and family not in rendered_examples_text:
                errors.append(f"generated/rendered-examples.md is missing prompt family `{family}`")
                continue
            if send_mode and send_mode not in rendered_examples_text:
                errors.append(f"generated/rendered-examples.md is missing send mode `{send_mode}`")

    _validate_live_prompt_surface_paths(errors, skip_inventory=skip_inventory_checks)
    _validate_exact_block_asset_mirrors(errors)
    _validate_live_prompt_family_node_kind_alignment(data, errors)
    _validate_live_instruction_block_consumption(data, errors)
    _validate_current_assignment_examples(errors, skip_generated_examples=skip_inventory_checks)
    _validate_assignment_and_checkpoint_path_lines(
        errors, skip_generated_examples=skip_inventory_checks
    )
    _validate_same_session_examples(data, errors, skip_generated_examples=skip_inventory_checks)
    _validate_live_renderer_alignment(errors)
    if not skip_inventory_checks:
        _validate_generated_example_parity(errors)

    return errors


def _render_inventory_md(data: dict[str, Any]) -> str:
    send_mode_ids = [send_mode["id"] for send_mode in data["send_modes"]]
    lines = [
        "# Generated Prompt Inventory",
        "",
        "Status: Generated reference",
        "",
        "This page inventories the current generated prompt contract surfaces.",
        "Static exact blocks are shipped from app-owned assets under "
        f"`{PROMPT_ASSET_DISPLAY_ROOT}/`, while the prompt-pack docs remain "
        "human-readable mirrors.",
        "",
        "## Canonical Section Order",
        "",
    ]
    for index, section in enumerate(data["section_order"], start=1):
        lines.append(f"{index}. `{section}`")
    lines.extend(["", "## Static Continuation Sections", ""])
    for section in data["static_sections"]:
        lines.append(f"- `{section}`")
    lines.extend(["", "## Canonical Prompt Families", ""])
    for family in data["prompt_families"]:
        lines.append(f"- `{family['id']}`")
    lines.extend(["", "## Canonical Send Modes", ""])
    for send_mode_id in send_mode_ids:
        lines.append(f"- `{send_mode_id}`")
    lines.extend(
        [
            "",
            "Current generated same-session examples are renderer compatibility examples only.",
            "They are not proof that the shipped launch or continue paths currently select "
            "`same_session_continue` automatically.",
        ]
    )
    lines.extend(["", "## Exact Block Registry", ""])
    for block in data["exact_blocks"]:
        asset = get_exact_prompt_block_asset(block["id"])
        lines.append(f"- `{block['id']}`")
        lines.append(f"  - asset: `{PROMPT_ASSET_DISPLAY_ROOT}/{asset.asset_path}`")
        lines.append(f"  - mirror doc: `{block['owner_file']}`")
        lines.append(f"  - role: `{block['role']}`")
    lines.extend(["", "## Generated Artifact Registry", ""])
    for artifact in data["generated_artifacts"]:
        lines.append(f"- `{artifact['id']}`")
        lines.append(f"  - file: `{artifact['path']}`")
    lines.extend(["", "## Generated Example Registry", ""])
    for example in data["generated_examples"]:
        lines.append(f"- `{example['id']}`")
        lines.append(f"  - rendered heading: `{example['rendered_heading']}`")
        lines.append(f"  - family: `{example['family']}`")
        lines.append(f"  - send mode: `{example['send_mode']}`")
    return "\n".join(lines).rstrip() + "\n"


def _render_generated_examples_md(data: dict[str, Any]) -> str:
    rendered_examples = _render_generated_example_bodies()
    lines = [
        "# Generated Rendered Prompt Examples",
        "",
        "Status: Generated reference",
        "",
        "This page is generated from app-owned prompt assets under "
        f"`{PROMPT_ASSET_DISPLAY_ROOT}/` plus live `render_prompt_bundle()` "
        "output.",
        "",
        "The `same_session_continue` examples below are renderer and persisted-request "
        "compatibility examples only. They do not prove that the shipped launch or "
        "continue paths currently open real dispatches with that send mode.",
        "",
        "If this page drifts from the runtime renderer, regenerate it from "
        "`scripts/docs/prompt_catalog_tools.py generate` and then rerun validation.",
        "",
    ]
    for example in data["generated_examples"]:
        heading = example["rendered_heading"]
        lines.extend([f"## `{heading}`", "", "Scenario:", ""])
        for scenario_line in GENERATED_EXAMPLE_SCENARIOS.get(heading, []):
            lines.append(f"- {scenario_line}")
        lines.extend(
            [
                "",
                "```text",
                rendered_examples[heading],
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_inventory_debug(data: dict[str, Any]) -> str:
    send_mode_ids = [
        send_mode["id"]
        for send_mode in data.get("send_modes", [])
        if isinstance(send_mode, dict) and isinstance(send_mode.get("id"), str)
    ]
    lines = [
        "Prompt catalog inventory:",
        f"- version: {data.get('version')}",
        f"- owner docs: {len(data.get('owner_docs', []))}",
        f"- sections: {len(data.get('section_order', []))}",
    ]
    for section in data.get("section_order", []):
        lines.append(f"  - section: {section} -> {SECTION_HEADINGS.get(section, 'UNKNOWN')}")
    lines.append(f"- static sections: {len(data.get('static_sections', []))}")
    for section in data.get("static_sections", []):
        lines.append(f"  - {section}")
    lines.append(f"- send modes: {', '.join(send_mode_ids)}")
    lines.append(f"- exact blocks: {len(data.get('exact_blocks', []))}")
    for block in data.get("exact_blocks", []):
        if isinstance(block, dict):
            asset_path = "UNKNOWN"
            block_id = block.get("id")
            if isinstance(block_id, str):
                try:
                    asset_path = get_exact_prompt_block_asset(block_id).asset_path
                except ValueError:
                    asset_path = "MISSING"
            lines.append(
                f"  - {block.get('id')} | asset={asset_path} | owner={block.get('owner_file')} | "
                f"role={block.get('role')}"
            )
    lines.append(f"- prompt families: {len(data.get('prompt_families', []))}")
    for family in data.get("prompt_families", []):
        if isinstance(family, dict):
            lines.append(
                "  - "
                f"{family.get('id')} | "
                f"send_modes={','.join(family.get('allowed_send_modes', []))} | "
                f"required_sections={','.join(family.get('required_sections', []))}"
            )
    lines.append(f"- generated artifacts: {len(data.get('generated_artifacts', []))}")
    lines.append(f"- generated examples: {len(data.get('generated_examples', []))}")
    lines.append(f"- validation references: {len(data.get('validation_references', []))}")
    return "\n".join(lines).rstrip() + "\n"


def generate() -> None:
    data = load_catalog()
    errors = _validate_catalog(data, skip_inventory_checks=True)
    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    INVENTORY_PATH.write_text(_render_inventory_md(data), encoding="utf-8")
    EXAMPLES_PATH.write_text(_render_generated_examples_md(data), encoding="utf-8")


def validate() -> int:
    data = load_catalog()
    errors = _validate_catalog(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Prompt catalog validation passed.")
    return 0


def inventory() -> int:
    data = load_catalog()
    print(_render_inventory_debug(data), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate", "validate", "inventory"])
    args = parser.parse_args(argv)
    if args.command == "generate":
        generate()
        return 0
    if args.command == "inventory":
        return inventory()
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
