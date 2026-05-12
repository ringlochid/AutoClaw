from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..paths import DOCS_ROOT, ROOT
from ..record_rules import (
    CURRENT_PHASE_PAGE_PATTERN,
    DELEGATED_SLICES_PATTERN,
    PHASE_PAGE_BY_NAME,
    PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS,
    PHASE_SCOPED_PLAN_EXCLUDED_PATHS,
    PHASE_SCOPED_REVIEW_EXCLUDED_PATHS,
    SELECTED_PHASE_PATTERN,
    SELECTED_WORK_PACKAGES_PATTERN,
    SELECTED_WORK_PACKAGES_VALUE_PATTERN,
    SUMMARY_ONLY_PATTERN,
    WORK_PACKAGE_ID_PATTERN,
)
from ..sections import section_body


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


def extract_single_marked_value(
    *,
    text: str,
    pattern: re.Pattern[str],
    label: str,
    artifact_path: Path,
    errors: list[str],
) -> str | None:
    matches = [str(match.group("value")).strip() for match in pattern.finditer(text)]
    unique_matches = list(dict.fromkeys(matches))
    if not unique_matches:
        errors.append(f"{artifact_path.relative_to(ROOT)} is missing {label}")
        return None
    if len(unique_matches) != 1:
        joined = ", ".join(unique_matches)
        errors.append(f"{artifact_path.relative_to(ROOT)} must name exactly one {label}: {joined}")
        return None
    return unique_matches[0]


def resolve_record_link(artifact_path: Path, relative_ref: str) -> Path:
    return (artifact_path.parent / relative_ref).resolve()


def extract_selected_phase(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> str | None:
    return extract_single_marked_value(
        text=artifact_text,
        pattern=SELECTED_PHASE_PATTERN,
        label="top-level `selected phase:` label",
        artifact_path=artifact_path,
        errors=errors,
    )


def extract_selected_work_packages(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> list[str] | None:
    selected_work_packages = extract_single_marked_value(
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


def extract_current_phase_page(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> Path | None:
    current_phase_page = extract_single_marked_value(
        text=artifact_text,
        pattern=CURRENT_PHASE_PAGE_PATTERN,
        label="top-level `current phase page:` label",
        artifact_path=artifact_path,
        errors=errors,
    )
    if current_phase_page is None:
        return None
    return (ROOT / current_phase_page).resolve()


def extract_summary_only(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> str | None:
    return extract_single_marked_value(
        text=artifact_text,
        pattern=SUMMARY_ONLY_PATTERN,
        label="top-level `summary-only:` label",
        artifact_path=artifact_path,
        errors=errors,
    )


def extract_delegated_slices(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> str | None:
    return extract_single_marked_value(
        text=artifact_text,
        pattern=DELEGATED_SLICES_PATTERN,
        label="top-level `delegated slices:` label",
        artifact_path=artifact_path,
        errors=errors,
    )


def phase_scoped_plan_paths() -> list[Path]:
    return phase_scoped_paths(
        DOCS_ROOT / "execution" / "plans",
        PHASE_SCOPED_PLAN_EXCLUDED_PATHS,
    )


def phase_scoped_evidence_paths() -> list[Path]:
    return phase_scoped_paths(
        DOCS_ROOT / "execution" / "evidence",
        PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS,
    )


def phase_scoped_review_paths() -> list[Path]:
    return phase_scoped_paths(
        DOCS_ROOT / "execution" / "reviews",
        PHASE_SCOPED_REVIEW_EXCLUDED_PATHS,
    )


def phase_scoped_paths(record_root: Path, excluded_paths: set[Path]) -> list[Path]:
    return [
        path
        for path in sorted(record_root.glob("*.md"))
        if path not in excluded_paths
    ]


def validate_phase_context(
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> tuple[str, Path] | None:
    selected_phase = extract_selected_phase(artifact_path, artifact_text, errors)
    current_phase_page = extract_current_phase_page(artifact_path, artifact_text, errors)
    if selected_phase is None or current_phase_page is None:
        return None

    expected_phase_page = PHASE_PAGE_BY_NAME.get(selected_phase)
    if expected_phase_page is None:
        errors.append(
            f"{artifact_path.relative_to(ROOT)} resolves an unknown selected phase: "
            f"{selected_phase}"
        )
        return None
    if current_phase_page != expected_phase_page.resolve():
        errors.append(
            f"{artifact_path.relative_to(ROOT)} resolves the wrong current phase page for "
            f"{selected_phase}: {current_phase_page.relative_to(ROOT)}"
        )
        return None
    return selected_phase, current_phase_page


def phase_page_work_package_ids(phase_page_path: Path) -> set[str]:
    ordered_work_packages = section_body(
        phase_page_path.read_text(encoding="utf-8"),
        "## Ordered work packages",
    )
    return set(WORK_PACKAGE_ID_PATTERN.findall(ordered_work_packages))
