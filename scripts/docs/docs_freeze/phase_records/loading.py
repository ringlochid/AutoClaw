from __future__ import annotations

from pathlib import Path

from ..paths import ROOT
from ..record_rules import (
    APPROVED_PLAN_PATTERN,
    PHASE_SCOPED_REVIEW_REQUIRED_HEADINGS,
    REVIEW_ARTIFACT_PATTERN,
    REVIEWED_EVIDENCE_PATTERN,
    REVIEWED_PLAN_PATTERN,
)
from .parsing import (
    PhaseScopedEvidenceRecord,
    PhaseScopedPlanRecord,
    PhaseScopedReviewBundle,
    extract_selected_phase,
    extract_single_marked_value,
    extract_summary_only,
    phase_scoped_evidence_paths,
    phase_scoped_plan_paths,
    phase_scoped_review_paths,
    resolve_record_link,
    validate_phase_context,
)


def phase_scoped_plan_records(errors: list[str]) -> list[PhaseScopedPlanRecord]:
    records: list[PhaseScopedPlanRecord] = []
    for plan_path in phase_scoped_plan_paths():
        plan_text = plan_path.read_text(encoding="utf-8")
        if extract_summary_only(plan_path, plan_text, errors) == "yes":
            continue

        phase_context = validate_phase_context(plan_path, plan_text, errors)
        if phase_context is None:
            continue
        selected_phase, current_phase_page = phase_context
        records.append(
            PhaseScopedPlanRecord(
                plan_path=plan_path,
                plan_text=plan_text,
                selected_phase=selected_phase,
                current_phase_page=current_phase_page,
            )
        )
    return records


def phase_scoped_evidence_records(
    *,
    errors: list[str],
    plan_records: list[PhaseScopedPlanRecord],
) -> list[PhaseScopedEvidenceRecord]:
    plan_records_by_path = {record.plan_path.resolve(): record for record in plan_records}
    records: list[PhaseScopedEvidenceRecord] = []
    for evidence_path in phase_scoped_evidence_paths():
        evidence_text = evidence_path.read_text(encoding="utf-8")
        if extract_summary_only(evidence_path, evidence_text, errors) == "yes":
            continue

        selected_phase = extract_selected_phase(evidence_path, evidence_text, errors)
        approved_plan_ref = extract_single_marked_value(
            text=evidence_text,
            pattern=APPROVED_PLAN_PATTERN,
            label="approved plan link",
            artifact_path=evidence_path,
            errors=errors,
        )
        if selected_phase is None or approved_plan_ref is None:
            continue

        approved_plan_path = resolve_record_link(evidence_path, approved_plan_ref)
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


def phase_scoped_review_bundles(errors: list[str]) -> list[PhaseScopedReviewBundle]:
    bundles: list[PhaseScopedReviewBundle] = []
    for review_path in phase_scoped_review_paths():
        review_text = review_path.read_text(encoding="utf-8")
        if extract_summary_only(review_path, review_text, errors) == "yes":
            continue

        validate_required_review_headings(review_path, review_text, errors)
        reviewed_paths = reviewed_artifact_paths(review_path, review_text, errors)
        if reviewed_paths is None:
            continue
        reviewed_plan_path, reviewed_evidence_path = reviewed_paths

        bundle_context = validate_review_bundle_context(
            review_path=review_path,
            review_text=review_text,
            reviewed_plan_path=reviewed_plan_path,
            reviewed_evidence_path=reviewed_evidence_path,
            errors=errors,
        )
        if bundle_context is None:
            continue
        selected_phase, current_phase_page = bundle_context
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


def validate_required_review_headings(
    review_path: Path,
    review_text: str,
    errors: list[str],
) -> None:
    for heading in PHASE_SCOPED_REVIEW_REQUIRED_HEADINGS:
        if heading not in review_text:
            errors.append(
                f"{review_path.relative_to(ROOT)} is missing required review heading: {heading}"
            )


def reviewed_artifact_paths(
    review_path: Path,
    review_text: str,
    errors: list[str],
) -> tuple[Path, Path] | None:
    reviewed_plan_ref = extract_single_marked_value(
        text=review_text,
        pattern=REVIEWED_PLAN_PATTERN,
        label="reviewed plan link",
        artifact_path=review_path,
        errors=errors,
    )
    reviewed_evidence_ref = extract_single_marked_value(
        text=review_text,
        pattern=REVIEWED_EVIDENCE_PATTERN,
        label="reviewed evidence link",
        artifact_path=review_path,
        errors=errors,
    )
    if reviewed_plan_ref is None or reviewed_evidence_ref is None:
        return None

    reviewed_plan_path = resolve_record_link(review_path, reviewed_plan_ref)
    reviewed_evidence_path = resolve_record_link(review_path, reviewed_evidence_ref)
    if not reviewed_plan_path.exists():
        errors.append(
            f"{review_path.relative_to(ROOT)} points to missing reviewed plan: "
            f"{reviewed_plan_ref}"
        )
        return None
    if not reviewed_evidence_path.exists():
        errors.append(
            f"{review_path.relative_to(ROOT)} points to missing reviewed evidence: "
            f"{reviewed_evidence_ref}"
        )
        return None
    return reviewed_plan_path, reviewed_evidence_path


def validate_review_bundle_context(
    *,
    review_path: Path,
    review_text: str,
    reviewed_plan_path: Path,
    reviewed_evidence_path: Path,
    errors: list[str],
) -> tuple[str, Path] | None:
    review_context = validate_phase_context(review_path, review_text, errors)
    if review_context is None:
        return None
    review_selected_phase, review_current_phase_page = review_context

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
    plan_context = validate_phase_context(reviewed_plan_path, plan_text, errors)
    evidence_phase = extract_selected_phase(reviewed_evidence_path, evidence_text, errors)
    if plan_context is None or evidence_phase is None:
        return None

    selected_phase, current_phase_page = plan_context
    if selected_phase != evidence_phase:
        errors.append(
            f"{review_path.relative_to(ROOT)} resolves conflicting selected phases: "
            f"{selected_phase} vs {evidence_phase}"
        )
        return None
    if review_selected_phase != selected_phase:
        errors.append(
            f"{review_path.relative_to(ROOT)} must record the same selected phase as "
            f"its plan/evidence bundle: {review_selected_phase} vs {selected_phase}"
        )
        return None
    if review_current_phase_page != current_phase_page:
        errors.append(
            f"{review_path.relative_to(ROOT)} must record the same current phase page as "
            f"its reviewed plan: {review_current_phase_page.relative_to(ROOT)} vs "
            f"{current_phase_page.relative_to(ROOT)}"
        )
        return None
    if not current_phase_page.exists():
        errors.append(
            f"{review_path.relative_to(ROOT)} points to missing current phase page: "
            f"{current_phase_page.relative_to(ROOT)}"
        )
        return None

    evidence_review_ref = extract_single_marked_value(
        text=evidence_text,
        pattern=REVIEW_ARTIFACT_PATTERN,
        label="review artifact link",
        artifact_path=reviewed_evidence_path,
        errors=errors,
    )
    if evidence_review_ref is not None:
        linked_review_path = resolve_record_link(reviewed_evidence_path, evidence_review_ref)
        if linked_review_path != review_path.resolve():
            errors.append(
                f"{reviewed_evidence_path.relative_to(ROOT)} must link back to "
                f"{review_path.relative_to(ROOT)}"
            )
    return selected_phase, current_phase_page
