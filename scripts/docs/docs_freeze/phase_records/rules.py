from __future__ import annotations

from pathlib import Path

from ..paths import ARCHIVE_ROOT, CURRENT_ROOT

PHASE0_AUTHORITY_REQUIRED_MARKERS: dict[Path, list[str]] = {}

PHASE0_AUTHORITY_FORBIDDEN_MARKERS: dict[Path, list[str]] = {}

PHASE0_CURRENT_DOC_REQUIRED_MARKERS = {
    CURRENT_ROOT / "README.md": [
        "does not compete with design canon",
    ],
    CURRENT_ROOT / "architecture" / "README.md": [
        "It is current-behavior contrast only, not design canon.",
    ],
    CURRENT_ROOT / "architecture" / "manifest-projection-and-acknowledgement.md": [
        "Older docs taught manifest-acknowledgement vocabulary",
    ],
    CURRENT_ROOT / "architecture" / "openclaw-and-bridge-plugin.md": [
        "manifest and checkpoint lineage remain controller-owned prompt and runtime truth",
    ],
    CURRENT_ROOT / "architecture" / "runtime-read-models-and-operator-surfaces.md": [
        "Current code also does not expose a dedicated manifest-ack query surface",
    ],
    CURRENT_ROOT / "interfaces" / "definition-precedence-and-skill-version-defaults.md": [
        "not part of the shipped default seed path",
    ],
    CURRENT_ROOT / "interfaces" / "cli-surface-and-config-precedence.md": [
        "### Init and local setup",
    ],
    CURRENT_ROOT / "interfaces" / "current-definition-bootstrap-and-task-upload.md": [
        "It does not define a canonical dispatch phase",
    ],
    CURRENT_ROOT / "interfaces" / "definitions-compiler-and-launch.md": [
        "Missing packaged seed files fail the shipped seed path",
    ],
    CURRENT_ROOT / "interfaces" / "definition-registry-and-publish-lifecycle.md": [
        "append a new immutable revision",
    ],
    CURRENT_ROOT / "operations" / "inspect-approvals-and-watchdog.md": [
        "accepted first-dispatch turns that have not produced committed first progress yet",
    ],
    CURRENT_ROOT / "architecture" / "runtime-control-plane.md": [
        "cancel requests `abort_requested`",
        "keeps the workspace lease held until inactivity is proven",
        "Current dispatch observation/drain facts include:",
        "accepted-boundary waiting is not a persisted control-state enum;",
    ],
}

PHASE0_CURRENT_DOC_FORBIDDEN_MARKERS = {
    CURRENT_ROOT / "architecture" / "manifest-projection-and-acknowledgement.md": [
        "records that the older manifest-acknowledgement flow no longer ships in the current tree",
    ],
    CURRENT_ROOT / "architecture" / "openclaw-and-bridge-plugin.md": [
        "manifest acknowledgement and checkpoint lineage",
    ],
    CURRENT_ROOT / "interfaces" / "definition-precedence-and-skill-version-defaults.md": [
        "otherwise fall back to the repo-root mirror under `definitions/**`",
        "if packaged seeds are unavailable, fall back to the repo definitions/ mirror",
    ],
    CURRENT_ROOT / "interfaces" / "cli-surface-and-config-precedence.md": [
        "### Init and local bootstrap",
    ],
    CURRENT_ROOT / "operations" / "inspect-approvals-and-watchdog.md": [
        "never ack their manifest",
    ],
    CURRENT_ROOT / "interfaces" / "definitions-compiler-and-launch.md": [
        "falls back to the repo mirror only if the packaged tree is unavailable",
        "not a public HTTP route",
    ],
    CURRENT_ROOT / "interfaces" / "definition-registry-and-publish-lifecycle.md": [
        (
            "The repo-root mirror matters only as an explicit override or as a "
            "fallback when packaged seeds are unavailable."
        ),
    ],
    CURRENT_ROOT / "architecture" / "openclaw-dispatch-and-session-contract.md": [
        "dispatch in bootstrap shape",
        "dispatch in execution shape",
        "Current bootstrap vs execution shapes",
        "manifest to acknowledge",
        "wait_for_response=true",
    ],
    CURRENT_ROOT / "architecture" / "runtime-control-plane.md": [
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
        ARCHIVE_ROOT / "execution" / home / f"{family}.md"
        for family in AGGREGATE_SUMMARY_FAMILIES
        for home in ("plans", "evidence", "reviews")
    }
    if include_review_exceptions:
        paths |= {
            ARCHIVE_ROOT / "execution" / "reviews" / filename
            for filename in AGGREGATE_SUMMARY_REVIEW_EXCEPTION_FILES
        }
    return paths


PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS = {
    path: ["summary-only: yes"] for path in aggregate_summary_paths(include_review_exceptions=True)
}

PHASE0_CLOSEOUT_SUMMARY_FORBIDDEN_MARKERS = {
    ARCHIVE_ROOT / "execution" / "plans" / "phase-0-3-closeout.md": [
        "selected phase: cross-phase",
    ],
    ARCHIVE_ROOT / "execution" / "evidence" / "phase-0-3-closeout.md": [
        "selected phase: cross-phase",
    ],
    ARCHIVE_ROOT / "execution" / "reviews" / "phase-0-3-closeout.md": [
        "- pass",
        "no confirmed Phase 0-3 blocker remains open on the integrated tree",
    ],
    ARCHIVE_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md": [
        "`WP6`",
    ],
}

CROSS_PHASE_SUMMARY_SENTINEL_PATHS = aggregate_summary_paths(include_review_exceptions=True)

ARTIFACTS_CHANGED_REQUIRED_EVIDENCE_PATHS = {
    ARCHIVE_ROOT / "execution" / "evidence" / "phase-0-closeout-grammar-and-proof.md",
}

SUMMARY_ONLY_REPLACEMENT_REQUIRED_PATHS = {
    ARCHIVE_ROOT / "execution" / "plans" / "phase-0-canon-current-contrast-repair.md",
    ARCHIVE_ROOT / "execution" / "evidence" / "phase-0-canon-current-contrast-repair.md",
    ARCHIVE_ROOT / "execution" / "reviews" / "phase-0-canon-current-contrast-repair.md",
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
