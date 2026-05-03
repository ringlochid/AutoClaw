from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from format_markdown import FormatterViolation, collect_violations, iter_maintained_markdown_files


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
        "Where are exhaustive API request/response details?",
        "Where is the frozen `autoclaw definitions import ...` contract?",
        "Should we rewrite from scratch or salvage first?",
    ],
    DOCS_ROOT / "execution" / "how-to" / "use-this-pack-for-implementation.md": [
        "## Fast path",
        "## Appendix-owner rule",
        "use the current phase page as the sole phase-local contract",
    ],
    DOCS_ROOT / "execution" / "phases" / "overview.md": [
        "## Phase authority rule",
        "the current phase page is the sole phase-local implementation contract",
        "Phase 0.5",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-0.5-cleanup-and-salvage-baseline.md": [
        "fresh-baseline DB/schema reset",
        "one new redesign baseline migration",
        "plugin near-greenfield rebuild",
        "Cleanup and salvage checklist",
        "Repo salvage matrix",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-3-runtime-parent-review-and-replan.md": [
        "Assignment contract",
        "Workflow schema appendix",
        "API schema appendix",
    ],
    DOCS_ROOT / "execution" / "phases" / "phase-5-ingest-api-cli-package-and-cutover.md": [
        "API schema appendix",
        "autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]",
        "zero-arg `autoclaw definitions import [--overwrite reject|allow_new_revision]` for shallow current-working-directory scan only",
    ],
    DOCS_ROOT / "execution" / "gates" / "phase-implementation-prompts.md": [
        "treat the current phase page as the sole phase-local implementation contract",
        "autoclaw definitions import ...",
        "workflow-schema-appendix.md",
        "api-schema-appendix.md",
        "prompt-resource-usage-appendix.md",
        "## Phase-plan prompt",
        "selected current phase page",
        "do not mirror unrelated phase pages",
    ],
    DOCS_ROOT / "execution" / "gates" / "cleanup-and-salvage-checklist.md": [
        "fresh-baseline schema reset",
        "plugin rebuild boundary",
        "rewrite to redesign contract",
        "delete as stale-contract coverage",
    ],
    DOCS_ROOT / "execution" / "gates" / "supporting-prompts.md": [
        "use any appendix owners named by the current phase page",
        "update named appendix owners when the changed behavior affects exhaustive",
        "Cleanup and salvage classification for this phase",
        "Plugin rebuild boundary review",
    ],
    DOCS_ROOT / "execution" / "gates" / "verification-prompts.md": [
        "Re-read any appendix owners named by the current phase page",
        "did the current phase page remain the phase-local authority?",
        "were named appendix owners updated when exhaustive detail changed?",
        "Confirm that any phase-local required checklist was completed.",
    ],
    DOCS_ROOT / "execution" / "gates" / "phase-done-gate.md": [
        "the current phase page remained the sole phase-local contract",
        "named appendix owners were updated when exhaustive API/schema/prompt detail changed",
        "reusable prompts, gates, or checklists touched for the phase still point back to the current phase page",
        "any checklist explicitly required by the current phase page was completed",
    ],
    DOCS_ROOT / "execution" / "gates" / "mandatory-review-gate.md": [
        "the current phase page still acts as the phase-local contract owner",
        "named appendix owners were updated when exhaustive API/schema/prompt detail changed",
        "reusable execution prompts or checklists touched by the phase still reference the phase page",
        "any checklist explicitly required by the current phase page was completed",
    ],
    DOCS_ROOT / "execution" / "gates" / "docs-answer-sourcing-checklist.md": [
        "I checked the named appendix owner when exact API/schema/prompt detail mattered",
        "I treated the current phase page as the sole phase-local execution contract",
    ],
    DOCS_ROOT / "execution" / "gates" / "README.md": [
        "Cleanup and salvage checklist",
    ],
    DOCS_ROOT / "execution" / "gates" / "reset-gate.md": [
        "Phase 0.5 cleanup and salvage always requires this gate",
        "reseed/bootstrap procedure is documented when reset would leave the system empty",
    ],
    DOCS_ROOT / "execution" / "gates" / "rewrite-done-gate.md": [
        "shared Codex execution policy and shared implementation quickstart",
        "phase pages act as the sole phase-local execution contract owners",
        "execution routing points implementers to appendix owners for exhaustive API/schema/prompt detail",
        "reusable execution prompts are reference-first rather than large mirrored phase summaries",
        "cleanup-and-salvage checklist",
        "repo salvage matrix",
    ],
    DOCS_ROOT / "execution" / "maps" / "file-priority-map.md": [
        "authoritative appendix owners:",
        "docs/redesign/interfaces/api-schema-appendix.md",
        "docs/redesign/workflows/workflow-schema-appendix.md",
        "docs/redesign/prompt-layer/prompt-resource-usage-appendix.md",
        "phase-0.5-cleanup-and-salvage-baseline.md",
        "cleanup-and-salvage-checklist.md",
        "repo-salvage-matrix.md",
    ],
    DOCS_ROOT / "execution" / "maps" / "repo-salvage-matrix.md": [
        "plugin rebuild",
        "current Alembic history",
        "keep",
        "rewrite in place",
        "delete",
        "quarantine support-only",
    ],
    DOCS_ROOT / "execution" / "how-to" / "reset-db-schema-and-package-state.md": [
        "whether reseed/bootstrap was required",
        "Phase 0.5 is the explicit cleanup phase where old schema truth may be",
    ],
    DOCS_ROOT / "execution" / "how-to" / "track-a-redesign-bug.md": [
        "phase_0_5",
        "cleanup-baseline issue",
    ],
    DOCS_ROOT / "execution" / "how-to" / "triage-a-failing-phase-or-workflow-lane.md": [
        "cleanup baseline issue",
        "Phase 0.5 cleanup and salvage baseline",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "definition-ingest-and-upload-contract.md": [
        "autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]",
        "zero-arg `autoclaw definitions import` is the canonical shallow current-working-directory scan/import path",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "cli-surface-and-operator-workflows.md": [
        "`autoclaw definitions ...`",
        "autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]",
        "zero-arg `autoclaw definitions import` is a shallow current-working-directory scan only",
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
                print(f"  - {path.relative_to(ROOT)}: lines {', '.join(str(n) for n in line_numbers)}")
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
    redesign_and_execution_paths = list((DOCS_ROOT / "redesign").rglob("*.md")) + list((DOCS_ROOT / "execution").rglob("*.md"))
    legacy_heading_hits = _legacy_heading_hits()
    compatibility_status_hits = _compatibility_status_hits()
    deleted_filename_hits = _deleted_filename_hits()
    formatter_violations = _markdown_formatter_violations()

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

    api_appendix_headings = _api_appendix_headings()
    for heading in REQUIRED_API_APPENDIX_HEADINGS:
        if heading not in api_appendix_headings:
            errors.append(f"api-schema-appendix.md is missing required heading: {heading}")

    all_docs_text = "\n".join(path.read_text(encoding="utf-8") for path in redesign_and_execution_paths)
    for rule in DEFAULT_ROOT_RULES:
        count = all_docs_text.count(rule)
        if count != 1:
            errors.append(f"default-root rule must appear exactly once across redesign/execution docs: {rule} (found {count})")

    wrong_wrapper_route = '"What exact wrapper fields differ by send mode?" -> [Prompt render and dispatch audit](../prompt-layer/render-and-persistence.md)'
    if wrong_wrapper_route in all_docs_text:
        errors.append("continuity router still points wrapper-field questions to render-and-persistence.md")

    if "current_refs: [ref_id, ...]" in all_docs_text:
        errors.append("target docs still contain `current_refs: [ref_id, ...]`; `current_refs` must mean resolved_ref[] everywhere")

    if "treat the current phase page as the sole phase-local implementation contract" not in all_docs_text:
        errors.append("execution pack is missing the phase-page-authoritative execution rule")

    for path, line_numbers in sorted(legacy_heading_hits.items()):
        errors.append(f"{path.relative_to(ROOT)} contains `{LEGACY_HEADING}` at line(s): {', '.join(str(n) for n in line_numbers)}")

    for path, line_numbers in sorted(compatibility_status_hits.items()):
        errors.append(f"{path.relative_to(ROOT)} contains `{COMPATIBILITY_STATUS}` at line(s): {', '.join(str(n) for n in line_numbers)}")

    for deleted_name, locations in sorted(deleted_filename_hits.items()):
        for path, line_numbers in locations:
            errors.append(
                f"{path.relative_to(ROOT)} still references deleted router `{deleted_name}` at line(s): {', '.join(str(n) for n in line_numbers)}"
            )

    redesign_readme = DOCS_ROOT / "redesign" / "README.md"
    if redesign_readme.exists():
        redesign_readme_text = redesign_readme.read_text(encoding="utf-8")
        if SEARCH_ONLY_COMPATIBILITY_SECTION in redesign_readme_text:
            errors.append(f"{redesign_readme.relative_to(ROOT)} still contains the `{SEARCH_ONLY_COMPATIBILITY_SECTION}` section")

    for violation in formatter_violations:
        errors.append(f"{violation.path.relative_to(ROOT)} needs markdown unwrap formatting at line {violation.line}")

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
        _print_inventory()
        return 0
    return validate(debug_inventory=args.debug_inventory)


if __name__ == "__main__":
    raise SystemExit(main())
