from __future__ import annotations

from pathlib import Path

from ..paths import ROOT
from ..phase_records import (
    DelegatedSliceHeader,
    PhaseScopedPlanRecord,
    PhaseScopedReviewBundle,
    execution_record_body,
    parse_delegated_slice_headers,
    split_surface_values,
)

DELEGATED_SLICE_BRIEF_REQUIREMENTS = {
    "do-not-edit surfaces": ("do-not-edit", "do not edit"),
    "required reads": ("required reads",),
    "required tests/validators": (
        "required tests",
        "required validators",
        "required validation",
    ),
    "expected outputs": ("expected outputs", "expected output"),
    "dependencies": ("dependencies",),
    "evidence to return": ("evidence to return",),
    "parent-owned decisions": ("parent-owned decisions", "parent-owned"),
    "stop conditions": ("stop conditions",),
}
STYLE_AUDIT_TOKENS = (
    "style_audit.cli --fail-on-findings",
    "style_audit",
)
PRIVATE_SYMBOL_TOKENS = (
    "exact repo search",
    "private symbol",
    "private-symbol",
    "underscore-private",
)
PROMPT_GENERATE_TOKENS = (
    "prompt_catalog.cli generate",
    "prompt_catalog generate",
)
SCRIPTS_DOCS_RUFF_TOKENS = ("ruff check scripts/docs",)
SCRIPTS_DOCS_MYPY_TOKENS = ("mypy scripts/docs",)
STRONG_DB_LANE_TOKENS = ("make test-api-db",)
SQLITE_TOKENS = ("sqlite",)
RESET_TOKENS = ("reset",)
PROMPT_GENERATION_PREFIXES = (
    "apps/api/app/runtime/prompt/assets/",
    "docs-internal/design/v1/prompt-layer/generated/",
    "docs-internal/design/v1/prompt-layer/prompt-catalog.yaml",
    "scripts/docs/prompt_catalog/",
)
SCRIPTS_DOCS_PREFIX = "scripts/docs/"
PHASES_REQUIRING_STRONG_DB_PROOF = {"Phase 1", "Phase 3"}


def validate_plan_delegated_slice_briefs(
    *,
    plan_record: PhaseScopedPlanRecord,
    errors: list[str],
) -> None:
    slice_headers = parse_delegated_slice_headers(
        plan_record.plan_path,
        plan_record.plan_text,
        errors,
    )
    if not slice_headers:
        return

    body_text = execution_record_body(plan_record.plan_text)
    body_lower = body_text.lower()
    slice_positions = {
        slice_header.slice_id: body_lower.find(slice_header.slice_id.lower())
        for slice_header in slice_headers
    }

    for slice_header in slice_headers:
        slice_position = slice_positions[slice_header.slice_id]
        if slice_position < 0:
            errors.append(
                f"{plan_record.plan_path.relative_to(ROOT)} must include a body brief for "
                f"delegated slice `{slice_header.slice_id}`"
            )
            continue

        slice_block = slice_brief_block(
            body_text=body_text,
            slice_header=slice_header,
            slice_positions=slice_positions,
        )
        missing_requirements = [
            label
            for label, markers in DELEGATED_SLICE_BRIEF_REQUIREMENTS.items()
            if not any(marker in slice_block.lower() for marker in markers)
        ]
        if missing_requirements:
            missing_rendered = ", ".join(missing_requirements)
            errors.append(
                f"{plan_record.plan_path.relative_to(ROOT)} delegated slice "
                f"`{slice_header.slice_id}` is missing required brief content: "
                f"{missing_rendered}"
            )


