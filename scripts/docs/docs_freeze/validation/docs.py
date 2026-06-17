from __future__ import annotations

from pathlib import Path

from scripts.docs.prompt_catalog import (
    load_catalog,
    render_generated_examples_md,
    render_inventory_md,
    validate_catalog,
)

from ..content.rules import (
    BANNED_PATTERN_EXCLUDED_PATHS,
    BANNED_PATTERNS,
    COMPATIBILITY_STATUS,
    FORBIDDEN_MARKERS,
    FORBIDDEN_ROOT_FILES,
    LEGACY_HEADING,
    REQUIRED_MARKERS,
    SEARCH_ONLY_COMPATIBILITY_SECTION,
)
from ..execution_records import (
    validate_forbidden_markers,
    validate_required_markers,
)
from ..paths import DESIGN_ROOT, EXECUTION_ROOT, ROOT
from ..phase_records.rules import (
    DEFAULT_ROOT_RULES,
    PHASE0_AUTHORITY_FORBIDDEN_MARKERS,
    PHASE0_AUTHORITY_REQUIRED_MARKERS,
    PHASE0_CLOSEOUT_SUMMARY_FORBIDDEN_MARKERS,
    PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS,
    PHASE0_CURRENT_DOC_FORBIDDEN_MARKERS,
    PHASE0_CURRENT_DOC_REQUIRED_MARKERS,
    REQUIRED_API_APPENDIX_HEADINGS,
)
from ..sections import api_appendix_headings, missing_section_markers, section_slice
from .inventory import DocsFreezeInventory


def validate_text_rules(errors: list[str], maintained_markdown_paths: list[Path]) -> None:
    for path in maintained_markdown_paths:
        if path in BANNED_PATTERN_EXCLUDED_PATHS:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for pattern in BANNED_PATTERNS:
            if pattern in text:
                errors.append(f"{path.relative_to(ROOT)} still contains banned text: {pattern}")

    for forbidden in FORBIDDEN_ROOT_FILES:
        if forbidden.exists():
            errors.append(f"forbidden root file still exists: {forbidden.relative_to(ROOT)}")


def validate_marker_rules(errors: list[str]) -> None:
    validate_required_docs_markers(errors)
    validate_required_markers(
        errors=errors,
        rules=PHASE0_AUTHORITY_REQUIRED_MARKERS,
        missing_prefix="Phase 0 execution authority surface is missing required marker",
        missing_file_prefix="Phase 0 execution authority surface is missing",
        require_presence=True,
    )
    validate_forbidden_markers(
        errors=errors,
        rules=PHASE0_AUTHORITY_FORBIDDEN_MARKERS,
        forbidden_prefix="Phase 0 execution authority surface still contains forbidden marker",
    )
    validate_required_markers(
        errors=errors,
        rules=PHASE0_CURRENT_DOC_REQUIRED_MARKERS,
        missing_prefix="Phase 0 current-contrast doc is missing required marker",
        missing_file_prefix="Phase 0 current-contrast doc is missing",
        require_presence=True,
    )
    validate_forbidden_markers(
        errors=errors,
        rules=PHASE0_CURRENT_DOC_FORBIDDEN_MARKERS,
        forbidden_prefix="Phase 0 current-contrast doc still contains forbidden marker",
    )
    validate_required_markers(
        errors=errors,
        rules=PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS,
        missing_prefix="Phase 0 aggregate summary is missing required marker",
        missing_file_prefix="Phase 0 aggregate summary artifact is missing",
        require_presence=False,
    )
    validate_forbidden_markers(
        errors=errors,
        rules=PHASE0_CLOSEOUT_SUMMARY_FORBIDDEN_MARKERS,
        forbidden_prefix="Phase 0 closeout summary still contains forbidden marker",
    )


