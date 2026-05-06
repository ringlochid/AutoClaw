from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from format_markdown import (
    FormatterViolation,
    collect_violations,
    iter_maintained_markdown_files,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "docs"
LIVE_REDESIGN_ROOT = DOCS_ROOT / "redesign"

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

REQUIRED_MARKERS = {
    DOCS_ROOT / "redesign" / "interfaces" / "distribution-and-database-support-matrix.md": [
        "pipx install autoclaw",
        'pipx install "autoclaw[postgres]"',
        "make docker-up",
        "make test-api-db",
        "make docker-down",
    ],
    DOCS_ROOT / "redesign" / "how-to" / "install-and-onboard.md": [
        "autoclaw init",
        "autoclaw doctor",
        "autoclaw serve",
    ],
    DOCS_ROOT / "redesign" / "how-to" / "use-postgres.md": [
        "AUTOCLAW_DATABASE_URL",
        "make docker-up",
        "make test-api-db",
        "make docker-down",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "README.md": [
        "api-schema-appendix.md",
        "api-machine-catalog.yaml",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "api-machine-catalog.yaml": [
        "version: 1",
        "search_definitions",
        "/definitions/{kind}/{key}",
        "maps_to_http: q",
    ],
    DOCS_ROOT / "redesign" / "workflows" / "README.md": [
        "Workflow schema appendix",
    ],
    DOCS_ROOT / "redesign" / "prompt-layer" / "README.md": [
        "prompt-resource-usage-appendix.md",
        "machine-contract.md",
    ],
    DOCS_ROOT / "redesign" / "architecture" / "assignment-contract.md": [
        "assignment_intent",
        "supplemental_durable_context",
        "`produces` is a requirement list only",
    ],
    DOCS_ROOT / "redesign" / "architecture" / "checkpoint-contract.md": [
        "record_checkpoint",
        "produced_artifacts",
        "transient_surfaces",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "api-surface-and-trust-lane-map.md": [
        "api-schema-appendix.md",
        "DispatchContextRead",
        "CheckpointWrite",
        "ParentToolSuccess",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "plugin-tool-reference.md": [
        "list_definition_versions(kind, key, limit?, cursor?, sort?)",
        "search_definitions(kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)",
        "get_definition(kind, key)",
        "## Operator-safe external lane",
        "record_checkpoint(checkpoint)",
        "upload_definition(definition_path)",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "api-schema-appendix.md": [
        "## Shared object ownership",
        "### `DefinitionUploadRequest`",
        "### `TaskStartResponse`",
        "### `DispatchContextRead`",
        "### `CheckpointWrite`",
        "### `OperatorFlowSnapshotResponse`",
        "### `ParentToolSuccess`",
        "### `DefinitionListQuery`",
        "### `DefinitionRevisionHistoryQuery`",
        "### `RuntimeTaskListQuery`",
    ],
    DOCS_ROOT / "redesign" / "workflows" / "task-compose-schema.md": [
        "If `roots.workspace` is omitted, it defaults to `ensure_task_default`.",
        "If `roots.context` is omitted, it defaults to `ensure_task_default`.",
    ],
    DOCS_ROOT / "execution" / "maps" / "current-schema-route-and-plugin-migration-appendix.md": [
        "support-only lane",
        "Plugin tool migration",
        "Current schema, route, and plugin migration appendix",
    ],
    DOCS_ROOT / "execution" / "maps" / "README.md": [
        "Current schema, route, and plugin migration appendix",
    ],
    DOCS_ROOT / "execution" / "maps" / "current-to-target-mapping.md": [
        "Detailed appendix",
        "current-schema-route-and-plugin-migration-appendix.md",
    ],
    DOCS_ROOT / "execution" / "README.md": [
        "## Fast path",
        "Redesign-to-code landing map",
        "required supporting redesign reads",
        "required current-contrast pages",
        "Where are exhaustive API request/response details?",
        "Where is the frozen `autoclaw definitions import ...` contract?",
        "Should we rewrite from scratch or hard reset first?",
    ],
    DOCS_ROOT / "execution" / "how-to" / "use-this-pack-for-implementation.md": [
        "## Fast path",
        "## Appendix-owner rule",
        "use the current phase page as the sole phase-local contract",
        "Redesign-to-code landing map",
        "required supporting redesign reads",
        "required current-contrast pages",
        "required examples and diagrams",
        (
            "layer index page, machine catalog, generated inventory, or "
            "reference-only historical search router"
        ),
        "## Completeness rule",
    ],
    DOCS_ROOT / "execution" / "phases" / "overview.md": [
        "## Phase authority rule",
        "the current phase page is the sole phase-local implementation contract",
        "Phase 0.5",
        "required supporting redesign reads",
        "required current-contrast pages",
        "required examples or diagrams",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-0-docs-contract-freeze-and-setup.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "## Required examples and diagrams",
        "phase-boundary, read-coverage, and redesign-to-code landing maps",
        (
            "every phase page names required supporting redesign reads, "
            "required current-contrast reads, and required examples or "
            "diagrams"
        ),
        "`ruff check scripts/docs`",
        "`mypy scripts/docs`",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-0.5-cleanup-and-salvage-baseline.md": [
        "## Required supporting redesign reads",
        "fresh-baseline DB/state reset",
        "no carried migration history or reset-only schema survives as redesign authority",
        "plugin near-greenfield rebuild",
        "Cleanup and salvage checklist",
        "Repo salvage matrix",
        "## Required current contrast reads",
        "stale generated build or dist mirrors do not survive as typecheck or schema authority",
        "Historical prompt and artifact layers",
        "Findings",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-1-authoring-and-compiler-rewrite.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "Definition and task-compose YAML contract",
        "Definitions compiler and launch",
        "## Required examples and diagrams",
        "existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` only",
        "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
        "narrow `pyproject.toml` package-data entries",
        "shipped-path schema install, upgrade, and reset proof for SQLite",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "Prompt layer and worker delivery",
        "## Required examples and diagrams",
        "prompt-catalog generate/validate checks",
        (
            "runtime persistence truth for assignments, attempts, checkpoints, "
            "and currentness remains deferred to Phase 3"
        ),
        "Prompt-layer index",
        "Prompt field renderers",
        "Prompt machine contract",
        "Prompt catalog machine surface",
        "Generated prompt inventory",
        "Runtime rule blocks",
        "System and provider block",
        "Validation and reject blocks",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-3-runtime-parent-review-and-replan.md": [
        "Assignment contract",
        "Workflow schema appendix",
        "API schema appendix",
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "Runtime control plane",
        "`apps/api/app/cli.py` when Phase 3-owned runtime persistence truth must be",
        "shipped install, upgrade, and reset paths create the landed runtime schema",
        "SQLite local smoke",
        "Postgres + Docker strong verification",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-4a-openclaw-gateway-session-and-continuity.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "## Required examples and diagrams",
        "Recover a provider session",
        "API trust lanes",
        "Runtime lane separation rationale",
        "Prompt-layer index",
        "System and provider block",
        "Runtime rule blocks",
        "Validation and reject blocks",
        "Generated prompt inventory",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-4b-watchdog-operator-plugin-and-support-state.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "## Required examples and diagrams",
        "Operator definition and role boundary",
        "Use the current OpenClaw bridge plugin",
        "Runtime lane separation rationale",
        "Provider, worker, and operator boundary",
        "Recover a provider session",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-5a-definition-ingest-api-and-cli.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "API surface and route map",
        "API machine catalog",
        "SQLite local smoke",
        "Postgres + Docker strong verification",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-5b-packaging-release-and-docs-cutover.md": [
        "## Required supporting redesign reads",
        "## Required current contrast reads",
        "Packaging CLI and install",
        "Distribution and database support matrix",
        "SQLite local smoke verification",
        "Postgres + Docker strong verification",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-5-ingest-api-cli-package-and-cutover.md": [
        "API schema appendix",
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        (
            "zero-arg `autoclaw definitions import "
            "[--overwrite reject|allow_new_revision]` for shallow "
            "current-working-directory scan only"
        ),
    ],
    DOCS_ROOT / "execution" / "gates" / "phase-implementation-prompts.md": [
        "treat the current phase page as the sole phase-local implementation contract",
        "autoclaw definitions import ...",
        "workflow-schema-appendix.md",
        "api-schema-appendix.md",
        "prompt-resource-usage-appendix.md",
        "required supporting redesign reads",
        "required current-contrast pages",
        "required examples and diagrams",
        "redesign-code-landing-map.md",
        "## Phase-plan prompt",
        "selected current phase page",
        "do not mirror unrelated phase pages",
    ],
    DOCS_ROOT / "execution" / "gates" / "cleanup-and-salvage-checklist.md": [
        "fresh-baseline schema reset",
        "plugin rebuild boundary",
        "retain infra shell only",
        "delete as stale-contract coverage",
    ],
    DOCS_ROOT / "execution" / "gates" / "supporting-prompts.md": [
        "use any appendix owners named by the current phase page",
        "update named appendix owners when the changed behavior affects exhaustive",
        "Hard-reset classification for this phase",
        "Plugin rebuild boundary review",
        (
            "required supporting redesign reads, required current-contrast "
            "reads, and required examples and diagrams"
        ),
        "SQLite, Postgres+Docker, package, or reset verification lane",
    ],
    DOCS_ROOT / "execution" / "gates" / "verification-prompts.md": [
        "required supporting redesign reads",
        "Re-read any appendix owners named by the current phase page",
        "did the current phase page remain the phase-local authority?",
        "were named appendix owners updated when exhaustive detail changed?",
        "Confirm that any phase-local required checklist was completed.",
    ],
    DOCS_ROOT / "execution" / "gates" / "phase-done-gate.md": [
        "the current phase page remained the sole phase-local contract",
        "named appendix owners were updated when exhaustive API/schema/prompt detail changed",
        (
            "reusable prompts, gates, or checklists touched for the phase "
            "still point back to the current phase page"
        ),
        "any checklist explicitly required by the current phase page was completed",
        "required supporting redesign reads named by the phase page were used",
        "required current-contrast pages named by the phase page were used",
        "required examples and diagrams named by the phase page were read",
        "SQLite, Postgres+Docker, package, or reset verification lane",
    ],
    DOCS_ROOT / "execution" / "gates" / "mandatory-review-gate.md": [
        "the current phase page still acts as the phase-local contract owner",
        "named appendix owners were updated when exhaustive API/schema/prompt detail changed",
        (
            "reusable execution prompts or checklists touched by the phase "
            "still reference the phase page"
        ),
        "any earlier-phase prerequisite truth that this phase depends on was actually landed",
        "any checklist explicitly required by the current phase page was completed",
        "required supporting redesign reads named by the phase page were reread",
        "required current-contrast pages named by the phase page were reread",
        "required examples and diagrams named by the phase page were reviewed",
        "required SQLite, Postgres+Docker, package, or reset verification lanes",
        "install, upgrade, or reset proof does not rely on test-only schema creation",
    ],
    DOCS_ROOT / "execution" / "gates" / "docs-answer-sourcing-checklist.md": [
        "I checked the named appendix owner when exact API/schema/prompt detail mattered",
        (
            "I checked any required supporting redesign reads explicitly named "
            "by the current phase page"
        ),
        "I treated the current phase page as the sole phase-local execution contract",
    ],
    DOCS_ROOT / "execution" / "gates" / "README.md": [
        "Cleanup and salvage checklist",
    ],
    DOCS_ROOT / "execution" / "gates" / "reset-gate.md": [
        "Phase 0.5 cleanup and salvage always requires this gate",
        "reseed/bootstrap procedure is documented when reset would leave the system empty",
        "install or upgrade proof used the shipped path rather than test-only schema creation",
        "SQLite smoke ran",
        "Postgres + Docker strong verification ran",
    ],
    DOCS_ROOT / "execution" / "gates" / "rewrite-done-gate.md": [
        "shared Codex execution policy and shared implementation quickstart",
        "phase pages act as the sole phase-local execution contract owners",
        (
            "execution routing points implementers to appendix owners for "
            "exhaustive API/schema/prompt detail"
        ),
        (
            "reusable execution prompts are reference-first rather than large "
            "mirrored phase summaries"
        ),
        "cleanup-and-salvage checklist",
        "repo salvage matrix",
    ],
    DOCS_ROOT / "execution" / "maps" / "file-priority-map.md": [
        "authoritative appendix owners:",
        "docs/redesign/interfaces/api-schema-appendix.md",
        "docs/redesign/workflows/workflow-schema-appendix.md",
        "docs/redesign/prompt-layer/prompt-resource-usage-appendix.md",
        "repo code under `apps/**`",
        "repo tests under `apps/api/tests/**`",
        "`docs/**`",
        "targeted prompt validation tooling under `scripts/docs/*`",
        "`apps/api/app/schemas/runtime.py`",
        "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
        "narrow `pyproject.toml` package-data entries",
    ],
    DOCS_ROOT / "execution" / "maps" / "redesign-code-landing-map.md": [
        "## Coverage classes",
        "## Cross-cutting secondary coverage",
        "## Phase 0",
        "## Phase 5B",
        "Decisions front door",
        "How-to front door",
        "Tutorials front door",
        "Findings",
        "docs/redesign/prompt-layer/contract.md",
        "docs/redesign/architecture/runtime-database-and-object-contract.md",
        "docs/redesign/interfaces/testing-and-release-checklist.md",
        "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
        "narrow `pyproject.toml` package-data entries for those seed mirrors",
        "Postgres + Docker strong verification",
        "Prompt-layer index",
        "Prompt catalog machine surface",
        "System and provider block",
        "Runtime rule blocks",
        "Validation and reject blocks",
        "historical dispatch-family packs",
    ],
    DOCS_ROOT / "execution" / "maps" / "repo-salvage-matrix.md": [
        "plugin rebuild",
        "migration roots and mirrors",
        "retain infra shell only",
        "delete now",
    ],
    DOCS_ROOT / "execution" / "how-to" / "reset-db-schema-and-package-state.md": [
        "whether the baseline was intentionally left empty",
        "Phase 0.5 is the explicit cleanup phase where old schema truth may be",
    ],
    DOCS_ROOT / "execution" / "how-to" / "track-a-redesign-bug.md": [
        "phase_0_5",
        "cleanup-baseline issue",
    ],
    DOCS_ROOT / "execution" / "how-to" / "triage-a-failing-phase-or-workflow-lane.md": [
        "cleanup baseline issue",
        "Phase 0.5 total code hard reset baseline",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "definition-ingest-and-upload-contract.md": [
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        (
            "zero-arg `autoclaw definitions import` is the canonical shallow "
            "current-working-directory scan/import path"
        ),
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "cli-surface-and-operator-workflows.md": [
        "`autoclaw definitions ...`",
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        "zero-arg `autoclaw definitions import` is a shallow current-working-directory scan only",
    ],
}

FORBIDDEN_MARKERS = {
    DOCS_ROOT / "execution" / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md": [
        "`apps/api/app/schemas/runtime.py`",
        "`apps/api/app/db/models/runtime.py`",
    ],
}

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

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)#]+)")
REVIEWED_PLAN_PATTERN = re.compile(r"^- reviewed plan: `(?P<value>[^`]+)`$", re.MULTILINE)
REVIEWED_EVIDENCE_PATTERN = re.compile(r"^- reviewed evidence: `(?P<value>[^`]+)`$", re.MULTILINE)
REVIEW_ARTIFACT_PATTERN = re.compile(r"^- review artifact: `(?P<value>[^`]+)`$", re.MULTILINE)
WORK_PACKAGE_ID_TOKEN = r"P[0-9]+(?:\.[0-9]+|[A-Z])?-WP[0-9]+"
SELECTED_PHASE_PATTERN = re.compile(r"^selected phase: (?P<value>.+)$", re.MULTILINE)
CURRENT_PHASE_PAGE_PATTERN = re.compile(r"^current phase page: (?P<value>\S+)$", re.MULTILINE)
SELECTED_WORK_PACKAGES_PATTERN = re.compile(
    r"^selected work packages: (?P<value>.+)$",
    re.MULTILINE,
)
SELECTED_WORK_PACKAGES_VALUE_PATTERN = re.compile(
    rf"^{WORK_PACKAGE_ID_TOKEN}(?:, {WORK_PACKAGE_ID_TOKEN})*$"
)
SUMMARY_ONLY_PATTERN = re.compile(r"^summary-only: (?P<value>yes|no)$", re.MULTILINE)
DELEGATED_SLICES_PATTERN = re.compile(r"^delegated slices: (?P<value>none|listed)$", re.MULTILINE)
SLICE_ID_PATTERN = re.compile(r"^slice id: (?P<value>.+)$", re.MULTILINE)
SLICE_TYPE_PATTERN = re.compile(r"^slice type: (?P<value>edit|review-only)$", re.MULTILINE)
OWNED_SURFACES_PATTERN = re.compile(r"^owned surfaces: (?P<value>.+)$", re.MULTILINE)
TOUCHED_SURFACES_PATTERN = re.compile(r"^touched surfaces: (?P<value>.+)$", re.MULTILINE)
APPROVED_PLAN_PATTERN = re.compile(r"^- approved plan: `(?P<value>[^`]+)`$", re.MULTILINE)
SUMMARY_EXCEPTION_ENTRY_PATTERN = re.compile(
    r"^### (?P<title>[^\n]+)$\n(?P<body>.*?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)
SUMMARY_EXCEPTION_SURFACE_PATTERN = re.compile(r"^- surface: `(?P<value>[^`]+)`$", re.MULTILINE)
LATEST_OWNING_PHASE_REVIEW_PATTERN = re.compile(
    r"^- latest owning phase review: `(?P<value>[^`]+)`$",
    re.MULTILINE,
)
AUTHORITATIVE_EXCEPTION_HOME_PATTERN = re.compile(
    r"^- authoritative exception home: `(?P<value>[^`]+)`$",
    re.MULTILINE,
)
WORK_PACKAGE_ID_PATTERN = re.compile(rf"\b{WORK_PACKAGE_ID_TOKEN}\b")
CURRENT_DOC_PATH_PATTERN = re.compile(r"\bdocs/current/[A-Za-z0-9._/-]+\.md\b")
BACKTICKED_VALUE_PATTERN = re.compile(r"`(?P<value>[^`]+)`")
REPO_PATH_PATTERN = re.compile(
    r"\b(?:AGENTS\.md|STYLE\.md|README\.md|pyproject\.toml|Makefile|"
    r"docs/[A-Za-z0-9_./*-]+|apps/[A-Za-z0-9_./*-]+|"
    r"scripts/[A-Za-z0-9_./*-]+|definitions/[A-Za-z0-9_./*-]+)\b"
)

PHASE_SCOPED_REVIEW_EXCLUDED_PATHS = {
    DOCS_ROOT / "execution" / "reviews" / "README.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md",
    DOCS_ROOT / "execution" / "reviews" / "phase-review-template.md",
}

PHASE_SCOPED_REVIEW_REQUIRED_HEADINGS = [
    "## Slice identity",
    "## Phase-local contract",
    "## Scope",
    "## Verdict",
    "## Findings",
    "## Delegated-slice compliance",
    "## Proof lanes relied on",
    "## Stale-logic search proof",
    "## Kill-list proof",
    "## Docs answer-sourcing proof",
    "## Phase-bounded STYLE exceptions",
]

PHASE_SCOPED_PLAN_EXCLUDED_PATHS = {
    DOCS_ROOT / "execution" / "plans" / "README.md",
    DOCS_ROOT / "execution" / "plans" / "phase-plan-template.md",
    DOCS_ROOT / "execution" / "plans" / "phase-0-3-closeout.md",
}

PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS = {
    DOCS_ROOT / "execution" / "evidence" / "README.md",
    DOCS_ROOT / "execution" / "evidence" / "phase-evidence-template.md",
    DOCS_ROOT / "execution" / "evidence" / "phase-0-3-closeout.md",
}

PHASE0_ALLOWED_CURRENT_DOC_PATHS = {
    path.relative_to(ROOT).as_posix() for path in PHASE0_CURRENT_DOC_REQUIRED_MARKERS
}

PHASE_PAGE_BY_NAME = {
    "Phase 0": DOCS_ROOT / "execution" / "phases" / "phase-0-docs-contract-freeze-and-setup.md",
    "Phase 0.5": DOCS_ROOT / "execution" / "phases" / "phase-0.5-cleanup-and-salvage-baseline.md",
    "Phase 1": DOCS_ROOT / "execution" / "phases" / "phase-1-authoring-and-compiler-rewrite.md",
    "Phase 2": DOCS_ROOT / "execution" / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md",
    "Phase 3": DOCS_ROOT / "execution" / "phases" / "phase-3-runtime-parent-review-and-replan.md",
    "Phase 4A": DOCS_ROOT
    / "execution"
    / "phases"
    / "phase-4a-openclaw-gateway-session-and-continuity.md",
    "Phase 4B": DOCS_ROOT
    / "execution"
    / "phases"
    / "phase-4b-watchdog-operator-plugin-and-support-state.md",
    "Phase 5A": DOCS_ROOT / "execution" / "phases" / "phase-5a-definition-ingest-api-and-cli.md",
    "Phase 5B": DOCS_ROOT
    / "execution"
    / "phases"
    / "phase-5b-packaging-release-and-docs-cutover.md",
}


@dataclass(frozen=True)
class PhaseScopedReviewBundle:
    review_path: Path
    review_text: str
    reviewed_plan_path: Path
    reviewed_evidence_path: Path
    selected_phase: str
    current_phase_page: Path


@dataclass(frozen=True)
class PhaseScopedPlanRecord:
    plan_path: Path
    plan_text: str
    selected_phase: str
    current_phase_page: Path


@dataclass(frozen=True)
class PhaseScopedEvidenceRecord:
    evidence_path: Path
    evidence_text: str
    selected_phase: str
    approved_plan_path: Path
    approved_plan_record: PhaseScopedPlanRecord


def _api_appendix_path() -> Path:
    return DOCS_ROOT / "redesign" / "interfaces" / "api-schema-appendix.md"


def _api_appendix_headings() -> list[str]:
    headings: list[str] = []
    for line in _api_appendix_path().read_text(encoding="utf-8").splitlines():
        if line.startswith("### `") and line.endswith("`"):
            headings.append(line.strip())
    return headings


def _matching_line_numbers(text: str, needle: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines(), start=1) if needle in line]


def _section_slice(text: str, start_heading: str, end_heading: str) -> str:
    start = text.find(start_heading)
    if start == -1:
        return ""
    end = text.find(end_heading, start + len(start_heading))
    if end == -1:
        return text[start:]
    return text[start:end]


def _section_body(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body") if match else ""


def _missing_section_markers(
    text: str,
    *,
    start_heading: str,
    end_heading: str,
    markers: list[str],
) -> list[str]:
    section = _section_slice(text, start_heading, end_heading)
    return [marker for marker in markers if marker not in section]


def _extract_single_marked_value(
    *,
    text: str,
    pattern: re.Pattern[str],
    label: str,
    artifact_path: Path,
    errors: list[str],
) -> str | None:
    matches = [match.group("value").strip() for match in pattern.finditer(text)]
    unique_matches = list(dict.fromkeys(matches))
    if not unique_matches:
        errors.append(f"{artifact_path.relative_to(ROOT)} is missing {label}")
        return None
    if len(unique_matches) != 1:
        joined = ", ".join(unique_matches)
        errors.append(f"{artifact_path.relative_to(ROOT)} must name exactly one {label}: {joined}")
        return None
    return unique_matches[0]


def _resolve_record_link(artifact_path: Path, relative_ref: str) -> Path:
    return (artifact_path.parent / relative_ref).resolve()


def _extract_selected_phase(
    artifact_path: Path, artifact_text: str, errors: list[str]
) -> str | None:
    return _extract_single_marked_value(
        text=artifact_text,
        pattern=SELECTED_PHASE_PATTERN,
        label="top-level `selected phase:` label",
        artifact_path=artifact_path,
        errors=errors,
    )


def _extract_selected_work_packages(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> list[str] | None:
    selected_work_packages = _extract_single_marked_value(
        text=artifact_text,
        pattern=SELECTED_WORK_PACKAGES_PATTERN,
        label="top-level `selected work packages:` label",
        artifact_path=artifact_path,
        errors=errors,
    )
    if selected_work_packages is None:
        return None
    if not SELECTED_WORK_PACKAGES_VALUE_PATTERN.fullmatch(selected_work_packages):
        errors.append(
            f"{artifact_path.relative_to(ROOT)} must use exact comma-separated "
            "`selected work packages:` grammar"
        )
        return None
    return selected_work_packages.split(", ")


def _extract_current_phase_page(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> Path | None:
    current_phase_page = _extract_single_marked_value(
        text=artifact_text,
        pattern=CURRENT_PHASE_PAGE_PATTERN,
        label="top-level `current phase page:` label",
        artifact_path=artifact_path,
        errors=errors,
    )
    if current_phase_page is None:
        return None
    return (ROOT / current_phase_page).resolve()


def _extract_summary_only(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> str | None:
    return _extract_single_marked_value(
        text=artifact_text,
        pattern=SUMMARY_ONLY_PATTERN,
        label="top-level `summary-only:` label",
        artifact_path=artifact_path,
        errors=errors,
    )


def _extract_delegated_slices(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> str | None:
    return _extract_single_marked_value(
        text=artifact_text,
        pattern=DELEGATED_SLICES_PATTERN,
        label="top-level `delegated slices:` label",
        artifact_path=artifact_path,
        errors=errors,
    )


def _validate_delegated_slice_grammar(
    *,
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> None:
    delegated_slices = _extract_delegated_slices(artifact_path, artifact_text, errors)
    if delegated_slices is None:
        return

    slice_id_count = len(SLICE_ID_PATTERN.findall(artifact_text))
    slice_type_count = len(SLICE_TYPE_PATTERN.findall(artifact_text))
    owned_surfaces_count = len(OWNED_SURFACES_PATTERN.findall(artifact_text))
    touched_surfaces_count = len(TOUCHED_SURFACES_PATTERN.findall(artifact_text))

    if delegated_slices == "none":
        if any((slice_id_count, slice_type_count, owned_surfaces_count, touched_surfaces_count)):
            errors.append(
                f"{artifact_path.relative_to(ROOT)} declares `delegated slices: none` "
                "but still lists delegated-slice label lines"
            )
        return

    counts = {
        "slice id": slice_id_count,
        "slice type": slice_type_count,
        "owned surfaces": owned_surfaces_count,
        "touched surfaces": touched_surfaces_count,
    }
    if not slice_id_count:
        errors.append(
            f"{artifact_path.relative_to(ROOT)} declares `delegated slices: listed` "
            "but has no `slice id:` entries"
        )
        return
    if len(set(counts.values())) != 1:
        rendered_counts = ", ".join(f"{label}={count}" for label, count in counts.items())
        errors.append(
            f"{artifact_path.relative_to(ROOT)} has unbalanced delegated-slice "
            f"labels: {rendered_counts}"
        )


def _legacy_heading_hits() -> dict[Path, list[int]]:
    hits: dict[Path, list[int]] = {}
    for path in LIVE_REDESIGN_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        line_numbers = _matching_line_numbers(text, LEGACY_HEADING)
        if line_numbers:
            hits[path] = line_numbers
    return hits


def _compatibility_status_hits() -> dict[Path, list[int]]:
    hits: dict[Path, list[int]] = {}
    for path in LIVE_REDESIGN_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        line_numbers = _matching_line_numbers(text, COMPATIBILITY_STATUS)
        if line_numbers:
            hits[path] = line_numbers
    return hits


def _deleted_filename_hits() -> dict[str, list[tuple[Path, list[int]]]]:
    hits: dict[str, list[tuple[Path, list[int]]]] = {}
    for path in iter_maintained_markdown_files(ROOT):
        if path in DELETED_FILENAME_HISTORY_EXCLUDED_PATHS:
            continue
        text = path.read_text(encoding="utf-8")
        for deleted_name in DELETED_ROUTER_FILENAMES:
            line_numbers = _matching_line_numbers(text, deleted_name)
            if line_numbers:
                hits.setdefault(deleted_name, []).append((path, line_numbers))
    return hits


def _front_door_formatter_paths() -> list[Path]:
    return [path for path in FRONT_DOOR_FORMATTER_PATHS if path.exists()]


def _execution_markdown_sources() -> list[Path]:
    execution_docs = sorted((DOCS_ROOT / "execution").rglob("*.md"))
    return [ROOT / "AGENTS.md", *execution_docs]


def _linked_redesign_paths_from_execution() -> set[Path]:
    linked: set[Path] = set()
    for path in _execution_markdown_sources():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (path.parent / target).resolve()
            try:
                rel = resolved.relative_to(ROOT)
            except ValueError:
                continue
            if rel.parts[:2] == ("docs", "redesign") and resolved.is_file():
                linked.add(resolved)
    return linked


def _unreferenced_redesign_paths() -> list[Path]:
    redesign_files = sorted(
        path
        for path in LIVE_REDESIGN_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".md", ".yaml"}
    )
    linked = _linked_redesign_paths_from_execution()
    return [path for path in redesign_files if path not in linked]


def _markdown_formatter_violations() -> list[FormatterViolation]:
    return collect_violations(_front_door_formatter_paths())


def _phase_scoped_review_paths() -> list[Path]:
    review_root = DOCS_ROOT / "execution" / "reviews"
    return [
        path
        for path in sorted(review_root.glob("*.md"))
        if path not in PHASE_SCOPED_REVIEW_EXCLUDED_PATHS
    ]


def _phase_scoped_plan_paths() -> list[Path]:
    plan_root = DOCS_ROOT / "execution" / "plans"
    return [
        path
        for path in sorted(plan_root.glob("*.md"))
        if path not in PHASE_SCOPED_PLAN_EXCLUDED_PATHS
    ]


def _phase_scoped_evidence_paths() -> list[Path]:
    evidence_root = DOCS_ROOT / "execution" / "evidence"
    return [
        path
        for path in sorted(evidence_root.glob("*.md"))
        if path not in PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS
    ]


def _phase_page_work_package_ids(phase_page_path: Path) -> set[str]:
    ordered_work_packages = _section_body(
        phase_page_path.read_text(encoding="utf-8"),
        "## Ordered work packages",
    )
    return set(WORK_PACKAGE_ID_PATTERN.findall(ordered_work_packages))


def _validate_artifact_work_package_ids(
    *,
    artifact_path: Path,
    artifact_text: str,
    current_phase_page: Path,
    errors: list[str],
) -> None:
    phase_work_package_ids = _phase_page_work_package_ids(current_phase_page)
    if not phase_work_package_ids:
        errors.append(
            f"{current_phase_page.relative_to(ROOT)} is missing parseable work-package ids "
            "under `## Ordered work packages`"
        )
        return

    selected_work_packages = _extract_selected_work_packages(artifact_path, artifact_text, errors)
    if selected_work_packages is not None:
        for work_package_id in selected_work_packages:
            if work_package_id not in phase_work_package_ids:
                errors.append(
                    f"{artifact_path.relative_to(ROOT)} names unknown work-package id "
                    f"`{work_package_id}` for {current_phase_page.relative_to(ROOT)}"
                )

    ordered_work_packages = _section_body(artifact_text, "## Ordered work packages")
    for work_package_id in WORK_PACKAGE_ID_PATTERN.findall(ordered_work_packages):
        if work_package_id not in phase_work_package_ids:
            errors.append(
                f"{artifact_path.relative_to(ROOT)} defines unknown work-package id "
                f"`{work_package_id}` for {current_phase_page.relative_to(ROOT)}"
            )


def _validate_phase0_current_doc_unlocks(
    *,
    artifact_path: Path,
    artifact_text: str,
    selected_phase: str,
    errors: list[str],
) -> None:
    if selected_phase != "Phase 0":
        return

    current_doc_paths = set(CURRENT_DOC_PATH_PATTERN.findall(artifact_text))
    for current_doc_path in sorted(current_doc_paths - PHASE0_ALLOWED_CURRENT_DOC_PATHS):
        errors.append(
            f"{artifact_path.relative_to(ROOT)} references out-of-policy Phase 0 current doc: "
            f"{current_doc_path}"
        )


def _extract_backticked_repo_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for backticked_value in BACKTICKED_VALUE_PATTERN.findall(text):
        for path in REPO_PATH_PATTERN.findall(backticked_value):
            paths.add(path.rstrip(".,"))
    return paths


def _path_matches_surface(path: str, surface: str) -> bool:
    normalized_path = path.rstrip("/")
    normalized_surface = surface.rstrip("/")
    if "*" in normalized_surface:
        return Path(normalized_path).match(normalized_surface)
    if normalized_path == normalized_surface:
        return True
    if "." not in Path(normalized_surface).name:
        return normalized_path.startswith(f"{normalized_surface}/")
    return False


def _allowed_surface_specs_from_plan(plan_record: PhaseScopedPlanRecord) -> set[str]:
    allowed_specs = _extract_backticked_repo_paths(plan_record.plan_text)
    allowed_specs.add(plan_record.plan_path.relative_to(ROOT).as_posix())
    return allowed_specs


def _validate_evidence_artifact_paths(
    *,
    evidence_record: PhaseScopedEvidenceRecord,
    errors: list[str],
) -> None:
    artifact_section = _section_body(evidence_record.evidence_text, "## Artifacts")
    if not artifact_section:
        return

    artifact_paths = _extract_backticked_repo_paths(artifact_section)
    if not artifact_paths:
        return

    allowed_specs = _allowed_surface_specs_from_plan(evidence_record.approved_plan_record)
    allowed_specs.add(evidence_record.evidence_path.relative_to(ROOT).as_posix())
    review_artifact_ref = _extract_single_marked_value(
        text=evidence_record.evidence_text,
        pattern=REVIEW_ARTIFACT_PATTERN,
        label="review artifact link",
        artifact_path=evidence_record.evidence_path,
        errors=errors,
    )
    if review_artifact_ref is not None:
        allowed_specs.add(
            _resolve_record_link(evidence_record.evidence_path, review_artifact_ref)
            .relative_to(ROOT)
            .as_posix()
        )

    for artifact_path in sorted(artifact_paths):
        if not any(_path_matches_surface(artifact_path, surface) for surface in allowed_specs):
            errors.append(
                f"{evidence_record.evidence_path.relative_to(ROOT)} lists artifact path outside "
                f"parseable owned/allowed surfaces: {artifact_path}"
            )


def _phase_scoped_plan_records(errors: list[str]) -> list[PhaseScopedPlanRecord]:
    records: list[PhaseScopedPlanRecord] = []
    for plan_path in _phase_scoped_plan_paths():
        plan_text = plan_path.read_text(encoding="utf-8")
        if _extract_summary_only(plan_path, plan_text, errors) == "yes":
            continue
        selected_phase = _extract_selected_phase(plan_path, plan_text, errors)
        current_phase_page = _extract_current_phase_page(plan_path, plan_text, errors)
        if selected_phase is None or current_phase_page is None:
            continue

        expected_phase_page = PHASE_PAGE_BY_NAME.get(selected_phase)
        if expected_phase_page is None:
            errors.append(
                f"{plan_path.relative_to(ROOT)} resolves an unknown selected phase: "
                f"{selected_phase}"
            )
            continue
        if current_phase_page != expected_phase_page.resolve():
            errors.append(
                f"{plan_path.relative_to(ROOT)} resolves the wrong current phase page for "
                f"{selected_phase}: {current_phase_page.relative_to(ROOT)}"
            )
            continue

        records.append(
            PhaseScopedPlanRecord(
                plan_path=plan_path,
                plan_text=plan_text,
                selected_phase=selected_phase,
                current_phase_page=current_phase_page,
            )
        )
    return records


def _phase_scoped_evidence_records(
    *,
    errors: list[str],
    plan_records: list[PhaseScopedPlanRecord],
) -> list[PhaseScopedEvidenceRecord]:
    plan_records_by_path = {record.plan_path.resolve(): record for record in plan_records}
    records: list[PhaseScopedEvidenceRecord] = []
    for evidence_path in _phase_scoped_evidence_paths():
        evidence_text = evidence_path.read_text(encoding="utf-8")
        if _extract_summary_only(evidence_path, evidence_text, errors) == "yes":
            continue
        selected_phase = _extract_selected_phase(evidence_path, evidence_text, errors)
        approved_plan_ref = _extract_single_marked_value(
            text=evidence_text,
            pattern=APPROVED_PLAN_PATTERN,
            label="approved plan link",
            artifact_path=evidence_path,
            errors=errors,
        )
        if selected_phase is None or approved_plan_ref is None:
            continue

        approved_plan_path = _resolve_record_link(evidence_path, approved_plan_ref)
        plan_record = plan_records_by_path.get(approved_plan_path)
        if plan_record is None:
            errors.append(
                f"{evidence_path.relative_to(ROOT)} points to missing or non-phase-scoped "
                f"approved plan: {approved_plan_ref}"
            )
            continue
        if plan_record.plan_path.name != evidence_path.name:
            errors.append(
                f"{evidence_path.relative_to(ROOT)} must link to the matching phase-scoped "
                f"plan artifact, not {plan_record.plan_path.relative_to(ROOT)}"
            )
            continue
        if selected_phase != plan_record.selected_phase:
            errors.append(
                f"{evidence_path.relative_to(ROOT)} must record the same selected phase as "
                f"its approved plan: {selected_phase} vs {plan_record.selected_phase}"
            )
            continue

        records.append(
            PhaseScopedEvidenceRecord(
                evidence_path=evidence_path,
                evidence_text=evidence_text,
                selected_phase=selected_phase,
                approved_plan_path=approved_plan_path,
                approved_plan_record=plan_record,
            )
        )
    return records


def _phase_scoped_review_bundles(errors: list[str]) -> list[PhaseScopedReviewBundle]:
    bundles: list[PhaseScopedReviewBundle] = []
    for review_path in _phase_scoped_review_paths():
        review_text = review_path.read_text(encoding="utf-8")
        if _extract_summary_only(review_path, review_text, errors) == "yes":
            continue
        for heading in PHASE_SCOPED_REVIEW_REQUIRED_HEADINGS:
            if heading not in review_text:
                errors.append(
                    f"{review_path.relative_to(ROOT)} is missing required review heading: {heading}"
                )

        reviewed_plan_ref = _extract_single_marked_value(
            text=review_text,
            pattern=REVIEWED_PLAN_PATTERN,
            label="reviewed plan link",
            artifact_path=review_path,
            errors=errors,
        )
        reviewed_evidence_ref = _extract_single_marked_value(
            text=review_text,
            pattern=REVIEWED_EVIDENCE_PATTERN,
            label="reviewed evidence link",
            artifact_path=review_path,
            errors=errors,
        )
        if reviewed_plan_ref is None or reviewed_evidence_ref is None:
            continue

        review_selected_phase = _extract_selected_phase(review_path, review_text, errors)
        review_current_phase_page = _extract_current_phase_page(review_path, review_text, errors)
        if review_selected_phase is None or review_current_phase_page is None:
            continue

        reviewed_plan_path = _resolve_record_link(review_path, reviewed_plan_ref)
        reviewed_evidence_path = _resolve_record_link(review_path, reviewed_evidence_ref)
        if not reviewed_plan_path.exists():
            errors.append(
                f"{review_path.relative_to(ROOT)} points to missing reviewed plan: "
                f"{reviewed_plan_ref}"
            )
            continue
        if not reviewed_evidence_path.exists():
            errors.append(
                f"{review_path.relative_to(ROOT)} points to missing reviewed evidence: "
                f"{reviewed_evidence_ref}"
            )
            continue

        if reviewed_plan_path.name != review_path.name:
            errors.append(
                f"{review_path.relative_to(ROOT)} must review the matching plan artifact, "
                f"not {reviewed_plan_path.relative_to(ROOT)}"
            )
        if reviewed_evidence_path.name != review_path.name:
            errors.append(
                f"{review_path.relative_to(ROOT)} must review the matching evidence artifact, "
                f"not {reviewed_evidence_path.relative_to(ROOT)}"
            )

        plan_text = reviewed_plan_path.read_text(encoding="utf-8")
        evidence_text = reviewed_evidence_path.read_text(encoding="utf-8")
        selected_phase = _extract_selected_phase(reviewed_plan_path, plan_text, errors)
        evidence_phase = _extract_selected_phase(reviewed_evidence_path, evidence_text, errors)
        current_phase_page = _extract_current_phase_page(reviewed_plan_path, plan_text, errors)
        if selected_phase is None or evidence_phase is None or current_phase_page is None:
            continue
        if selected_phase != evidence_phase:
            errors.append(
                f"{review_path.relative_to(ROOT)} resolves conflicting selected phases: "
                f"{selected_phase} vs {evidence_phase}"
            )
            continue
        if review_selected_phase != selected_phase:
            errors.append(
                f"{review_path.relative_to(ROOT)} must record the same selected phase as "
                f"its plan/evidence bundle: {review_selected_phase} vs {selected_phase}"
            )
            continue

        expected_phase_page = PHASE_PAGE_BY_NAME.get(selected_phase)
        if expected_phase_page is None:
            errors.append(
                f"{review_path.relative_to(ROOT)} resolves an unknown selected phase: "
                f"{selected_phase}"
            )
            continue
        if current_phase_page != expected_phase_page.resolve():
            errors.append(
                f"{review_path.relative_to(ROOT)} resolves the wrong current phase page for "
                f"{selected_phase}: {current_phase_page.relative_to(ROOT)}"
            )
            continue
        if review_current_phase_page != current_phase_page:
            errors.append(
                f"{review_path.relative_to(ROOT)} must record the same current phase page as "
                f"its reviewed plan: {review_current_phase_page.relative_to(ROOT)} vs "
                f"{current_phase_page.relative_to(ROOT)}"
            )
            continue
        if not current_phase_page.exists():
            errors.append(
                f"{review_path.relative_to(ROOT)} points to missing current phase page: "
                f"{current_phase_page.relative_to(ROOT)}"
            )
            continue

        evidence_review_ref = _extract_single_marked_value(
            text=evidence_text,
            pattern=REVIEW_ARTIFACT_PATTERN,
            label="review artifact link",
            artifact_path=reviewed_evidence_path,
            errors=errors,
        )
        if evidence_review_ref is not None:
            linked_review_path = _resolve_record_link(reviewed_evidence_path, evidence_review_ref)
            if linked_review_path != review_path.resolve():
                errors.append(
                    f"{reviewed_evidence_path.relative_to(ROOT)} must link back to "
                    f"{review_path.relative_to(ROOT)}"
                )

        bundles.append(
            PhaseScopedReviewBundle(
                review_path=review_path,
                review_text=review_text,
                reviewed_plan_path=reviewed_plan_path,
                reviewed_evidence_path=reviewed_evidence_path,
                selected_phase=selected_phase,
                current_phase_page=current_phase_page,
            )
        )
    return bundles


def _validate_summary_only_review_exceptions(
    *,
    errors: list[str],
    review_bundles: list[PhaseScopedReviewBundle],
) -> None:
    summary_only_exceptions_path = (
        DOCS_ROOT / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md"
    )
    if not summary_only_exceptions_path.exists():
        return

    review_bundles_by_path = {bundle.review_path.resolve(): bundle for bundle in review_bundles}

    summary_text = summary_only_exceptions_path.read_text(encoding="utf-8")
    for match in SUMMARY_EXCEPTION_ENTRY_PATTERN.finditer(summary_text):
        entry_text = match.group("body")
        exception_path = _extract_single_marked_value(
            text=entry_text,
            pattern=SUMMARY_EXCEPTION_SURFACE_PATTERN,
            label=f"summary-only exception surface in `{match.group('title')}`",
            artifact_path=summary_only_exceptions_path,
            errors=errors,
        )
        latest_review_ref = _extract_single_marked_value(
            text=entry_text,
            pattern=LATEST_OWNING_PHASE_REVIEW_PATTERN,
            label=f"latest owning phase review link in `{match.group('title')}`",
            artifact_path=summary_only_exceptions_path,
            errors=errors,
        )
        authoritative_home_ref = _extract_single_marked_value(
            text=entry_text,
            pattern=AUTHORITATIVE_EXCEPTION_HOME_PATTERN,
            label=f"authoritative exception home link in `{match.group('title')}`",
            artifact_path=summary_only_exceptions_path,
            errors=errors,
        )
        if exception_path is None or latest_review_ref is None or authoritative_home_ref is None:
            continue

        latest_review_path = _resolve_record_link(summary_only_exceptions_path, latest_review_ref)
        authoritative_home_path = _resolve_record_link(
            summary_only_exceptions_path,
            authoritative_home_ref,
        )
        if latest_review_path != authoritative_home_path:
            errors.append(
                f"{summary_only_exceptions_path.relative_to(ROOT)} must point "
                f"`{match.group('title')}` at the same authoritative later-phase review for "
                "`latest owning phase review` and `authoritative exception home`"
            )
            continue

        review_bundle = review_bundles_by_path.get(latest_review_path)
        if review_bundle is None:
            errors.append(
                f"{summary_only_exceptions_path.relative_to(ROOT)} points later-phase "
                f"STYLE exception `{exception_path}` at non-phase-scoped review "
                f"{latest_review_path.relative_to(ROOT)}"
            )
            continue

        if review_bundle.selected_phase == "Phase 0":
            continue

        if (
            "## Phase-bounded STYLE exceptions" not in review_bundle.review_text
            or f"### `{exception_path}`" not in review_bundle.review_text
        ):
            errors.append(
                f"{summary_only_exceptions_path.relative_to(ROOT)} still carries later-phase "
                f"STYLE exception `{exception_path}` for {review_bundle.selected_phase} "
                f"without authoritative phase-scoped coverage in "
                f"{review_bundle.review_path.relative_to(ROOT)}"
            )


def _validate_summary_only_artifact_headers(errors: list[str]) -> None:
    for artifact_path in sorted(PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS):
        if not artifact_path.exists():
            continue
        artifact_text = artifact_path.read_text(encoding="utf-8")
        summary_only = _extract_summary_only(artifact_path, artifact_text, errors)
        if summary_only is None:
            continue
        if summary_only != "yes":
            errors.append(
                f"{artifact_path.relative_to(ROOT)} must use `summary-only: yes` "
                "to stay valid as a historical or aggregate summary artifact"
            )


def _validate_required_markers(
    *,
    errors: list[str],
    rules: dict[Path, list[str]],
    missing_prefix: str,
    missing_file_prefix: str,
    require_presence: bool,
) -> None:
    for path, markers in rules.items():
        if not path.exists():
            if require_presence:
                errors.append(f"{missing_file_prefix}: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{missing_prefix}: {path.relative_to(ROOT)} -> {marker}")


def _validate_forbidden_markers(
    *,
    errors: list[str],
    rules: dict[Path, list[str]],
    forbidden_prefix: str,
) -> None:
    for path, markers in rules.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker in text:
                errors.append(f"{forbidden_prefix}: {path.relative_to(ROOT)} -> {marker}")


def _print_inventory(
    *,
    legacy_heading_hits: dict[Path, list[int]],
    compatibility_status_hits: dict[Path, list[int]],
    deleted_filename_hits: dict[str, list[tuple[Path, list[int]]]],
    formatter_violations: list[FormatterViolation],
) -> None:
    print("API appendix headings:")
    for heading in _api_appendix_headings():
        print(f"- {heading}")

    print("")
    print("Required marker coverage:")
    for path, markers in REQUIRED_MARKERS.items():
        rel = path.relative_to(ROOT)
        if not path.exists():
            print(f"- {rel}: missing file")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            print(f"- {rel}: missing {len(missing)} marker(s)")
            for marker in missing:
                print(f"  - {marker}")
        else:
            print(f"- {rel}: ok ({len(markers)} marker(s))")

    print("")
    print("Execution-linked redesign coverage:")
    unreferenced = _unreferenced_redesign_paths()
    if unreferenced:
        for path in unreferenced:
            print(f"- missing execution link: {path.relative_to(ROOT)}")
    else:
        print("- all redesign markdown/yaml files are linked from AGENTS.md or docs/execution/")

    print("")
    print("Legacy filename headings in live redesign docs:")
    if legacy_heading_hits:
        for path, line_numbers in sorted(legacy_heading_hits.items()):
            print(f"- {path.relative_to(ROOT)}: lines {', '.join(str(n) for n in line_numbers)}")
    else:
        print("- none")

    print("")
    print("Compatibility statuses in live redesign docs:")
    if compatibility_status_hits:
        for path, line_numbers in sorted(compatibility_status_hits.items()):
            print(f"- {path.relative_to(ROOT)}: lines {', '.join(str(n) for n in line_numbers)}")
    else:
        print("- none")

    print("")
    print("Deleted router filename references in maintained docs:")
    if deleted_filename_hits:
        for deleted_name in sorted(deleted_filename_hits):
            print(f"- {deleted_name}")
            for path, line_numbers in deleted_filename_hits[deleted_name]:
                joined = ", ".join(str(n) for n in line_numbers)
                print(f"  - {path.relative_to(ROOT)}: lines {joined}")
    else:
        print("- none")

    print("")
    print("Front-door markdown unwrap formatter violations:")
    if formatter_violations:
        for violation in formatter_violations:
            print(f"- {violation.path.relative_to(ROOT)}:{violation.line}: {violation.reason}")
    else:
        print("- none")


def validate(debug_inventory: bool = False) -> int:
    errors: list[str] = []
    maintained_markdown_paths = iter_maintained_markdown_files(ROOT)
    redesign_and_execution_paths = list((DOCS_ROOT / "redesign").rglob("*.md")) + list(
        (DOCS_ROOT / "execution").rglob("*.md")
    )
    legacy_heading_hits = _legacy_heading_hits()
    compatibility_status_hits = _compatibility_status_hits()
    deleted_filename_hits = _deleted_filename_hits()
    formatter_violations = _markdown_formatter_violations()
    unreferenced_redesign_paths = _unreferenced_redesign_paths()

    for path in maintained_markdown_paths:
        if path in BANNED_PATTERN_EXCLUDED_PATHS:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for pattern in BANNED_PATTERNS:
            if pattern in text:
                errors.append(f"{path.relative_to(ROOT)} still contains banned text: {pattern}")

    for path, markers in REQUIRED_MARKERS.items():
        if not path.exists():
            errors.append(f"required docs file is missing: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{path.relative_to(ROOT)} is missing required marker: {marker}")

    for forbidden in FORBIDDEN_ROOT_FILES:
        if forbidden.exists():
            errors.append(f"forbidden root file still exists: {forbidden.relative_to(ROOT)}")

    for path, forbidden_markers in FORBIDDEN_MARKERS.items():
        if not path.exists():
            errors.append(f"required docs file is missing: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            if marker in text:
                errors.append(f"{path.relative_to(ROOT)} still contains forbidden marker: {marker}")

    _validate_required_markers(
        errors=errors,
        rules=PHASE0_AUTHORITY_REQUIRED_MARKERS,
        missing_prefix="Phase 0 execution authority surface is missing required marker",
        missing_file_prefix="Phase 0 execution authority surface is missing",
        require_presence=True,
    )
    _validate_forbidden_markers(
        errors=errors,
        rules=PHASE0_AUTHORITY_FORBIDDEN_MARKERS,
        forbidden_prefix="Phase 0 execution authority surface still contains forbidden marker",
    )

    _validate_required_markers(
        errors=errors,
        rules=PHASE0_CURRENT_DOC_REQUIRED_MARKERS,
        missing_prefix="Phase 0 current-contrast doc is missing required marker",
        missing_file_prefix="Phase 0 current-contrast doc is missing",
        require_presence=True,
    )
    _validate_forbidden_markers(
        errors=errors,
        rules=PHASE0_CURRENT_DOC_FORBIDDEN_MARKERS,
        forbidden_prefix="Phase 0 current-contrast doc still contains forbidden marker",
    )

    _validate_required_markers(
        errors=errors,
        rules=PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS,
        missing_prefix="Phase 0 closeout summary is missing required marker",
        missing_file_prefix="Phase 0 closeout summary artifact is missing",
        require_presence=False,
    )
    _validate_forbidden_markers(
        errors=errors,
        rules=PHASE0_CLOSEOUT_SUMMARY_FORBIDDEN_MARKERS,
        forbidden_prefix="Phase 0 closeout summary still contains forbidden marker",
    )

    phase_scoped_review_bundles = _phase_scoped_review_bundles(errors)
    phase_scoped_plan_records = _phase_scoped_plan_records(errors)
    phase_scoped_evidence_records = _phase_scoped_evidence_records(
        errors=errors,
        plan_records=phase_scoped_plan_records,
    )
    _validate_summary_only_artifact_headers(errors)
    _validate_summary_only_review_exceptions(
        errors=errors,
        review_bundles=phase_scoped_review_bundles,
    )
    for plan_record in phase_scoped_plan_records:
        if _extract_summary_only(plan_record.plan_path, plan_record.plan_text, errors) != "no":
            errors.append(
                f"{plan_record.plan_path.relative_to(ROOT)} must use `summary-only: no` "
                "for authoritative phase-scoped closure artifacts"
            )
        _validate_delegated_slice_grammar(
            artifact_path=plan_record.plan_path,
            artifact_text=plan_record.plan_text,
            errors=errors,
        )
        _validate_artifact_work_package_ids(
            artifact_path=plan_record.plan_path,
            artifact_text=plan_record.plan_text,
            current_phase_page=plan_record.current_phase_page,
            errors=errors,
        )
        _validate_phase0_current_doc_unlocks(
            artifact_path=plan_record.plan_path,
            artifact_text=plan_record.plan_text,
            selected_phase=plan_record.selected_phase,
            errors=errors,
        )

    for evidence_record in phase_scoped_evidence_records:
        if (
            _extract_summary_only(
                evidence_record.evidence_path,
                evidence_record.evidence_text,
                errors,
            )
            != "no"
        ):
            errors.append(
                f"{evidence_record.evidence_path.relative_to(ROOT)} must use "
                "`summary-only: no` for authoritative phase-scoped closure artifacts"
            )
        _validate_delegated_slice_grammar(
            artifact_path=evidence_record.evidence_path,
            artifact_text=evidence_record.evidence_text,
            errors=errors,
        )
        _validate_artifact_work_package_ids(
            artifact_path=evidence_record.evidence_path,
            artifact_text=evidence_record.evidence_text,
            current_phase_page=evidence_record.approved_plan_record.current_phase_page,
            errors=errors,
        )
        _validate_phase0_current_doc_unlocks(
            artifact_path=evidence_record.evidence_path,
            artifact_text=evidence_record.evidence_text,
            selected_phase=evidence_record.selected_phase,
            errors=errors,
        )
        _validate_evidence_artifact_paths(
            evidence_record=evidence_record,
            errors=errors,
        )

    for review_bundle in phase_scoped_review_bundles:
        if (
            _extract_summary_only(
                review_bundle.review_path,
                review_bundle.review_text,
                errors,
            )
            != "no"
        ):
            errors.append(
                f"{review_bundle.review_path.relative_to(ROOT)} must use `summary-only: no` "
                "for authoritative phase-scoped closure artifacts"
            )
        _validate_delegated_slice_grammar(
            artifact_path=review_bundle.review_path,
            artifact_text=review_bundle.review_text,
            errors=errors,
        )
        _validate_artifact_work_package_ids(
            artifact_path=review_bundle.review_path,
            artifact_text=review_bundle.review_text,
            current_phase_page=review_bundle.current_phase_page,
            errors=errors,
        )
        _validate_phase0_current_doc_unlocks(
            artifact_path=review_bundle.review_path,
            artifact_text=review_bundle.review_text,
            selected_phase=review_bundle.selected_phase,
            errors=errors,
        )

    api_appendix_headings = _api_appendix_headings()
    for heading in REQUIRED_API_APPENDIX_HEADINGS:
        if heading not in api_appendix_headings:
            errors.append(f"api-schema-appendix.md is missing required heading: {heading}")

    all_docs_text = "\n".join(
        path.read_text(encoding="utf-8") for path in redesign_and_execution_paths
    )
    for rule in DEFAULT_ROOT_RULES:
        count = all_docs_text.count(rule)
        if count != 1:
            errors.append(
                "default-root rule must appear exactly once across redesign/execution "
                f"docs: {rule} (found {count})"
            )

    wrong_wrapper_route = (
        '"What exact wrapper fields differ by send mode?" -> '
        "[Prompt render and dispatch audit](../prompt-layer/render-and-persistence.md)"
    )
    if wrong_wrapper_route in all_docs_text:
        errors.append(
            "continuity router still points wrapper-field questions to render-and-persistence.md"
        )

    if "current_refs: [ref_id, ...]" in all_docs_text:
        errors.append(
            "target docs still contain `current_refs: [ref_id, ...]`; `current_refs` "
            "must mean resolved_ref[] everywhere"
        )

    if (
        "treat the current phase page as the sole phase-local implementation contract"
        not in all_docs_text
    ):
        errors.append("execution pack is missing the phase-page-authoritative execution rule")

    for path in unreferenced_redesign_paths:
        errors.append(
            f"execution pack does not link redesign coverage for {path.relative_to(ROOT)}"
        )

    phase2_page = (
        DOCS_ROOT / "execution" / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md"
    )
    if phase2_page.exists():
        phase2_text = phase2_page.read_text(encoding="utf-8")
        implementation_surfaces = _section_slice(
            phase2_text,
            "## Implementation surfaces",
            "## Do not edit / defer surfaces",
        )
        for marker in FORBIDDEN_MARKERS[phase2_page]:
            if marker in implementation_surfaces:
                errors.append(
                    "phase-2-prompt-manifest-artifact-bootstrap.md still assigns "
                    f"Phase 2 ownership to {marker}"
                )

    lock_map = DOCS_ROOT / "execution" / "maps" / "file-priority-map.md"
    if lock_map.exists():
        lock_map_text = lock_map.read_text(encoding="utf-8")
        missing_phase0_markers = _missing_section_markers(
            lock_map_text,
            start_heading="## Phase 0",
            end_heading="## Phase 0.5",
            markers=[
                "`docs/execution/README.md`",
                "`docs/execution/maps/*`",
            ],
        )
        for marker in missing_phase0_markers:
            errors.append(f"file-priority-map.md Phase 0 section must own {marker}")
        missing_phase1_markers = _missing_section_markers(
            lock_map_text,
            start_heading="## Phase 1",
            end_heading="## Phase 2",
            markers=[
                "`apps/api/app/cli.py` only when Phase 1-owned persistence truth must be reachable",
                "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
                "narrow `pyproject.toml` package-data entries",
                "shipped-path schema install, upgrade, and reset proof for SQLite "
                "when definition persistence truth changes",
            ],
        )
        for marker in missing_phase1_markers:
            errors.append(
                f"file-priority-map.md Phase 1 section is missing required marker: {marker}"
            )
        phase2_section = _section_slice(lock_map_text, "## Phase 2", "## Phase 3")
        phase3_section = _section_slice(lock_map_text, "## Phase 3", "## Phase 4A")
        missing_phase3_markers = _missing_section_markers(
            lock_map_text,
            start_heading="## Phase 3",
            end_heading="## Phase 4A",
            markers=[
                "`apps/api/app/cli.py` only when Phase 3-owned runtime persistence "
                "truth must be reachable",
                "shipped-path schema install, upgrade, and reset proof for SQLite "
                "when runtime persistence truth changes",
            ],
        )
        for marker in missing_phase3_markers:
            errors.append(
                f"file-priority-map.md Phase 3 section is missing required marker: {marker}"
            )
        for marker in FORBIDDEN_MARKERS[phase2_page]:
            if marker in phase2_section:
                errors.append(f"file-priority-map.md still assigns Phase 2 ownership to {marker}")
        if "`apps/api/app/schemas/runtime.py`" not in phase3_section:
            errors.append(
                "file-priority-map.md Phase 3 section must own `apps/api/app/schemas/runtime.py`"
            )

    for path, line_numbers in sorted(legacy_heading_hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        errors.append(f"{path.relative_to(ROOT)} contains `{LEGACY_HEADING}` at line(s): {joined}")

    for path, line_numbers in sorted(compatibility_status_hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        errors.append(
            f"{path.relative_to(ROOT)} contains `{COMPATIBILITY_STATUS}` at line(s): {joined}"
        )

    for deleted_name, locations in sorted(deleted_filename_hits.items()):
        for path, line_numbers in locations:
            errors.append(
                f"{path.relative_to(ROOT)} still references deleted router "
                f"`{deleted_name}` at line(s): "
                f"{', '.join(str(n) for n in line_numbers)}"
            )

    redesign_readme = DOCS_ROOT / "redesign" / "README.md"
    if redesign_readme.exists():
        redesign_readme_text = redesign_readme.read_text(encoding="utf-8")
        if SEARCH_ONLY_COMPATIBILITY_SECTION in redesign_readme_text:
            errors.append(
                f"{redesign_readme.relative_to(ROOT)} still contains the "
                f"`{SEARCH_ONLY_COMPATIBILITY_SECTION}` section"
            )

    for violation in formatter_violations:
        errors.append(
            f"{violation.path.relative_to(ROOT)} needs markdown unwrap formatting "
            f"at line {violation.line}"
        )

    prompt_validation = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "docs" / "prompt_catalog_tools.py"), "validate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if prompt_validation.returncode != 0:
        errors.append("prompt catalog validation failed")
        if prompt_validation.stdout.strip():
            errors.append(prompt_validation.stdout.strip())
        if prompt_validation.stderr.strip():
            errors.append(prompt_validation.stderr.strip())

    if debug_inventory:
        _print_inventory(
            legacy_heading_hits=legacy_heading_hits,
            compatibility_status_hits=compatibility_status_hits,
            deleted_filename_hits=deleted_filename_hits,
            formatter_violations=formatter_violations,
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Docs freeze validation passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=["validate", "inventory"], default="validate")
    parser.add_argument("--debug-inventory", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "inventory":
        _print_inventory(
            legacy_heading_hits=_legacy_heading_hits(),
            compatibility_status_hits=_compatibility_status_hits(),
            deleted_filename_hits=_deleted_filename_hits(),
            formatter_violations=_markdown_formatter_violations(),
        )
        return 0
    return validate(debug_inventory=args.debug_inventory)


if __name__ == "__main__":
    raise SystemExit(main())
