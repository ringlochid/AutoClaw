from __future__ import annotations

from ..paths import DOCS_ROOT

PHASE0_AUTHORITY_REQUIRED_MARKERS = {
    DOCS_ROOT / "execution" / "gates" / "phase-implementation-prompts.md": [
        "The read list below is the mandatory minimum read set for the selected phase;",
        (
            "The selected current phase page plus "
            "`docs/execution/maps/file-priority-map.md` remain authoritative "
            "for phase-local requirements, reads, and owned surfaces."
        ),
        "Do not treat implementation surfaces as suggestions;",
    ],
}

PHASE0_AUTHORITY_FORBIDDEN_MARKERS = {
    DOCS_ROOT / "execution" / "gates" / "phase-implementation-prompts.md": [
        "The Phase plan, like the pages to read in the plan is only suggested must read files",
        "Other sections like implementation surfaces and files are also only suggestions",
        "you need to proactively change that if that suits",
    ],
}

PHASE0_CURRENT_DOC_REQUIRED_MARKERS = {
    DOCS_ROOT / "current" / "interfaces" / "definition-precedence-and-skill-version-defaults.md": [
        "not part of the shipped default seed path",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definitions-compiler-and-launch.md": [
        "Missing packaged seed files fail the shipped seed path",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definition-registry-and-publish-lifecycle.md": [
        "append a new immutable revision",
    ],
    DOCS_ROOT / "current" / "architecture" / "runtime-control-plane.md": [
        "cancel requests `abort_requested`",
        "keeps the workspace lease held until inactivity is proven",
        "Current dispatch observation/drain facts include:",
        "accepted-boundary waiting is not a persisted control-state enum;",
    ],
}

PHASE0_CURRENT_DOC_FORBIDDEN_MARKERS = {
    DOCS_ROOT / "current" / "interfaces" / "definition-precedence-and-skill-version-defaults.md": [
        "otherwise fall back to the repo-root mirror under `definitions/**`",
        "if packaged seeds are unavailable, fall back to the repo definitions/ mirror",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definitions-compiler-and-launch.md": [
        "falls back to the repo mirror only if the packaged tree is unavailable",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definition-registry-and-publish-lifecycle.md": [
        (
            "The repo-root mirror matters only as an explicit override or as a "
            "fallback when packaged seeds are unavailable."
        ),
    ],
    DOCS_ROOT / "current" / "architecture" / "runtime-control-plane.md": [
        "cancel fences the current dispatch",
        "- accepted-terminal waiting state: `boundary_accepted_waiting_terminal`",
        "- accepted-terminal waiting state: boundary_accepted_waiting_terminal",
    ],
}

PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS = {
    DOCS_ROOT / "execution" / "plans" / "phase-0-3-closeout.md": [
        "summary-only: yes",
    ],
    DOCS_ROOT / "execution" / "evidence" / "phase-0-3-closeout.md": [
        "summary-only: yes",
    ],
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout.md": [
        "summary-only: yes",
    ],
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md": [
        "summary-only: yes",
    ],
}

PHASE0_CLOSEOUT_SUMMARY_FORBIDDEN_MARKERS = {
    DOCS_ROOT / "execution" / "plans" / "phase-0-3-closeout.md": [
        "selected phase: cross-phase",
    ],
    DOCS_ROOT / "execution" / "evidence" / "phase-0-3-closeout.md": [
        "selected phase: cross-phase",
    ],
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout.md": [
        "- pass",
        "no confirmed Phase 0-3 blocker remains open on the integrated tree",
    ],
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md": [
        "`WP6`",
    ],
}

CROSS_PHASE_SUMMARY_SENTINEL_PATHS = {
    DOCS_ROOT / "execution" / "plans" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "evidence" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md",
}

ARTIFACTS_CHANGED_REQUIRED_EVIDENCE_PATHS = {
    DOCS_ROOT / "execution" / "evidence" / "phase-0-closeout-grammar-and-proof.md",
}

SUMMARY_ONLY_REPLACEMENT_REQUIRED_PATHS = {
    DOCS_ROOT / "execution" / "plans" / "phase-0-canon-current-contrast-repair.md",
    DOCS_ROOT / "execution" / "evidence" / "phase-0-canon-current-contrast-repair.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-canon-current-contrast-repair.md",
    DOCS_ROOT / "execution" / "plans" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "evidence" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md",
}

DEFAULT_ROOT_RULES = [
    "If `roots.workspace` is omitted, it defaults to `ensure_task_default`.",
    "If `roots.context` is omitted, it defaults to `ensure_task_default`.",
]

REQUIRED_API_APPENDIX_HEADINGS = [
    "### `DefinitionSummaryListResponse`",
    "### `DefinitionRevisionHistoryResponse`",
    "### `DefinitionRevisionDetailResponse`",
    "### `DefinitionListQuery`",
    "### `DefinitionRevisionHistoryQuery`",
    "### `TaskStartResponse`",
    "### `RuntimeFlowSummaryListResponse`",
    "### `RuntimeFlowRead`",
    "### `RuntimeFlowPauseResponse`",
    "### `RuntimeTaskListQuery`",
    "### `OperatorFlowSnapshotResponse`",
    "### `OperatorFlowTraceResponse`",
    "### `DispatchContextRead`",
    "### `CheckpointWrite`",
    "### `CheckpointRead`",
    "### `BoundaryWrite`",
    "### `BoundaryRead`",
    "### `ParentToolCall`",
    "### `ParentToolSuccess`",
]