def validate_required_docs_markers(errors: list[str]) -> None:
    for path, markers in REQUIRED_MARKERS.items():
        if not path.exists():
            errors.append(f"required docs file is missing: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{path.relative_to(ROOT)} is missing required marker: {marker}")

    for path, forbidden_markers in FORBIDDEN_MARKERS.items():
        if not path.exists():
            errors.append(f"required docs file is missing: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            if marker in text:
                errors.append(f"{path.relative_to(ROOT)} still contains forbidden marker: {marker}")


def validate_docs_rules(
    *,
    errors: list[str],
    design_and_execution_paths: list[Path],
    inventory: DocsFreezeInventory,
) -> None:
    _validate_api_appendix_headings(errors)
    all_docs_text = _read_docs_text(design_and_execution_paths)
    _validate_default_root_rules(errors, all_docs_text)
    _validate_retired_docs_wording(errors, all_docs_text)
    _validate_inventory_doc_rule_issues(errors, inventory)
    _validate_design_readme_compat_section(errors)


def _validate_api_appendix_headings(errors: list[str]) -> None:
    appendix_headings = api_appendix_headings()
    for heading in REQUIRED_API_APPENDIX_HEADINGS:
        if heading not in appendix_headings:
            errors.append(f"api-schema-appendix.md is missing required heading: {heading}")


def _read_docs_text(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _validate_default_root_rules(errors: list[str], all_docs_text: str) -> None:
    for rule in DEFAULT_ROOT_RULES:
        count = all_docs_text.count(rule)
        if count != 1:
            errors.append(
                "default-root rule must appear exactly once across design/execution "
                f"docs: {rule} (found {count})"
            )


def _validate_retired_docs_wording(errors: list[str], all_docs_text: str) -> None:
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


def _validate_inventory_doc_rule_issues(
    errors: list[str],
    inventory: DocsFreezeInventory,
) -> None:
    for path in inventory.unreferenced_paths:
        errors.append(f"execution pack does not link design coverage for {path.relative_to(ROOT)}")
    for wording_issue in inventory.execution_program_wording_issues:
        errors.append(
            f"{wording_issue.path.relative_to(ROOT)} still contains execution-program wording "
            f"{wording_issue.label} at line {wording_issue.line}"
        )
    for heading_issue in inventory.public_doc_review_heading_issues:
        errors.append(
            f"{heading_issue.path.relative_to(ROOT)} must not use internal review heading "
            f"`{heading_issue.label}` at line {heading_issue.line}"
        )
    for path in inventory.current_doc_closeout_heading_issues:
        errors.append(
            f"{path.relative_to(ROOT)} is missing exact `## Evidence` or "
            "`## Verification`"
        )
    for path in inventory.public_reference_status_issues:
        errors.append(
            f"{path.relative_to(ROOT)} must use `Status: Reference` in the public reference tree"
        )
    for nav_issue in inventory.navigation_link_label_issues:
        errors.append(
            f"{nav_issue.doc_path.relative_to(ROOT)} uses filename-style link label "
            f"`{nav_issue.label}` for `{nav_issue.raw_target}` at line {nav_issue.line}"
        )
    for status_issue in inventory.status_issues:
        found_status = (
            status_issue.found_status if status_issue.found_status is not None else "<missing>"
        )
        allowed = ", ".join(f"`{status}`" for status in status_issue.allowed_statuses)
        errors.append(
            f"{status_issue.path.relative_to(ROOT)} uses `Status: {found_status}`; "
            f"allowed here: {allowed}"
        )
    for path, marker in inventory.public_reference_contrast_issues:
        errors.append(
            f"{path.relative_to(ROOT)} still contains public-reference-only "
            f"contrast marker: {marker}"
        )


def _validate_design_readme_compat_section(errors: list[str]) -> None:
    design_readme = DESIGN_ROOT / "README.md"
    if design_readme.exists():
        design_readme_text = design_readme.read_text(encoding="utf-8")
        if SEARCH_ONLY_COMPATIBILITY_SECTION in design_readme_text:
            errors.append(
                f"{design_readme.relative_to(ROOT)} still contains the "
                f"`{SEARCH_ONLY_COMPATIBILITY_SECTION}` section"
            )


def validate_lock_map_rules(errors: list[str]) -> None:
    phase2_page = EXECUTION_ROOT / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md"
    if phase2_page.exists():
        phase2_text = phase2_page.read_text(encoding="utf-8")
        implementation_surfaces = section_slice(
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

    lock_map = EXECUTION_ROOT / "maps" / "file-priority-map.md"
    if not lock_map.exists():
        return

    lock_map_text = lock_map.read_text(encoding="utf-8")
    validate_phase0_lock_map_markers(lock_map_text, errors)
    validate_phase1_lock_map_markers(lock_map_text, errors)
    validate_phase2_and_phase3_lock_map_markers(lock_map_text, errors)
    validate_phase6_and_phase7_lock_map_markers(lock_map_text, errors)


def validate_inventory_hits(
    *,
    errors: list[str],
    inventory: DocsFreezeInventory,
) -> None:
    for path, line_numbers in sorted(inventory.legacy_hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        errors.append(f"{path.relative_to(ROOT)} contains `{LEGACY_HEADING}` at line(s): {joined}")

    for path, line_numbers in sorted(inventory.compatibility_hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        errors.append(
            f"{path.relative_to(ROOT)} contains `{COMPATIBILITY_STATUS}` at line(s): {joined}"
        )

    for deleted_name, locations in sorted(inventory.deleted_hits.items()):
        for path, line_numbers in locations:
            errors.append(
                f"{path.relative_to(ROOT)} still references deleted router "
                f"`{deleted_name}` at line(s): "
                f"{', '.join(str(n) for n in line_numbers)}"
            )

    for issue in inventory.repo_path_issues:
        if issue.reason == "pseudo_repo_root":
            errors.append(
                f"{issue.doc_path.relative_to(ROOT)} references pseudo repo-root path "
                f"`{issue.raw_reference}` at line {issue.line}; rewrite it to "
                f"`{issue.normalized_reference}`"
            )
            continue
        errors.append(
            f"{issue.doc_path.relative_to(ROOT)} references missing repo path "
            f"`{issue.raw_reference}` at line {issue.line}"
        )

    for violation in inventory.formatter_violations:
        errors.append(
            "docs style blocker: "
            f"{violation.path.relative_to(ROOT)} needs markdown unwrap formatting "
            f"at line {violation.line}"
        )


def validate_prompt_catalog(errors: list[str]) -> None:
    try:
        prompt_catalog = load_catalog()
    except Exception as exc:
        errors.append(f"prompt catalog validation failed to load catalog: {exc}")
        return

    validate_generated_prompt_status_lines(prompt_catalog, errors)
    prompt_validation_errors = validate_catalog(prompt_catalog)
    for error in prompt_validation_errors:
        errors.append(f"prompt catalog validation failed: {error}")


def validate_generated_prompt_status_lines(
    prompt_catalog: dict[str, object],
    errors: list[str],
) -> None:
    expected_status = "Status: Reference"
    rendered_docs = (
        ("generated inventory", render_inventory_md(prompt_catalog)),
        ("generated rendered examples", render_generated_examples_md(prompt_catalog)),
    )
    for label, rendered_text in rendered_docs:
        status_line = next(
            (line.strip() for line in rendered_text.splitlines() if line.startswith("Status: ")),
            None,
        )
        if status_line == expected_status:
            continue
        found_status = status_line if status_line is not None else "<missing>"
        errors.append(
            f"prompt catalog validation failed: {label} uses `{found_status}`; "
            f"expected `{expected_status}`"
        )


def validate_phase0_lock_map_markers(lock_map_text: str, errors: list[str]) -> None:
    missing_phase0_markers = missing_section_markers(
        lock_map_text,
        start_heading="## Phase 0",
        end_heading="## Phase 0.5",
        markers=[
            "`docs-internal/execution/v1/README.md`",
            "`docs-internal/execution/v1/maps/*`",
        ],
    )
    for marker in missing_phase0_markers:
        errors.append(f"file-priority-map.md Phase 0 section must own {marker}")


def validate_phase1_lock_map_markers(lock_map_text: str, errors: list[str]) -> None:
    missing_phase1_markers = missing_section_markers(
        lock_map_text,
        start_heading="## Phase 1",
        end_heading="## Phase 2",
        markers=[
            (
                "`apps/api/src/autoclaw/interfaces/cli/**` only when Phase 1-owned "
                "persistence truth must be reachable"
            ),
            "package-contained seed mirrors under `apps/api/src/autoclaw/definitions/seeds/**`",
            "narrow `pyproject.toml` package-data entries",
            "shipped-path schema install, upgrade, and reset proof for SQLite "
            "when definition persistence truth changes",
        ],
    )
    for marker in missing_phase1_markers:
        errors.append(f"file-priority-map.md Phase 1 section is missing required marker: {marker}")


def validate_phase2_and_phase3_lock_map_markers(
    lock_map_text: str,
    errors: list[str],
) -> None:
    phase2_page = EXECUTION_ROOT / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md"
    phase2_section = section_slice(lock_map_text, "## Phase 2", "## Phase 3")
    phase3_section = section_slice(lock_map_text, "## Phase 3", "## Phase 4A")

    missing_phase3_markers = missing_section_markers(
        lock_map_text,
        start_heading="## Phase 3",
        end_heading="## Phase 4A",
        markers=[
            "`apps/api/src/autoclaw/interfaces/cli/**` only when Phase 3-owned runtime persistence "
            "truth must be reachable",
            "shipped-path schema install, upgrade, and reset proof for SQLite "
            "when runtime persistence truth changes",
        ],
    )
    for marker in missing_phase3_markers:
        errors.append(f"file-priority-map.md Phase 3 section is missing required marker: {marker}")
    for marker in FORBIDDEN_MARKERS[phase2_page]:
        if marker in phase2_section:
            errors.append(f"file-priority-map.md still assigns Phase 2 ownership to {marker}")
    if "`apps/api/src/autoclaw/runtime/contracts/__init__.py`" not in phase3_section:
        errors.append(
            "file-priority-map.md Phase 3 section must own "
            "`apps/api/src/autoclaw/runtime/contracts/__init__.py`"
        )


def validate_phase6_and_phase7_lock_map_markers(
    lock_map_text: str,
    errors: list[str],
) -> None:
    missing_phase6_markers = missing_section_markers(
        lock_map_text,
        start_heading="## Phase 6",
        end_heading="## Phase 7",
        markers=[
            "`apps/api/src/autoclaw/**` as it is introduced by the phase",
            "controller-truth mutator cleanup, source wait or continuity cleanup",
            "targeted proof tests under `apps/api/tests/**` when source movement",
            "`./.venv/bin/python -m scripts.docs.docs_freeze.cli` when "
            "`docs-internal/execution/v1/**`, `docs-internal/current/v1/**`, "
            "`docs/reference/**`, or `scripts/docs/docs_freeze/**` changes as "
            "Phase 6 collateral",
            "grouped-runner relayout, and proof-lane cleanup, which remain Phase 7-owned",
        ],
    )
    for marker in missing_phase6_markers:
        errors.append(f"file-priority-map.md Phase 6 section is missing required marker: {marker}")

    phase7_section = section_slice(
        lock_map_text,
        "## Phase 7",
        "### Phase 7 required tests and validators",
    )
    missing_phase7_markers = missing_section_markers(
        phase7_section,
        start_heading="### Phase 7 owned surfaces",
        end_heading="### Phase 7 required tests and validators",
        markers=[
            (
                "`apps/api/src/autoclaw/**` when removing execution-roadmap "
                "or internal-doc leak language"
            ),
            (
                "without taking ownership of broader Phase 6 source-owner, "
                "compatibility-shell, or taxonomy cleanup"
            ),
            "source-tree relayout and package-authority work that remains Phase 6-owned",
        ],
    )
    for marker in missing_phase7_markers:
        errors.append(f"file-priority-map.md Phase 7 section is missing required marker: {marker}")
