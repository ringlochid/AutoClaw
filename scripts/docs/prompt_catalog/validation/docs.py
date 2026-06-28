from __future__ import annotations

from typing import Any

from ..extract import (
    extract_exact_block_text_from_mirror_doc,
    extract_first_text_code_block,
    extract_markdown_section,
)
from ..load import (
    COMPOSITION_PATH,
    EXAMPLES_PATH,
    INVENTORY_PATH,
    LIVE_PROMPT_SURFACE_PATHS,
    PROMPT_ASSET_ROOT,
    PROMPT_LAYER_ROOT,
    ROOT,
    SECTION_HEADINGS,
    list_exact_prompt_block_assets,
    load_exact_prompt_block,
)
from ..render import render_generated_example_bodies


def _validate_live_prompt_surface_paths(errors: list[str], *, skip_inventory: bool = False) -> None:
    for path in LIVE_PROMPT_SURFACE_PATHS:
        if skip_inventory and path == INVENTORY_PATH:
            continue
        text = path.read_text(encoding="utf-8")
        if "lock_next/" in text or "lock_next\\" in text:
            errors.append(
                f"{path.relative_to(ROOT)} still routes live prompt semantics to lock_next/"
            )


def _validate_current_assignment_examples(
    errors: list[str], *, skip_generated_examples: bool = False
) -> None:
    example_paths = [PROMPT_LAYER_ROOT / "field-renderers.md", COMPOSITION_PATH]
    if not skip_generated_examples:
        example_paths.insert(1, EXAMPLES_PATH)
    for path in example_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        in_current_assignment = False
        subsection: str | None = None
        criteria_entry_has_kind = False
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped in {
                "Current Assignment",
                "## Current Assignment",
                "### Current Assignment",
            }:
                in_current_assignment = True
                subsection = None
                criteria_entry_has_kind = False
                continue
            if not in_current_assignment:
                continue
            if stripped in SECTION_HEADINGS.values() and stripped != "Current Assignment":
                in_current_assignment = False
                subsection = None
                criteria_entry_has_kind = False
                continue
            if stripped.startswith(("## ", "### ")) or stripped == "```":
                in_current_assignment = False
                subsection = None
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- criteria:"):
                subsection = "criteria"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- consumes:"):
                subsection = "consumes"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- produces:"):
                subsection = "produces"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- transient_refs:"):
                subsection = "transient_refs"
                criteria_entry_has_kind = False
                continue
            if stripped.startswith("- task_memory_search_hints:"):
                subsection = "task_memory_search_hints"
                criteria_entry_has_kind = False
                continue
            if subsection == "criteria" and stripped == "- kind: criteria":
                criteria_entry_has_kind = True
                continue
            if (
                subsection == "criteria"
                and (stripped.startswith("- slot:") or stripped.startswith("slot:"))
                and not criteria_entry_has_kind
            ):
                errors.append(
                    f"{path.relative_to(ROOT)} is missing `kind: criteria` in Current Assignment "
                    f"`criteria` at line {line_number}"
                )
            if subsection in {"criteria", "consumes", "produces"} and (
                stripped.startswith("path:") or stripped.startswith("version:")
            ):
                leaked_field = stripped.split(":", 1)[0]
                errors.append(
                    f"{path.relative_to(ROOT)} leaks `{leaked_field}` into "
                    f"Current Assignment `{subsection}` at line {line_number}"
                )


def _validate_assignment_and_checkpoint_path_lines(
    errors: list[str], *, skip_generated_examples: bool = False
) -> None:
    section_specs = [
        (PROMPT_LAYER_ROOT / "source-and-sections.md", "Current Assignment", "- path:"),
        (PROMPT_LAYER_ROOT / "field-renderers.md", "Current Assignment", "- path:"),
        (COMPOSITION_PATH, "Current Assignment", "- path:"),
        (PROMPT_LAYER_ROOT / "field-renderers.md", "Latest Checkpoint Context", "- path:"),
        (COMPOSITION_PATH, "Latest Checkpoint Context", "- path:"),
    ]
    if not skip_generated_examples:
        section_specs.insert(2, (EXAMPLES_PATH, "Current Assignment", "- path:"))
        section_specs.insert(5, (EXAMPLES_PATH, "Latest Checkpoint Context", "- path:"))
    for path, section_heading, required_prefix in section_specs:
        lines = path.read_text(encoding="utf-8").splitlines()
        in_section = False
        saw_required_line = False
        saw_section = False
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped in {
                section_heading,
                f"## {section_heading}",
                f"### {section_heading}",
            }:
                saw_section = True
                in_section = True
                saw_required_line = False
                continue
            if not in_section:
                continue
            if stripped in SECTION_HEADINGS.values() and stripped != section_heading:
                if not saw_required_line:
                    errors.append(
                        f"{path.relative_to(ROOT)} section `{section_heading}` is "
                        f"missing a `{required_prefix}` line before line {line_number}"
                    )
                in_section = False
                continue
            if stripped.startswith(("## ", "### ")) or stripped == "```":
                if not saw_required_line:
                    errors.append(
                        f"{path.relative_to(ROOT)} section `{section_heading}` is "
                        f"missing a `{required_prefix}` line before line {line_number}"
                    )
                in_section = False
                continue
            if stripped.startswith(required_prefix):
                saw_required_line = True
        if saw_section and in_section and not saw_required_line:
            errors.append(
                f"{path.relative_to(ROOT)} section `{section_heading}` is missing a "
                f"`{required_prefix}` line"
            )


