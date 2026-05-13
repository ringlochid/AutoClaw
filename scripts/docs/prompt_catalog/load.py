from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn, Protocol, cast

import yaml

ROOT = Path(__file__).resolve().parents[3]


class ExactPromptBlockAssetLike(Protocol):
    id: str
    asset_path: str
    mirror_doc: str


class RenderedPromptOutputLike(Protocol):
    full_markdown: str
    input_text: str
    instructions_text: str | None


ListExactPromptBlockAssets = Callable[[], tuple[ExactPromptBlockAssetLike, ...]]
GetExactPromptBlockAsset = Callable[[str], ExactPromptBlockAssetLike]
LoadExactPromptBlock = Callable[[str], str]
LiveInstructionBlockInventory = Callable[[], dict[str, dict[str, tuple[str, ...]]]]
PromptFamilyForNodeKind = Callable[[Any], Any]
RenderPromptOutput = Callable[[Any], RenderedPromptOutputLike]


def _load_runtime_attr(module_name: str, attr_name: str) -> Any:
    return getattr(import_module(module_name), attr_name)


_RUNTIME_IMPORT_ERROR: Exception | None = None
prompt_family_for_node_kind: PromptFamilyForNodeKind
get_exact_prompt_block_asset: GetExactPromptBlockAsset
list_exact_prompt_block_assets: ListExactPromptBlockAssets
load_exact_prompt_block: LoadExactPromptBlock
live_instruction_block_inventory: LiveInstructionBlockInventory
render_prompt_bundle: RenderPromptOutput


def _raise_runtime_import_blocker(*_args: Any, **_kwargs: Any) -> NoReturn:
    raise RuntimeError(runtime_import_blocker_message()) from _RUNTIME_IMPORT_ERROR


try:
    runtime_contracts_module = "apps.api.app.runtime.contracts"
    runtime_asset_catalog_module = "apps.api.app.runtime.prompt.asset_catalog"
    runtime_instructions_module = "apps.api.app.runtime.prompt.instructions"
    runtime_bundle_module = "apps.api.app.runtime.prompt.bundle"

    AssignmentProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "AssignmentProjection",
    )
    CheckpointHandoff: Any = _load_runtime_attr(
        runtime_contracts_module,
        "CheckpointHandoff",
    )
    CheckpointKind: Any = _load_runtime_attr(runtime_contracts_module, "CheckpointKind")
    CheckpointOutcome: Any = _load_runtime_attr(
        runtime_contracts_module,
        "CheckpointOutcome",
    )
    CheckpointProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "CheckpointProjection",
    )
    EvidenceKind: Any = _load_runtime_attr(runtime_contracts_module, "EvidenceKind")
    EvidenceRef: Any = _load_runtime_attr(runtime_contracts_module, "EvidenceRef")
    ManifestCurrentContextProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "ManifestCurrentContextProjection",
    )
    ManifestFilesystemRootsProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "ManifestFilesystemRootsProjection",
    )
    ManifestProjection: Any = _load_runtime_attr(runtime_contracts_module, "ManifestProjection")
    ManifestTaskProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "ManifestTaskProjection",
    )
    ManifestWorkflowProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "ManifestWorkflowProjection",
    )
    NodeKind: Any = _load_runtime_attr(runtime_contracts_module, "NodeKind")
    NodeRuntimeFileKind: Any = _load_runtime_attr(
        runtime_contracts_module,
        "NodeRuntimeFileKind",
    )
    NodeRuntimeFileRef: Any = _load_runtime_attr(
        runtime_contracts_module,
        "NodeRuntimeFileRef",
    )
    PROMPT_FAMILY_NODE_KINDS: Any = _load_runtime_attr(
        runtime_contracts_module,
        "PROMPT_FAMILY_NODE_KINDS",
    )
    ProduceRequirement: Any = _load_runtime_attr(
        runtime_contracts_module,
        "ProduceRequirement",
    )
    PromptFamily: Any = _load_runtime_attr(runtime_contracts_module, "PromptFamily")
    PromptRenderRequest: Any = _load_runtime_attr(
        runtime_contracts_module,
        "PromptRenderRequest",
    )
    PromptSendMode: Any = _load_runtime_attr(runtime_contracts_module, "PromptSendMode")
    ResolvedNodeContext: Any = _load_runtime_attr(
        runtime_contracts_module,
        "ResolvedNodeContext",
    )
    StructuralEditPaletteProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "StructuralEditPaletteProjection",
    )
    StructuralEditPolicyProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "StructuralEditPolicyProjection",
    )
    StructuralEditRoleProjection: Any = _load_runtime_attr(
        runtime_contracts_module,
        "StructuralEditRoleProjection",
    )
    prompt_family_for_node_kind = cast(
        PromptFamilyForNodeKind,
        _load_runtime_attr(runtime_contracts_module, "prompt_family_for_node_kind"),
    )
    get_exact_prompt_block_asset = cast(
        GetExactPromptBlockAsset,
        _load_runtime_attr(runtime_asset_catalog_module, "get_exact_prompt_block_asset"),
    )
    list_exact_prompt_block_assets = cast(
        ListExactPromptBlockAssets,
        _load_runtime_attr(runtime_asset_catalog_module, "list_exact_prompt_block_assets"),
    )
    load_exact_prompt_block = cast(
        LoadExactPromptBlock,
        _load_runtime_attr(runtime_asset_catalog_module, "load_exact_prompt_block"),
    )
    live_instruction_block_inventory = cast(
        LiveInstructionBlockInventory,
        _load_runtime_attr(runtime_instructions_module, "live_instruction_block_inventory"),
    )
    render_prompt_bundle = cast(
        RenderPromptOutput,
        _load_runtime_attr(runtime_bundle_module, "render_prompt_bundle"),
    )
