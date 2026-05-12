from __future__ import annotations

import re
from pathlib import Path

from .paths import ROOT
from .phase_records import (
    PhaseScopedReviewBundle,
    extract_single_marked_value,
    extract_summary_only,
    resolve_record_link,
)
from .phase_rules import (
    ARTIFACTS_CHANGED_REQUIRED_EVIDENCE_PATHS,
    PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS,
    SUMMARY_ONLY_REPLACEMENT_REQUIRED_PATHS,
)
from .record_rules import (
    AUTHORITATIVE_EXCEPTION_HOME_PATTERN,
    BACKTICKED_VALUE_PATTERN,
    LATEST_OWNING_PHASE_REVIEW_PATTERN,
    SUMMARY_EXCEPTION_ENTRY_PATTERN,
    SUMMARY_EXCEPTION_SURFACE_PATTERN,
)
from .sections import section_body


def validate_required_artifacts_changed_heading(errors: list[str]) -> None:
    for evidence_path in ARTIFACTS_CHANGED_REQUIRED_EVIDENCE_PATHS:
        if not evidence_path.exists():
            continue
        evidence_text = evidence_path.read_text(encoding="utf-8")
        if "## Artifacts changed" not in evidence_text:
            errors.append(
                f"{evidence_path.relative_to(ROOT)} must use `## Artifacts changed` "
                "for its artifact inventory section"
            )


def validate_summary_only_artifact_headers(errors: list[str]) -> None:
    for artifact_path in sorted(PHASE0_CLOSEOUT_SUMMARY_REQUIRED_MARKERS):
        if not artifact_path.exists():
            continue
        artifact_text = artifact_path.read_text(encoding="utf-8")
        summary_only = extract_summary_only(artifact_path, artifact_text, errors)
        if summary_only is None:
            continue
        if summary_only != "yes":
            errors.append(
                f"{artifact_path.relative_to(ROOT)} must use `summary-only: yes` "
                "to stay valid as a historical or aggregate summary artifact"
            )


def validate_summary_only_replacement_links(errors: list[str]) -> None:
    for artifact_path in sorted(SUMMARY_ONLY_REPLACEMENT_REQUIRED_PATHS):
        if not artifact_path.exists():
            continue
        artifact_text = artifact_path.read_text(encoding="utf-8")
        if extract_summary_only(artifact_path, artifact_text, errors) != "yes":
            continue

        replacements_section = section_body(artifact_text, "## Authoritative replacements")
        if not replacements_section:
            errors.append(
                f"{artifact_path.relative_to(ROOT)} must include `## Authoritative replacements` "
                "with truthful replacement links"
            )
            continue

        replacement_paths = replacement_paths_from_section(artifact_path, replacements_section)
        if not replacement_paths:
            errors.append(
                f"{artifact_path.relative_to(ROOT)} must list at least one replacement "
                "artifact path under `## Authoritative replacements`"
            )
            continue

        for replacement_path in replacement_paths:
            validate_summary_only_replacement_path(
                artifact_path=artifact_path,
                replacement_path=replacement_path,
                errors=errors,
            )


def validate_summary_only_review_exceptions(
    *,
    errors: list[str],
    review_bundles: list[PhaseScopedReviewBundle],
) -> None:
    summary_only_exceptions_path = (
        ROOT / "docs" / "execution" / "reviews" / "phase-0-3-closeout-review-exceptions.md"
    )
    if not summary_only_exceptions_path.exists():
        return

    review_bundles_by_path = {bundle.review_path.resolve(): bundle for bundle in review_bundles}
    summary_text = summary_only_exceptions_path.read_text(encoding="utf-8")
    for match in SUMMARY_EXCEPTION_ENTRY_PATTERN.finditer(summary_text):
        validate_summary_only_review_exception_entry(
            summary_only_exceptions_path=summary_only_exceptions_path,
            review_bundles_by_path=review_bundles_by_path,
            match=match,
            errors=errors,
        )


def replacement_paths_from_section(artifact_path: Path, replacements_section: str) -> list[Path]:
    replacement_paths: list[Path] = []
    for raw_ref in BACKTICKED_VALUE_PATTERN.findall(replacements_section):
        resolved_path = (artifact_path.parent / raw_ref).resolve()
        try:
            resolved_path.relative_to(ROOT)
        except ValueError:
            continue
        replacement_paths.append(resolved_path)
    return sorted(dict.fromkeys(replacement_paths))


def validate_summary_only_replacement_path(
    *,
    artifact_path: Path,
    replacement_path: Path,
    errors: list[str],
) -> None:
    if not replacement_path.exists():
        errors.append(
            f"{artifact_path.relative_to(ROOT)} points to missing authoritative "
            f"replacement: {replacement_path.relative_to(ROOT)}"
        )
        return

    replacement_text = replacement_path.read_text(encoding="utf-8")
    replacement_summary_only = extract_summary_only(
        replacement_path,
        replacement_text,
        errors,
    )
    if replacement_summary_only is not None and replacement_summary_only != "no":
        errors.append(
            f"{artifact_path.relative_to(ROOT)} must point only to authoritative "
            f"`summary-only: no` replacements, not "
            f"{replacement_path.relative_to(ROOT)}"
        )


def validate_summary_only_review_exception_entry(
    *,
    summary_only_exceptions_path: Path,
    review_bundles_by_path: dict[Path, PhaseScopedReviewBundle],
    match: re.Match[str],
    errors: list[str],
) -> None:
    entry_text = match.group("body")
    exception_path = extract_single_marked_value(
        text=entry_text,
        pattern=SUMMARY_EXCEPTION_SURFACE_PATTERN,
        label=f"summary-only exception surface in `{match.group('title')}`",
        artifact_path=summary_only_exceptions_path,
        errors=errors,
    )
    latest_review_ref = extract_single_marked_value(
        text=entry_text,
        pattern=LATEST_OWNING_PHASE_REVIEW_PATTERN,
        label=f"latest owning phase review link in `{match.group('title')}`",
        artifact_path=summary_only_exceptions_path,
        errors=errors,
    )
    authoritative_home_ref = extract_single_marked_value(
        text=entry_text,
        pattern=AUTHORITATIVE_EXCEPTION_HOME_PATTERN,
        label=f"authoritative exception home link in `{match.group('title')}`",
        artifact_path=summary_only_exceptions_path,
        errors=errors,
    )
    if exception_path is None or latest_review_ref is None or authoritative_home_ref is None:
        return

    latest_review_path = resolve_record_link(summary_only_exceptions_path, latest_review_ref)
    authoritative_home_path = resolve_record_link(
        summary_only_exceptions_path,
        authoritative_home_ref,
    )
    if latest_review_path != authoritative_home_path:
        errors.append(
            f"{summary_only_exceptions_path.relative_to(ROOT)} must point "
            f"`{match.group('title')}` at the same authoritative later-phase review for "
            "`latest owning phase review` and `authoritative exception home`"
        )
        return

    review_bundle = review_bundles_by_path.get(latest_review_path)
    if review_bundle is None:
        errors.append(
            f"{summary_only_exceptions_path.relative_to(ROOT)} points later-phase "
            f"STYLE exception `{exception_path}` at non-phase-scoped review "
            f"{latest_review_path.relative_to(ROOT)}"
        )
        return
    if review_bundle.selected_phase == "Phase 0":
        return

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
