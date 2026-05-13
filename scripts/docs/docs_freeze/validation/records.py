from __future__ import annotations

import re

from ..execution_records import (
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
from ..paths import ROOT
from ..phase_records import (
    PhaseScopedEvidenceRecord,
    PhaseScopedPlanRecord,
    PhaseScopedReviewBundle,
    extract_summary_only,
    phase_scoped_evidence_records,
    phase_scoped_plan_records,
    phase_scoped_review_bundles,
)
from ..record_rules import TOUCHED_SURFACES_PATTERN
from ..sections import execution_record_paths
from .phase_requirements import (
    validate_phase_bundle_proof_requirements,
    validate_plan_delegated_slice_briefs,
)

PASS_FAIL_LINE_PATTERN = re.compile(r"^- pass/fail: (?P<value>pass|fail)$", re.MULTILINE)
DOCS_ONLY_CLAIM = "this slice changed only current docs and execution records"


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
    plan_records_by_path = {record.plan_path.resolve(): record for record in plan_records}
    evidence_records_by_path = {
        record.evidence_path.resolve(): record for record in evidence_records
    }

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
        matched_plan_record = plan_records_by_path.get(review_bundle.reviewed_plan_path.resolve())
        matched_evidence_record = evidence_records_by_path.get(
            review_bundle.reviewed_evidence_path.resolve()
        )
        if matched_plan_record is None or matched_evidence_record is None:
            continue
        validate_phase_bundle_proof_requirements(
            plan_record=matched_plan_record,
            evidence_text=matched_evidence_record.evidence_text,
            review_bundle=review_bundle,
            errors=errors,
        )


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
    validate_plan_delegated_slice_briefs(plan_record=plan_record, errors=errors)


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
    validate_review_verdict_consistency(review_bundle=review_bundle, errors=errors)
    validate_docs_only_claim_consistency(review_bundle=review_bundle, errors=errors)


def validate_review_verdict_consistency(
    *,
    review_bundle: PhaseScopedReviewBundle,
    errors: list[str],
) -> None:
    match = PASS_FAIL_LINE_PATTERN.search(review_bundle.review_text)
    if match is None:
        return
    remaining_section = execution_record_section(
        review_bundle.review_text,
        "## Remaining exact blockers",
    )
    if remaining_section is None:
        return
    remaining_lines = [line.strip() for line in remaining_section.splitlines() if line.strip()]
    has_none = any(line == "- none" for line in remaining_lines)
    has_explicit_blocker = any(
        line.startswith("- ") and line != "- none" for line in remaining_lines
    )
    verdict = match.group("value")
    if verdict == "pass" and has_explicit_blocker:
        errors.append(
            f"{review_bundle.review_path.relative_to(ROOT)} declares `pass/fail: pass` "
            "but still lists explicit remaining blockers"
        )
    if verdict == "fail" and has_none and not has_explicit_blocker:
        errors.append(
            f"{review_bundle.review_path.relative_to(ROOT)} declares `pass/fail: fail` "
            "but `## Remaining exact blockers` says `- none`"
        )


def validate_docs_only_claim_consistency(
    *,
    review_bundle: PhaseScopedReviewBundle,
    errors: list[str],
) -> None:
    if DOCS_ONLY_CLAIM not in review_bundle.review_text:
        return
    touched_surface_values = TOUCHED_SURFACES_PATTERN.findall(review_bundle.review_text)
    touched_paths: list[str] = []
    for value in touched_surface_values:
        touched_paths.extend(part.strip() for part in value.split(",") if part.strip())
    non_doc_paths = [
        path
        for path in touched_paths
        if not (path.startswith("docs/current/") or path.startswith("docs/execution/"))
    ]
    if non_doc_paths:
        errors.append(
            f"{review_bundle.review_path.relative_to(ROOT)} claims the slice changed only "
            "current docs and execution records, but its delegated-slice header lists "
            f"non-doc touched surfaces such as `{non_doc_paths[0]}`"
        )


def execution_record_section(text: str, heading: str) -> str | None:
    marker = f"{heading}\n"
    start = text.find(marker)
    if start < 0:
        return None
    start += len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading < 0:
        return text[start:].strip()
    return text[start:next_heading].strip()