except Exception as exc:  # pragma: no cover - exercised in shared-worktree blocker lanes
    _RUNTIME_IMPORT_ERROR = exc
    AssignmentProjection = None
    CheckpointHandoff = None
    CheckpointKind = None
    CheckpointOutcome = None
    CheckpointProjection = None
    EvidenceKind = None
    EvidenceRef = None
    ManifestCurrentContextProjection = None
    ManifestFilesystemRootsProjection = None
    ManifestProjection = None
    ManifestTaskProjection = None
    ManifestWorkflowProjection = None
    NodeKind = None
    NodeRuntimeFileKind = None
    NodeRuntimeFileRef = None
    PROMPT_FAMILY_NODE_KINDS = None
    ProduceRequirement = None
    PromptFamily = None
    PromptRenderRequest = None
    PromptSendMode = None
    ResolvedNodeContext = None
    StructuralEditPaletteProjection = None
    StructuralEditPolicyProjection = None
    StructuralEditRoleProjection = None
    prompt_family_for_node_kind = cast(PromptFamilyForNodeKind, _raise_runtime_import_blocker)
    get_exact_prompt_block_asset = cast(GetExactPromptBlockAsset, _raise_runtime_import_blocker)
    list_exact_prompt_block_assets = cast(ListExactPromptBlockAssets, _raise_runtime_import_blocker)
    load_exact_prompt_block = cast(LoadExactPromptBlock, _raise_runtime_import_blocker)
    live_instruction_block_inventory = cast(
        LiveInstructionBlockInventory,
        _raise_runtime_import_blocker,
    )
    render_prompt_bundle = cast(RenderPromptOutput, _raise_runtime_import_blocker)

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

EXACT_BLOCK_CONSUMPTION_MODES = {
    "live_instruction_block",
    "reference_only",
}

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
        "same attempt remains current and the prebound transport request already carries "
        "`previous_response_id`",
        "renderer compatibility example only; live dispatch opening still defaults "
        "to `full_prompt` on the current tree",
    ],
    "parent_root_dispatch_prompt same_session_continue": [
        "current node: `root`",
        "send mode: `same_session_continue`",
        "same parent/root attempt remains current and the prebound transport request "
        "already carries `previous_response_id`",
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


def runtime_import_blocker_message() -> str:
    if _RUNTIME_IMPORT_ERROR is None:
        raise AssertionError("runtime import blocker requested without an import error")
    return (
        "runtime-backed prompt catalog validation is blocked by a shared-worktree import "
        f"failure: {_RUNTIME_IMPORT_ERROR}"
    )


def runtime_import_failed() -> bool:
    return _RUNTIME_IMPORT_ERROR is not None


def load_catalog() -> dict[str, Any]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("prompt catalog must be a mapping")
    return data
