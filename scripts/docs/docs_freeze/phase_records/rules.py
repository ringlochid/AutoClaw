from __future__ import annotations

from pathlib import Path

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
    DOCS_ROOT / "current" / "README.md": [
        "does not compete with redesign canon",
    ],
    DOCS_ROOT / "current" / "architecture" / "README.md": [
        "It is current-behavior contrast only, not redesign canon.",
    ],
    DOCS_ROOT / "current" / "architecture" / "manifest-projection-and-acknowledgement.md": [
        "Older docs taught manifest-acknowledgement vocabulary",
    ],
    DOCS_ROOT / "current" / "architecture" / "openclaw-and-bridge-plugin.md": [
        "manifest and checkpoint lineage remain controller-owned prompt and runtime truth",
    ],
    DOCS_ROOT
    / "current"
    / "architecture"
    / "runtime-read-models-and-operator-surfaces.md": [
        "Current code also does not expose a dedicated manifest-ack query surface",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definition-precedence-and-skill-version-defaults.md": [
        "not part of the shipped default seed path",
    ],
    DOCS_ROOT / "current" / "interfaces" / "cli-surface-and-config-precedence.md": [
        "### Init and local setup",
    ],
    DOCS_ROOT
    / "current"
    / "interfaces"
    / "current-definition-bootstrap-and-task-upload.md": [
        "It does not define a canonical dispatch phase",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definitions-compiler-and-launch.md": [
        "Missing packaged seed files fail the shipped seed path",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definition-registry-and-publish-lifecycle.md": [
        "append a new immutable revision",
    ],
    DOCS_ROOT / "current" / "operations" / "inspect-approvals-and-watchdog.md": [
        "accepted first-dispatch turns that have not produced committed first progress yet",
    ],
    DOCS_ROOT / "current" / "architecture" / "runtime-control-plane.md": [
        "cancel requests `abort_requested`",
        "keeps the workspace lease held until inactivity is proven",
        "Current dispatch observation/drain facts include:",
        "accepted-boundary waiting is not a persisted control-state enum;",
    ],
}

PHASE0_CURRENT_DOC_FORBIDDEN_MARKERS = {
    DOCS_ROOT / "current" / "architecture" / "manifest-projection-and-acknowledgement.md": [
        "records that the older manifest-acknowledgement flow no longer ships in the current tree",
    ],
    DOCS_ROOT / "current" / "architecture" / "openclaw-and-bridge-plugin.md": [
        "manifest acknowledgement and checkpoint lineage",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definition-precedence-and-skill-version-defaults.md": [
        "otherwise fall back to the repo-root mirror under `definitions/**`",
        "if packaged seeds are unavailable, fall back to the repo definitions/ mirror",
    ],
    DOCS_ROOT / "current" / "interfaces" / "cli-surface-and-config-precedence.md": [
        "### Init and local bootstrap",
    ],
    DOCS_ROOT / "current" / "operations" / "inspect-approvals-and-watchdog.md": [
        "never ack their manifest",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definitions-compiler-and-launch.md": [
        "falls back to the repo mirror only if the packaged tree is unavailable",
        "not a public HTTP route",
    ],
    DOCS_ROOT / "current" / "interfaces" / "definition-registry-and-publish-lifecycle.md": [
        (
            "The repo-root mirror matters only as an explicit override or as a "
            "fallback when packaged seeds are unavailable."
        ),
    ],
    DOCS_ROOT / "current" / "architecture" / "openclaw-dispatch-and-session-contract.md": [
        "dispatch in bootstrap shape",
        "dispatch in execution shape",
        "Current bootstrap vs execution shapes",
        "manifest to acknowledge",
        "wait_for_response=true",
    ],
    DOCS_ROOT / "current" / "architecture" / "runtime-control-plane.md": [
        "cancel fences the current dispatch",
        "- accepted-terminal waiting state: `boundary_accepted_waiting_terminal`",
        "- accepted-terminal waiting state: boundary_accepted_waiting_terminal",
        "launch opens the root bootstrap dispatch",
    ],
}

AGGREGATE_SUMMARY_FAMILIES = (
    "phase-0-3-closeout",
    "phase-0-3-layout-and-shim-removal-program",
    "phase-0-3-contract-repair-program",
)
AGGREGATE_SUMMARY_REVIEW_EXCEPTION_FILES = ("phase-0-3-closeout-review-exceptions.md",)


def aggregate_summary_paths(*, include_review_exceptions: bool) -> set[Path]:
    paths = {
        DOCS_ROOT / "execution" / home / f"{family}.md"
        for family in AGGREGATE_SUMMARY_FAMILIES
        for home in ("plans", "evidence", "reviews")
    }
    if include_review_exceptions:
        paths |= {
            DOCS_ROOT / "execution" / "reviews" / filename
            for filename in AGGREGATE_SUMMARY_REVIEW_EXCEPTION_FILES
        }
    return paths


PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS = {
    path: ["summary-only: yes"] for path in aggregate_summary_paths(include_review_exceptions=True)
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

CROSS_PHASE_SUMMARY_SENTINEL_PATHS = aggregate_summary_paths(include_review_exceptions=True)

ARTIFACTS_CHANGED_REQUIRED_EVIDENCE_PATHS = {
    DOCS_ROOT / "execution" / "evidence" / "phase-0-closeout-grammar-and-proof.md",
}

SUMMARY_ONLY_REPLACEMENT_REQUIRED_PATHS = {
    DOCS_ROOT / "execution" / "plans" / "phase-0-canon-current-contrast-repair.md",
    DOCS_ROOT / "execution" / "evidence" / "phase-0-canon-current-contrast-repair.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-canon-current-contrast-repair.md",
    *aggregate_summary_paths(include_review_exceptions=True),
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
