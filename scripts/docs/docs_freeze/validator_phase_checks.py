from __future__ import annotations

from .execution_records import (
    validate_artifact_work_package_ids,
    validate_cross_phase_summary_sentinel,
    validate_delegated_slice_grammar,
    validate_evidence_artifact_paths,
    validate_exact_top_of_file_block,
    validate_phase0_current_doc_unlocks,
    validate_required_artifacts_changed_heading,
    validate_summary_only_artifact_headers,
    validate_summary_only_replacement_links,
    validate_summary_only_review_exceptions,
)
from .paths import ROOT
from .phase_records import (
    PhaseScopedEvidenceRecord,
    PhaseScopedPlanRecord,
    PhaseScopedReviewBundle,
    extract_summary_only,
    phase_scoped_evidence_records,
    phase_scoped_plan_records,
    phase_scoped_review_bundles,
)
from .sections import execution_record_paths


def validate_execution_record_headers(errors: list[str]) -> None:
    for artifact_path in execution_record_paths():
        artifact_text = artifact_path.read_text(encoding="utf-8")
        validate_exact_top_of_file_block(
            artifact_path=artifact_path,
            artifact_text=artifact_text,
            errors=errors,
        )
        validate_cross_phase_summary_sentinel(
            artifact_path=artifact_path,
            artifact_text=artifact_text,
            errors=errors,
        )


def validate_phase_scoped_records(errors: list[str]) -> None:
    review_bundles = phase_scoped_review_bundles(errors)
    plan_records = phase_scoped_plan_records(errors)
    evidence_records = phase_scoped_evidence_records(errors=errors, plan_records=plan_records)

    validate_summary_only_artifact_headers(errors)
    validate_summary_only_replacement_links(errors)
    validate_required_artifacts_changed_heading(errors)
    validate_summary_only_review_exceptions(errors=errors, review_bundles=review_bundles)

    for plan_record in plan_records:
        validate_phase_scoped_plan_record(plan_record, errors)
    for evidence_record in evidence_records:
        validate_phase_scoped_evidence_record(evidence_record, errors)
    for review_bundle in review_bundles:
        validate_phase_scoped_review_bundle(review_bundle, errors)


def validate_phase_scoped_plan_record(
    plan_record: PhaseScopedPlanRecord,
    errors: list[str],
) -> None:
    if extract_summary_only(plan_record.plan_path, plan_record.plan_text, errors) != "no":
        errors.append(
            f"{plan_record.plan_path.relative_to(ROOT)} must use `summary-only: no` "
            "for authoritative phase-scoped closure artifacts"
        )
    validate_delegated_slice_grammar(
        artifact_path=plan_record.plan_path,
        artifact_text=plan_record.plan_text,
        errors=errors,
    )
    validate_artifact_work_package_ids(
        artifact_path=plan_record.plan_path,
        artifact_text=plan_record.plan_text,
        current_phase_page=plan_record.current_phase_page,
        errors=errors,
    )
    validate_phase0_current_doc_unlocks(
        artifact_path=plan_record.plan_path,
        artifact_text=plan_record.plan_text,
        selected_phase=plan_record.selected_phase,
        errors=errors,
    )


def validate_phase_scoped_evidence_record(
    evidence_record: PhaseScopedEvidenceRecord,
    errors: list[str],
) -> None:
    if (
        extract_summary_only(
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
    validate_delegated_slice_grammar(
        artifact_path=evidence_record.evidence_path,
        artifact_text=evidence_record.evidence_text,
        errors=errors,
    )
    validate_artifact_work_package_ids(
        artifact_path=evidence_record.evidence_path,
        artifact_text=evidence_record.evidence_text,
        current_phase_page=evidence_record.approved_plan_record.current_phase_page,
        errors=errors,
    )
    validate_phase0_current_doc_unlocks(
        artifact_path=evidence_record.evidence_path,
        artifact_text=evidence_record.evidence_text,
        selected_phase=evidence_record.selected_phase,
        errors=errors,
    )
    validate_evidence_artifact_paths(evidence_record=evidence_record, errors=errors)


def validate_phase_scoped_review_bundle(
    review_bundle: PhaseScopedReviewBundle,
    errors: list[str],
) -> None:
    if extract_summary_only(review_bundle.review_path, review_bundle.review_text, errors) != "no":
        errors.append(
            f"{review_bundle.review_path.relative_to(ROOT)} must use `summary-only: no` "
            "for authoritative phase-scoped closure artifacts"
        )
    validate_delegated_slice_grammar(
        artifact_path=review_bundle.review_path,
        artifact_text=review_bundle.review_text,
        errors=errors,
    )
    validate_artifact_work_package_ids(
        artifact_path=review_bundle.review_path,
        artifact_text=review_bundle.review_text,
        current_phase_page=review_bundle.current_phase_page,
        errors=errors,
    )
    validate_phase0_current_doc_unlocks(
        artifact_path=review_bundle.review_path,
        artifact_text=review_bundle.review_text,
        selected_phase=review_bundle.selected_phase,
        errors=errors,
    )
