from __future__ import annotations

from pathlib import Path

from .paths import ROOT
from .phase_records import (
    extract_delegated_slices,
    extract_single_marked_value,
    extract_summary_only,
)
from .phase_rules import CROSS_PHASE_SUMMARY_SENTINEL_PATHS
from .record_rules import (
    CURRENT_PHASE_PAGE_PATTERN,
    OWNED_SURFACES_PATTERN,
    SELECTED_PHASE_PATTERN,
    SELECTED_WORK_PACKAGES_PATTERN,
    SLICE_ID_PATTERN,
    SLICE_TYPE_PATTERN,
    TOUCHED_SURFACES_PATTERN,
)


def validate_exact_top_of_file_block(
    *,
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> None:
    lines = artifact_text.splitlines()
    try:
        status_index = next(
            index for index, line in enumerate(lines) if line.startswith("Status: ")
        )
    except StopIteration:
        errors.append(f"{artifact_path.relative_to(ROOT)} is missing a top-level `Status:` line")
        return

    top_block_error = (
        f"{artifact_path.relative_to(ROOT)} must use one exact top-of-file execution-record "
        "block immediately after `Status:` with this order: `selected phase:`, "
        "`current phase page:`, `selected work packages:`, `summary-only:`, "
        "`delegated slices:`"
    )
    if status_index + 1 >= len(lines) or lines[status_index + 1] != "":
        errors.append(
            f"{artifact_path.relative_to(ROOT)} must leave a blank line after `Status:` "
            "before the execution-record block"
        )
        return

    block_index = status_index + 2
    expected_prefixes = [
        "selected phase: ",
        "current phase page: ",
        "selected work packages: ",
        "summary-only: ",
        "delegated slices: ",
    ]
    for prefix in expected_prefixes:
        if block_index >= len(lines) or not lines[block_index].startswith(prefix):
            errors.append(top_block_error)
            return
        if not lines[block_index][len(prefix) :].strip():
            errors.append(
                f"{artifact_path.relative_to(ROOT)} must give a value on the `{prefix[:-2]}` line"
            )
            return
        block_index += 1

    delegated_slices = lines[status_index + 6].removeprefix("delegated slices: ").strip()
    if delegated_slices == "listed":
        next_block_index = validate_listed_delegated_slice_block(
            artifact_path=artifact_path,
            lines=lines,
            start_index=block_index,
            errors=errors,
        )
        if next_block_index is None:
            return
        block_index = next_block_index

    if block_index >= len(lines) or lines[block_index] != "":
        errors.append(
            f"{artifact_path.relative_to(ROOT)} must end the top-of-file execution-record "
            "block with a blank line before the first narrative heading"
        )
        return
    if block_index + 1 >= len(lines) or not lines[block_index + 1].startswith("## "):
        errors.append(
            f"{artifact_path.relative_to(ROOT)} must start narrative content with a `## ` "
            "heading immediately after the top-of-file execution-record block"
        )


def validate_cross_phase_summary_sentinel(
    *,
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> None:
    if artifact_path not in CROSS_PHASE_SUMMARY_SENTINEL_PATHS:
        return
    if extract_summary_only(artifact_path, artifact_text, errors) != "yes":
        return

    sentinel_checks = [
        (SELECTED_PHASE_PATTERN, "selected phase", "none"),
        (CURRENT_PHASE_PAGE_PATTERN, "current phase page", "none"),
        (SELECTED_WORK_PACKAGES_PATTERN, "selected work packages", "none"),
    ]
    for pattern, label, expected_value in sentinel_checks:
        value = extract_single_marked_value(
            text=artifact_text,
            pattern=pattern,
            label=f"top-level `{label}:` label",
            artifact_path=artifact_path,
            errors=errors,
        )
        if value is not None and value != expected_value:
            errors.append(
                f"{artifact_path.relative_to(ROOT)} must use `{label}: {expected_value}` "
                "for the cross-phase or aggregate summary sentinel grammar"
            )


def validate_delegated_slice_grammar(
    *,
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> None:
    delegated_slices = extract_delegated_slices(artifact_path, artifact_text, errors)
    if delegated_slices is None:
        return

    slice_id_count = len(SLICE_ID_PATTERN.findall(artifact_text))
    slice_type_count = len(SLICE_TYPE_PATTERN.findall(artifact_text))
    owned_surfaces_count = len(OWNED_SURFACES_PATTERN.findall(artifact_text))
    touched_surfaces_count = len(TOUCHED_SURFACES_PATTERN.findall(artifact_text))
    if delegated_slices == "none":
        if any((slice_id_count, slice_type_count, owned_surfaces_count, touched_surfaces_count)):
            errors.append(
                f"{artifact_path.relative_to(ROOT)} declares `delegated slices: none` "
                "but still lists delegated-slice label lines"
            )
        return

    counts = {
        "slice id": slice_id_count,
        "slice type": slice_type_count,
        "owned surfaces": owned_surfaces_count,
        "touched surfaces": touched_surfaces_count,
    }
    if not slice_id_count:
        errors.append(
            f"{artifact_path.relative_to(ROOT)} declares `delegated slices: listed` "
            "but has no `slice id:` entries"
        )
        return
    if len(set(counts.values())) != 1:
        rendered_counts = ", ".join(f"{label}={count}" for label, count in counts.items())
        errors.append(
            f"{artifact_path.relative_to(ROOT)} has unbalanced delegated-slice "
            f"labels: {rendered_counts}"
        )


def validate_listed_delegated_slice_block(
    *,
    artifact_path: Path,
    lines: list[str],
    start_index: int,
    errors: list[str],
) -> int | None:
    slice_prefixes = [
        "slice id: ",
        "slice type: ",
        "owned surfaces: ",
        "touched surfaces: ",
    ]
    block_index = start_index
    slice_count = 0
    while block_index < len(lines) and lines[block_index].startswith("slice id: "):
        for prefix in slice_prefixes:
            if block_index >= len(lines) or not lines[block_index].startswith(prefix):
                errors.append(
                    f"{artifact_path.relative_to(ROOT)} must keep each delegated-slice "
                    "block contiguous and ordered as `slice id:`, `slice type:`, "
                    "`owned surfaces:`, `touched surfaces:`"
                )
                return None
            if not lines[block_index][len(prefix) :].strip():
                errors.append(
                    f"{artifact_path.relative_to(ROOT)} must give a value on the "
                    f"`{prefix[:-2]}` line"
                )
                return None
            block_index += 1
        slice_count += 1

    if slice_count == 0:
        errors.append(
            f"{artifact_path.relative_to(ROOT)} declares `delegated slices: listed` "
            "but has no contiguous delegated-slice block in the top-of-file header"
        )
        return None
    return block_index
