from __future__ import annotations

import argparse
import re
import subprocess
import sys
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
        "any checklist explicitly required by the current phase page was completed",
        "required supporting redesign reads named by the phase page were reread",
        "required current-contrast pages named by the phase page were reread",
        "required examples and diagrams named by the phase page were reviewed",
        "required SQLite, Postgres+Docker, package, or reset verification lanes",
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
    redesign_and_execution_paths = list((DOCS_ROOT / "redesign").rglob("*.md")) + list(
        (DOCS_ROOT / "execution").rglob("*.md")
    )
    legacy_heading_hits = _legacy_heading_hits()
    compatibility_status_hits = _compatibility_status_hits()
    deleted_filename_hits = _deleted_filename_hits()
    formatter_violations = _markdown_formatter_violations()
    unreferenced_redesign_paths = _unreferenced_redesign_paths()

    for path in redesign_and_execution_paths:
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
            "continuity router still points wrapper-field questions to "
            "render-and-persistence.md"
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
            "execution pack does not link redesign coverage for "
            f"{path.relative_to(ROOT)}"
        )

    phase2_page = (
        DOCS_ROOT
        / "execution"
        / "phases"
        / "phase-2-prompt-manifest-artifact-bootstrap.md"
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
        phase2_section = _section_slice(lock_map_text, "## Phase 2", "## Phase 3")
        phase3_section = _section_slice(lock_map_text, "## Phase 3", "## Phase 4A")
        for marker in FORBIDDEN_MARKERS[phase2_page]:
            if marker in phase2_section:
                errors.append(
                    "file-priority-map.md still assigns Phase 2 ownership to "
                    f"{marker}"
                )
        if "`apps/api/app/schemas/runtime.py`" not in phase3_section:
            errors.append(
                "file-priority-map.md Phase 3 section must own "
                "`apps/api/app/schemas/runtime.py`"
            )

    for path, line_numbers in sorted(legacy_heading_hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        errors.append(
            f"{path.relative_to(ROOT)} contains `{LEGACY_HEADING}` at line(s): {joined}"
        )

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
