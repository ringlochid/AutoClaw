from __future__ import annotations

import re

from ..paths import ARCHIVE_ROOT, CURRENT_ROOT, DESIGN_ROOT, DOCS_PUBLIC_ROOT, ROOT
from .markers_design import DESIGN_REQUIRED_MARKERS
from .markers_execution import EXECUTION_FORBIDDEN_MARKERS, EXECUTION_REQUIRED_MARKERS

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
    ARCHIVE_ROOT / "design" / "findings.md",
}

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
    DESIGN_ROOT / "architecture" / "execution-slice-ack-router.md",
    DESIGN_ROOT / "architecture" / "execution-slice-and-lineage-ack.md",
    DESIGN_ROOT / "findings.md",
}

EXECUTION_PROGRAM_WORDING_ROOTS = (
    ROOT / ".agents" / "standards",
    DOCS_PUBLIC_ROOT,
    DESIGN_ROOT,
    CURRENT_ROOT,
)
FORBIDDEN_EXECUTION_PROGRAM_PATTERNS = (
    ("`selected phase`", re.compile(r"\bselected phase\b", re.IGNORECASE)),
    ("`current phase page`", re.compile(r"\bcurrent phase page\b", re.IGNORECASE)),
    ("`phase-local`", re.compile(r"\bphase-local\b", re.IGNORECASE)),
    ("`phase plan`", re.compile(r"\bphase plan\b", re.IGNORECASE)),
    ("`work package`", re.compile(r"\bwork package\b", re.IGNORECASE)),
    ("`work-package`", re.compile(r"\bwork-package\b", re.IGNORECASE)),
    ("`reopen program`", re.compile(r"\breopen program\b", re.IGNORECASE)),
    ("`reopen chain`", re.compile(r"\breopen chain\b", re.IGNORECASE)),
    ("`canon fix`", re.compile(r"\bcanon fix\b", re.IGNORECASE)),
    ("`canon-fix`", re.compile(r"\bcanon-fix\b", re.IGNORECASE)),
)
PUBLIC_DOC_FORBIDDEN_REVIEW_HEADINGS = (
    "## Evidence",
    "## Verification",
)
CURRENT_DOC_CLOSEOUT_HEADINGS = (
    "## Evidence",
    "## Verification",
)

REQUIRED_MARKERS = DESIGN_REQUIRED_MARKERS | EXECUTION_REQUIRED_MARKERS
FORBIDDEN_MARKERS = dict(EXECUTION_FORBIDDEN_MARKERS)
