from __future__ import annotations

from ..paths import EXECUTION_ROOT

EXECUTION_REQUIRED_MARKERS = {
    EXECUTION_ROOT / "maps" / "current-schema-route-and-plugin-migration-appendix.md": [
        "support-only lane",
        "Plugin tool migration",
        "Current schema, route, and plugin migration appendix",
    ],
    EXECUTION_ROOT / "maps" / "README.md": [
        "Current schema, route, and plugin migration appendix",
    ],
    EXECUTION_ROOT / "maps" / "current-to-target-mapping.md": [
        "Detailed appendix",
        "current-schema-route-and-plugin-migration-appendix.md",
    ],
    EXECUTION_ROOT / "README.md": [
        "## Fast path",
        "Design-to-code landing map",
        "required supporting design reads",
        "required current-contrast pages",
        "Where are exhaustive API request/response details?",
        "Where is the frozen `autoclaw definitions import ...` contract?",
        "Should we rewrite from scratch or hard reset first?",
    ],
    EXECUTION_ROOT / "how-to" / "use-this-pack-for-implementation.md": [
        "## Fast path",
        "## Appendix-owner rule",
        "use the current phase page as the sole phase-local contract",
        "Design-to-code landing map",
        "required supporting design reads",
        "required current-contrast pages",
        "required examples and diagrams",
        (
            "layer index page, machine catalog, generated inventory, or "
            "reference-only historical search router"
        ),
        "## Completeness rule",
    ],
    EXECUTION_ROOT / "phases" / "overview.md": [
        "## Phase authority rule",
        "the current phase page is the sole phase-local implementation contract",
        "Phase 0.5",
        "required supporting design reads",
        "required current-contrast pages",
        "required examples or diagrams",
    ],
    EXECUTION_ROOT / "phases" / "phase-0-docs-contract-freeze-and-setup.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "## Required examples and diagrams",
        "phase-boundary, read-coverage, and design-to-code landing maps",
        (
            "every phase page names required supporting design reads, "
            "required current-contrast reads, and required examples or "
            "diagrams"
        ),
        "`ruff check scripts/docs`",
        "`mypy scripts/docs`",
    ],
    EXECUTION_ROOT / "phases" / "phase-0.5-cleanup-and-salvage-baseline.md": [
        "## Required supporting design reads",
        "fresh-baseline DB/state reset",
        "no carried migration history or reset-only schema survives as design authority",
        "plugin near-greenfield rebuild",
        "Cleanup and salvage checklist",
        "Repo salvage matrix",
        "## Required current contrast reads",
        "stale generated build or dist mirrors do not survive as typecheck or schema authority",
        "Historical prompt and artifact layers",
        "Findings",
    ],
    EXECUTION_ROOT / "phases" / "phase-1-authoring-and-compiler-rewrite.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "Definition and task-compose YAML contract",
        "Definitions compiler and launch",
        "## Required examples and diagrams",
        "existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` only",
        "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
        "narrow `pyproject.toml` package-data entries",
        "shipped-path schema install, upgrade, and reset proof for SQLite",
    ],
    EXECUTION_ROOT / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "Prompt layer and worker delivery",
        "## Required examples and diagrams",
        "prompt-catalog generate/validate checks",
        (
            "runtime persistence truth for assignments, attempts, checkpoints, "
            "and currentness remains deferred to Phase 3"
        ),
        "Prompt-layer front door",
        "Prompt field renderers",
        "Prompt machine contract",
        "Prompt catalog machine surface",
        "Generated prompt inventory",
        "Runtime rule blocks",
        "System and provider block",
        "Validation and reject blocks",
    ],
    EXECUTION_ROOT / "phases" / "phase-3-runtime-parent-review-and-replan.md": [
        "Assignment contract",
        "Workflow schema appendix",
        "API schema appendix",
        "## Required supporting design reads",
        "## Required current contrast reads",
        "Runtime control plane",
        "`apps/api/app/cli.py` when Phase 3-owned runtime persistence truth must be",
        "shipped install, upgrade, and reset paths create the landed runtime schema",
        "SQLite local smoke",
        "Postgres + Docker strong verification",
    ],
    EXECUTION_ROOT / "phases" / "phase-4a-openclaw-gateway-session-and-continuity.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "## Required examples and diagrams",
        "Recover a provider session",
        "API trust lanes",
        "Runtime lane separation rationale",
        "Prompt-layer front door",
        "System and provider block",
        "Runtime rule blocks",
        "Validation and reject blocks",
        "Generated prompt inventory",
    ],
    EXECUTION_ROOT / "phases" / "phase-4b-watchdog-operator-plugin-and-support-state.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "## Required examples and diagrams",
        "Operator definition and role boundary",
        "Use the current OpenClaw bridge plugin",
        "Runtime lane separation rationale",
        "Provider, worker, and operator boundary",
        "Recover a provider session",
    ],
    EXECUTION_ROOT / "phases" / "phase-5a-definition-ingest-api-and-cli.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "API surface and route map",
        "API machine catalog",
        "SQLite local smoke",
        "Postgres + Docker strong verification",
    ],
    EXECUTION_ROOT / "phases" / "phase-5b-packaging-release-and-docs-cutover.md": [
        "## Required supporting design reads",
        "## Required current contrast reads",
        "Packaging CLI and install",
        "Distribution and database support matrix",
        "SQLite local smoke verification",
        "Postgres + Docker strong verification",
    ],
    EXECUTION_ROOT / "gates" / "phase-implementation-prompts.md": [
        "treat the current phase page as the sole phase-local implementation contract",
        "autoclaw definitions import ...",
        "workflow-schema-appendix.md",
        "api-schema-appendix.md",
        "prompt-resource-usage-appendix.md",
        "required supporting design reads",
        "required current-contrast pages",
        "required examples and diagrams",
        "design-code-landing-map.md",
        "## Phase-plan prompt",
        "selected current phase page",
        "do not mirror unrelated phase pages",
    ],
    EXECUTION_ROOT / "gates" / "cleanup-and-salvage-checklist.md": [
        "fresh-baseline schema reset",
        "plugin rebuild boundary",
        "retain infra shell only",
        "delete as stale-contract coverage",
    ],
    EXECUTION_ROOT / "gates" / "supporting-prompts.md": [
        "use any appendix owners named by the current phase page",
        "update named appendix owners when the changed behavior affects exhaustive",
        "Hard-reset classification for this phase",
        "Plugin rebuild boundary review",
        (
            "required supporting design reads, required current-contrast "
            "reads, and required examples and diagrams"
        ),
        "SQLite, Postgres+Docker, package, or reset verification lane",
    ],
    EXECUTION_ROOT / "gates" / "verification-prompts.md": [
        "required supporting design reads",
        "Re-read any appendix owners named by the current phase page",
        "did the current phase page remain the phase-local authority?",
        "were named appendix owners updated when exhaustive detail changed?",
        "Confirm that any phase-local required checklist was completed.",
    ],
    EXECUTION_ROOT / "gates" / "phase-done-gate.md": [
        "the current phase page remained the sole phase-local contract",
        "named appendix owners were updated when exhaustive API/schema/prompt detail changed",
        (
            "reusable prompts, gates, or checklists touched for the phase "
            "still point back to the current phase page"
        ),
        "any checklist explicitly required by the current phase page was completed",
        "required supporting design reads named by the phase page were used",
        "required current-contrast pages named by the phase page were used",
        "required examples and diagrams named by the phase page were read",
        "SQLite, Postgres+Docker, package, or reset verification lane",
    ],
    EXECUTION_ROOT / "gates" / "mandatory-review-gate.md": [
        "the current phase page still acts as the phase-local contract owner",
        "named appendix owners were updated when exhaustive API/schema/prompt detail changed",
        (
            "reusable execution prompts or checklists touched by the phase "
            "still reference the phase page"
        ),
        "any earlier-phase prerequisite truth that this phase depends on was actually landed",
        "any checklist explicitly required by the current phase page was completed",
        "required supporting design reads named by the phase page were reread",
        "required current-contrast pages named by the phase page were reread",
        "required examples and diagrams named by the phase page were reviewed",
        "required SQLite, Postgres+Docker, package, or reset verification lanes",
        "install, upgrade, or reset proof does not rely on test-only schema creation",
    ],
    EXECUTION_ROOT / "gates" / "docs-answer-sourcing-checklist.md": [
        "I checked the named appendix owner when exact API/schema/prompt detail mattered",
        (
            "I checked any required supporting design reads explicitly named "
            "by the current phase page"
        ),
        "I treated the current phase page as the sole phase-local execution contract",
    ],
    EXECUTION_ROOT / "gates" / "README.md": [
        "Cleanup and salvage checklist",
    ],
    EXECUTION_ROOT / "gates" / "reset-gate.md": [
        "Phase 0.5 cleanup and salvage always requires this gate",
        "reseed/bootstrap procedure is documented when reset would leave the system empty",
        "install or upgrade proof used the shipped path rather than test-only schema creation",
        "SQLite smoke ran",
        "Postgres + Docker strong verification ran",
    ],
    EXECUTION_ROOT / "gates" / "rewrite-done-gate.md": [
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
    EXECUTION_ROOT / "maps" / "file-priority-map.md": [
        "authoritative appendix owners:",
        "docs-internal/design/v1/interfaces/api-schema-appendix.md",
        "docs-internal/design/v1/workflows/workflow-schema-appendix.md",
        "docs-internal/design/v1/prompt-layer/prompt-resource-usage-appendix.md",
        "repo code under `apps/**`",
        "repo tests under `apps/api/tests/**`",
        "`docs/**`",
        "targeted prompt validation tooling under `scripts/docs/*`",
        "`apps/api/app/schemas/runtime/__init__.py`",
        "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
        "narrow `pyproject.toml` package-data entries",
    ],
    EXECUTION_ROOT / "maps" / "design-code-landing-map.md": [
        "## Coverage classes",
        "## Cross-cutting secondary coverage",
        "## Phase 0",
        "## Phase 5B",
        "Decisions front door",
        "How-to front door",
        "Tutorials front door",
        "Findings",
        "docs-internal/design/v1/prompt-layer/contract.md",
        "docs-internal/design/v1/architecture/runtime-database-and-object-contract.md",
        "docs-internal/design/v1/interfaces/testing-and-release-checklist.md",
        "package-contained seed mirrors under `apps/api/app/resources/definitions/**`",
        "narrow `pyproject.toml` package-data entries for those seed mirrors",
        "Postgres + Docker strong verification",
        "Prompt-layer front door",
        "Prompt catalog machine surface",
        "System and provider block",
        "Runtime rule blocks",
        "Validation and reject blocks",
        "historical dispatch-family packs",
    ],
    EXECUTION_ROOT / "maps" / "repo-salvage-matrix.md": [
        "plugin rebuild",
        "migration roots and mirrors",
        "retain infra shell only",
        "delete now",
    ],
    EXECUTION_ROOT / "how-to" / "reset-db-schema-and-package-state.md": [
        "whether the baseline was intentionally left empty",
        "Phase 0.5 is the explicit cleanup phase where old schema truth may be",
    ],
    EXECUTION_ROOT / "how-to" / "track-a-design-bug.md": [
        "phase_0_5",
        "cleanup-baseline issue",
    ],
    EXECUTION_ROOT / "how-to" / "triage-a-failing-phase-or-workflow-lane.md": [
        "cleanup baseline issue",
        "Phase 0.5 total code hard reset baseline",
    ],
}

EXECUTION_FORBIDDEN_MARKERS = {
    EXECUTION_ROOT / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md": [
        "`apps/api/app/schemas/runtime/__init__.py`",
        "`apps/api/app/db/models/runtime.py`",
    ],
}