def validate_phase_bundle_proof_requirements(
    *,
    plan_record: PhaseScopedPlanRecord,
    evidence_text: str,
    review_bundle: PhaseScopedReviewBundle,
    errors: list[str],
) -> None:
    combined_text = "\n".join((evidence_text, review_bundle.review_text)).lower()
    review_text = review_bundle.review_text.lower()
    touched_surfaces = delegated_slice_touched_surfaces(plan_record)

    if plan_record.selected_phase in {"Phase 1", "Phase 2", "Phase 3"}:
        require_any_token(
            artifact_path=review_bundle.review_path,
            combined_text=combined_text,
            required_tokens=STYLE_AUDIT_TOKENS,
            label="style_audit proof",
            errors=errors,
        )
        require_any_token(
            artifact_path=review_bundle.review_path,
            combined_text=review_text,
            required_tokens=PRIVATE_SYMBOL_TOKENS,
            label="private-symbol search proof language",
            errors=errors,
        )

    if plan_record.selected_phase == "Phase 2":
        if requires_prompt_catalog_generate(touched_surfaces):
            require_any_token(
                artifact_path=review_bundle.review_path,
                combined_text=combined_text,
                required_tokens=PROMPT_GENERATE_TOKENS,
                label="prompt_catalog generate proof",
                errors=errors,
            )
        if touches_scripts_docs(touched_surfaces):
            require_any_token(
                artifact_path=review_bundle.review_path,
                combined_text=combined_text,
                required_tokens=SCRIPTS_DOCS_RUFF_TOKENS,
                label="`ruff check scripts/docs` proof",
                errors=errors,
            )
            require_any_token(
                artifact_path=review_bundle.review_path,
                combined_text=combined_text,
                required_tokens=SCRIPTS_DOCS_MYPY_TOKENS,
                label="`mypy scripts/docs` proof",
                errors=errors,
            )

    if plan_record.selected_phase in PHASES_REQUIRING_STRONG_DB_PROOF:
        require_any_token(
            artifact_path=review_bundle.review_path,
            combined_text=combined_text,
            required_tokens=STRONG_DB_LANE_TOKENS,
            label="Postgres strong-lane proof",
            errors=errors,
        )
        require_any_token(
            artifact_path=review_bundle.review_path,
            combined_text=combined_text,
            required_tokens=SQLITE_TOKENS,
            label="SQLite proof",
            errors=errors,
        )
        require_any_token(
            artifact_path=review_bundle.review_path,
            combined_text=combined_text,
            required_tokens=RESET_TOKENS,
            label="reset proof",
            errors=errors,
        )


def slice_brief_block(
    *,
    body_text: str,
    slice_header: DelegatedSliceHeader,
    slice_positions: dict[str, int],
) -> str:
    start = slice_positions[slice_header.slice_id]
    next_slice_starts = [
        position
        for slice_id, position in slice_positions.items()
        if slice_id != slice_header.slice_id and position > start
    ]
    next_heading = body_text.find("\n## ", start + 1)
    end_candidates = [position for position in next_slice_starts if position > start]
    if next_heading > start:
        end_candidates.append(next_heading)
    end = min(end_candidates) if end_candidates else len(body_text)
    return body_text[start:end]


def delegated_slice_touched_surfaces(plan_record: PhaseScopedPlanRecord) -> set[str]:
    touched_surfaces: set[str] = set()
    for slice_header in parse_delegated_slice_headers(
        plan_record.plan_path,
        plan_record.plan_text,
        errors=[],
    ):
        touched_surfaces.update(split_surface_values(slice_header.touched_surfaces))
    return touched_surfaces


def requires_prompt_catalog_generate(touched_surfaces: set[str]) -> bool:
    return any(
        surface.startswith(prefix)
        for surface in touched_surfaces
        for prefix in PROMPT_GENERATION_PREFIXES
    )


def touches_scripts_docs(touched_surfaces: set[str]) -> bool:
    return any(surface.startswith(SCRIPTS_DOCS_PREFIX) for surface in touched_surfaces)


def require_any_token(
    *,
    artifact_path: Path,
    combined_text: str,
    required_tokens: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    if any(token in combined_text for token in required_tokens):
        return
    errors.append(
        f"{artifact_path.relative_to(ROOT)} is missing required {label}; "
        f"expected one of: {', '.join(required_tokens)}"
    )
