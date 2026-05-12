from __future__ import annotations

from pathlib import Path

from .paths import ROOT
from .phase_records import (
    PhaseScopedEvidenceRecord,
    PhaseScopedPlanRecord,
    extract_selected_work_packages,
    extract_single_marked_value,
    phase_page_work_package_ids,
    resolve_record_link,
)
from .phase_rules import PHASE0_CURRENT_DOC_REQUIRED_MARKERS
from .record_rules import (
    BACKTICKED_VALUE_PATTERN,
    CURRENT_DOC_PATH_PATTERN,
    REPO_PATH_PATTERN,
    REVIEW_ARTIFACT_PATTERN,
    WORK_PACKAGE_ID_PATTERN,
    phase0_allowed_current_doc_paths,
)
from .sections import section_body

PHASE0_ALLOWED_CURRENT_DOC_PATHS = phase0_allowed_current_doc_paths(
    PHASE0_CURRENT_DOC_REQUIRED_MARKERS
)


def validate_artifact_work_package_ids(
    *,
    artifact_path: Path,
    artifact_text: str,
    current_phase_page: Path,
    errors: list[str],
) -> None:
    phase_work_package_ids = phase_page_work_package_ids(current_phase_page)
    if not phase_work_package_ids:
        errors.append(
            f"{current_phase_page.relative_to(ROOT)} is missing parseable work-package ids "
            "under `## Ordered work packages`"
        )
        return

    selected_work_packages = extract_selected_work_packages(artifact_path, artifact_text, errors)
    if selected_work_packages is not None:
        for work_package_id in selected_work_packages:
            if work_package_id not in phase_work_package_ids:
                errors.append(
                    f"{artifact_path.relative_to(ROOT)} names unknown work-package id "
                    f"`{work_package_id}` for {current_phase_page.relative_to(ROOT)}"
                )

    ordered_work_packages = section_body(artifact_text, "## Ordered work packages")
    for work_package_id in WORK_PACKAGE_ID_PATTERN.findall(ordered_work_packages):
        if work_package_id not in phase_work_package_ids:
            errors.append(
                f"{artifact_path.relative_to(ROOT)} defines unknown work-package id "
                f"`{work_package_id}` for {current_phase_page.relative_to(ROOT)}"
            )


def validate_phase0_current_doc_unlocks(
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


def validate_evidence_artifact_paths(
    *,
    evidence_record: PhaseScopedEvidenceRecord,
    errors: list[str],
) -> None:
    artifact_section = section_body(evidence_record.evidence_text, "## Artifacts changed")
    if not artifact_section:
        return

    artifact_paths = extract_backticked_repo_paths(artifact_section)
    if not artifact_paths:
        return

    allowed_specs = allowed_surface_specs_from_plan(evidence_record.approved_plan_record)
    allowed_specs.add(evidence_record.evidence_path.relative_to(ROOT).as_posix())
    review_artifact_ref = extract_single_marked_value(
        text=evidence_record.evidence_text,
        pattern=REVIEW_ARTIFACT_PATTERN,
        label="review artifact link",
        artifact_path=evidence_record.evidence_path,
        errors=errors,
    )
    if review_artifact_ref is not None:
        allowed_specs.add(
            resolve_record_link(evidence_record.evidence_path, review_artifact_ref)
            .relative_to(ROOT)
            .as_posix()
        )

    for artifact_path in sorted(artifact_paths):
        if not any(path_matches_surface(artifact_path, surface) for surface in allowed_specs):
            errors.append(
                f"{evidence_record.evidence_path.relative_to(ROOT)} lists artifact path outside "
                f"parseable owned/allowed surfaces: {artifact_path}"
            )


def validate_required_markers(
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


def validate_forbidden_markers(
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


def extract_backticked_repo_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for backticked_value in BACKTICKED_VALUE_PATTERN.findall(text):
        for path in REPO_PATH_PATTERN.findall(backticked_value):
            paths.add(path.rstrip(".,"))
    return paths


def allowed_surface_specs_from_plan(plan_record: PhaseScopedPlanRecord) -> set[str]:
    allowed_specs = extract_backticked_repo_paths(plan_record.plan_text)
    allowed_specs.add(plan_record.plan_path.relative_to(ROOT).as_posix())
    return allowed_specs


def path_matches_surface(path: str, surface: str) -> bool:
    normalized_path = path.rstrip("/")
    normalized_surface = surface.rstrip("/")
    if "*" in normalized_surface:
        return Path(normalized_path).match(normalized_surface)
    if normalized_path == normalized_surface:
        return True
    if "." not in Path(normalized_surface).name:
        return normalized_path.startswith(f"{normalized_surface}/")
    return False
