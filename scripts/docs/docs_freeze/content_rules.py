from __future__ import annotations

from .content_markers_execution import (
    EXECUTION_FORBIDDEN_MARKERS,
    EXECUTION_REQUIRED_MARKERS,
)
from .content_markers_redesign import REDESIGN_REQUIRED_MARKERS
from .paths import DOCS_ROOT, ROOT

LEGACY_HEADING = "# Legacy filename:"
COMPATIBILITY_STATUS = "Status: Compatibility router (search only)"
SEARCH_ONLY_COMPATIBILITY_SECTION = "Search-only compatibility routers"

DELETED_ROUTER_FILENAMES = [
    "artifact-layer-and-packets.md",
    "artifact-packet-bundle-router.md",
    "brief-contract.md",
    "execution-slice-ack-router.md",
    "execution-slice-and-lineage-ack.md",
    "manifest-contract-and-execution-slice.md",
    "manifest-slice-router.md",
    "openclaw-session-and-continuity-contract.md",
    "openclaw-session-and-continuity-router.md",
    "packet-and-release-bundle-router.md",
    "packet-families-and-release-bundles.md",
    "packetized-completion-and-evidence.md",
    "checklists-and-parent-verification.md",
    "local-replan-and-escalation.md",
    "maximal-checklist-projection-and-consumption-flow.md",
    "parent-gate-and-release.md",
    "parent-leaf-review-model.md",
    "provider-selection-and-skills.md",
    "skill-layer-removal-and-provider-skill-execution-rule.md",
    "typed-inputs-and-checklists.md",
    "typed-inputs-and-output-slots.md",
    "why-skill-refs-are-removed.md",
]

DELETED_FILENAME_HISTORY_EXCLUDED_PATHS = {
    DOCS_ROOT / "redesign" / "findings.md",
}

FRONT_DOOR_FORMATTER_PATHS = [
    DOCS_ROOT / "README.md",
    DOCS_ROOT / "execution" / "README.md",
    DOCS_ROOT / "execution" / "gates" / "phase-implementation-prompts.md",
]

FORBIDDEN_ROOT_FILES = [
    ROOT / "AGENT.md",
    ROOT / "STYLE_GUIDE.md",
]

BANNED_PATTERNS = [
    "autoclaw system ",
    "autoclaw tasks start",
    "work order",
    "work-order",
    "review finding packet",
    "review-finding packet",
    "ack_context_manifest",
    "manifest/ack flow",
    "compact_continuation",
    "prompt_assets/__init__.py",
    "align canonical CLI docs to the frozen shipped root-command model",
    "c:/users/",
]

BANNED_PATTERN_EXCLUDED_PATHS = {
    DOCS_ROOT / "redesign" / "architecture" / "execution-slice-ack-router.md",
    DOCS_ROOT / "redesign" / "architecture" / "execution-slice-and-lineage-ack.md",
    DOCS_ROOT / "redesign" / "findings.md",
}

REQUIRED_MARKERS = REDESIGN_REQUIRED_MARKERS | EXECUTION_REQUIRED_MARKERS
FORBIDDEN_MARKERS = dict(EXECUTION_FORBIDDEN_MARKERS)