def _validate_exact_block_asset_mirrors(errors: list[str]) -> None:
    for asset in list_exact_prompt_block_assets():
        mirror_path = PROMPT_LAYER_ROOT / asset.mirror_doc
        if not mirror_path.exists():
            errors.append(
                f"missing mirror doc for exact prompt block `{asset.id}`: {asset.mirror_doc}"
            )
            continue
        try:
            mirror_text = extract_exact_block_text_from_mirror_doc(mirror_path, asset.id)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        asset_text = load_exact_prompt_block(asset.id)
        if mirror_text != asset_text:
            errors.append(
                "exact prompt block mirror drift: "
                f"{mirror_path.relative_to(ROOT)} no longer matches byte-for-byte "
                f"{PROMPT_ASSET_ROOT.relative_to(ROOT) / asset.asset_path}"
            )


def _validate_generated_example_parity(errors: list[str]) -> None:
    rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
    for heading, expected_text in render_generated_example_bodies().items():
        section = extract_markdown_section(rendered_examples_text, f"## `{heading}`")
        if section is None:
            errors.append(f"generated/rendered-examples.md is missing section `## `{heading}``")
            continue
        actual_text = extract_first_text_code_block(section)
        if actual_text is None:
            errors.append(
                "generated/rendered-examples.md section "
                f"`## `{heading}`` is missing a text code block"
            )
            continue
        if actual_text.strip() != expected_text.strip():
            errors.append(
                f"generated/rendered-examples.md drifted from live renderer output for `{heading}`"
            )


def _section_between(text: str, heading: str, next_heading: str) -> str:
    marker = f"### {heading}"
    next_marker = f"### {next_heading}"
    if marker not in text:
        return ""
    section = text.split(marker, maxsplit=1)[1]
    if next_marker in section:
        section = section.split(next_marker, maxsplit=1)[0]
    return section


def _validate_non_root_parent_blocked_example(
    data: dict[str, Any],
    errors: list[str],
) -> None:
    required_heading = "parent_root_dispatch_prompt non-root blocked closure"
    registered_headings = {
        example.get("rendered_heading")
        for example in data.get("generated_examples", [])
        if isinstance(example, dict)
    }
    if required_heading not in registered_headings:
        errors.append("generated_examples is missing the non-root parent blocked closure example")
        return

    example_body = render_generated_example_bodies().get(required_heading)
    if example_body is None:
        errors.append("non-root parent blocked closure example has no generated body")
        return

    current_dispatch = _section_between(example_body, "Current Dispatch", "Workflow Manifest")
    latest_checkpoint = _section_between(
        example_body,
        "Latest Checkpoint Context",
        "Consumed Durable Refs",
    )
    allowed_actions = _section_between(example_body, "Allowed Actions Now", "Publication Rule")

    if "- node kind: parent" not in current_dispatch:
        errors.append("non-root parent blocked example is not rendered as node_kind: parent")
    if "- checkpoint_kind: terminal" not in latest_checkpoint:
        errors.append("non-root parent blocked example is missing terminal checkpoint context")
    if "- outcome: blocked" not in latest_checkpoint:
        errors.append("non-root parent blocked example is missing blocked checkpoint outcome")
    if "`autoclaw-node__release_blocked`" in allowed_actions:
        errors.append("non-root parent blocked example surfaces root-only release_blocked")
    if (
        "emit `blocked` only when this node cannot complete its current assignment "
        "and has published a terminal blocked checkpoint" not in allowed_actions
    ):
        errors.append("non-root parent blocked example omits terminal blocked closure guidance")
    if "root whole-flow terminal closure after committed `release_blocked`" in allowed_actions:
        errors.append("non-root parent blocked example teaches the root-only blocked path")


def run_doc_example_checks(
    data: dict[str, Any],
    errors: list[str],
    *,
    skip_inventory_checks: bool,
) -> None:
    _validate_live_prompt_surface_paths(errors, skip_inventory=skip_inventory_checks)
    _validate_exact_block_asset_mirrors(errors)
    _validate_current_assignment_examples(errors, skip_generated_examples=skip_inventory_checks)
    _validate_assignment_and_checkpoint_path_lines(
        errors,
        skip_generated_examples=skip_inventory_checks,
    )
    if not skip_inventory_checks:
        _validate_generated_example_parity(errors)
    _validate_non_root_parent_blocked_example(data, errors)
