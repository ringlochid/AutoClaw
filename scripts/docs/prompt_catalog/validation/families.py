from __future__ import annotations

from typing import Any

from ..load import EXAMPLES_PATH, EXPECTED_CLOSURE_MODES, INVENTORY_PATH
from .contracts import CatalogValidationState
from .fields import as_string_list


def validate_prompt_families(
    data: dict[str, Any],
    send_mode_ids: list[str],
    section_order: list[str],
    exact_block_ids: list[str],
    generated_example_ids: list[str],
    errors: list[str],
) -> list[str]:
    prompt_families = data.get("prompt_families")
    if not isinstance(prompt_families, list) or not prompt_families:
        errors.append("prompt_families must be a non-empty list")
        return []

    family_ids: list[str] = []
    for index, family in enumerate(prompt_families):
        prefix = f"prompt_families[{index}]"
        if not isinstance(family, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        family_ids.append(family_id)
        _validate_prompt_family(
            family,
            family_id,
            send_mode_ids,
            section_order,
            exact_block_ids,
            generated_example_ids,
            errors,
        )

    if len(family_ids) != len(set(family_ids)):
        errors.append("prompt family ids contain duplicates")
    if sorted(family_ids) != ["parent_root_dispatch_prompt", "worker_dispatch_prompt"]:
        errors.append(
            "prompt family ids must be exactly "
            "parent_root_dispatch_prompt and worker_dispatch_prompt"
        )
    return family_ids


def validate_rule_text(
    data: dict[str, Any],
    send_mode_ids: list[str],
    errors: list[str],
) -> None:
    rules = as_string_list(data.get("rules"), field_name="rules", errors=errors)
    validator_checks = as_string_list(
        data.get("validator_checks"),
        field_name="validator_checks",
        errors=errors,
    )
    if (
        rules
        and "same_session_continue is a transport-only optimization inside the same attempt"
        not in rules
    ):
        errors.append("rules is missing the same_session_continue transport-only rule")

    same_session_send_mode = next(
        (
            send_mode
            for send_mode in data.get("send_modes", [])
            if isinstance(send_mode, dict) and send_mode.get("id") == "same_session_continue"
        ),
        None,
    )
    if isinstance(same_session_send_mode, dict):
        legal_only_when = as_string_list(
            same_session_send_mode.get("legal_only_when"),
            field_name="same_session_continue.legal_only_when",
            errors=errors,
        )
        required_clause = (
            "a bound previous_response_id already exists for the current dispatch transport request"
        )
        if send_mode_ids and legal_only_when and required_clause not in legal_only_when:
            errors.append(
                "same_session_continue.legal_only_when is missing the previous_response_id rule"
            )

    if (
        validator_checks
        and "freeze exactly two canonical dispatch prompt families" not in validator_checks
    ):
        errors.append("validator_checks is missing the canonical prompt-family freeze rule")


def validate_generated_outputs(state: CatalogValidationState, errors: list[str]) -> None:
    _validate_inventory_presence(state, errors)
    _validate_rendered_example_presence(state, errors)


def _validate_prompt_family(
    family: dict[str, Any],
    family_id: str,
    send_mode_ids: list[str],
    section_order: list[str],
    exact_block_ids: list[str],
    generated_example_ids: list[str],
    errors: list[str],
) -> None:
    as_string_list(family.get("node_kinds"), field_name=f"{family_id}.node_kinds", errors=errors)
    _validate_allowed_send_modes(family, family_id, send_mode_ids, errors)
    _validate_required_sections(family, family_id, section_order, errors)
    _validate_conditional_sections(family, family_id, section_order, errors)
    _validate_closure_modes(family, family_id, errors)
    _validate_family_exact_blocks(family, family_id, exact_block_ids, errors)
    _validate_family_examples(family, family_id, generated_example_ids, errors)


def _validate_allowed_send_modes(
    family: dict[str, Any],
    family_id: str,
    send_mode_ids: list[str],
    errors: list[str],
) -> None:
    allowed_send_modes = as_string_list(
        family.get("allowed_send_modes"),
        field_name=f"{family_id}.allowed_send_modes",
        errors=errors,
    )
    for send_mode in allowed_send_modes:
        if send_mode not in send_mode_ids:
            errors.append(
                f"{family_id}.allowed_send_modes contains unknown send mode `{send_mode}`"
            )


def _validate_required_sections(
    family: dict[str, Any],
    family_id: str,
    section_order: list[str],
    errors: list[str],
) -> None:
    required_sections = as_string_list(
        family.get("required_sections"),
        field_name=f"{family_id}.required_sections",
        errors=errors,
    )
    for section in required_sections:
        if section not in section_order:
            errors.append(f"{family_id}.required_sections contains unknown section `{section}`")


def _validate_conditional_sections(
    family: dict[str, Any],
    family_id: str,
    section_order: list[str],
    errors: list[str],
) -> None:
    conditional_sections = family.get("conditionally_required_sections")
    if not isinstance(conditional_sections, list):
        errors.append(f"{family_id}.conditionally_required_sections must be a list")
        return

    for conditional_index, conditional in enumerate(conditional_sections):
        conditional_prefix = f"{family_id}.conditionally_required_sections[{conditional_index}]"
        if not isinstance(conditional, dict):
            errors.append(f"{conditional_prefix} must be a mapping")
            continue
        conditional_section = conditional.get("section")
        when = conditional.get("when")
        if not isinstance(conditional_section, str):
            errors.append(f"{conditional_prefix}.section must be a string")
        elif conditional_section not in section_order:
            errors.append(
                f"{conditional_prefix}.section is not in section_order: {conditional_section}"
            )
        if not isinstance(when, str):
            errors.append(f"{conditional_prefix}.when must be a string")


def _validate_closure_modes(family: dict[str, Any], family_id: str, errors: list[str]) -> None:
    as_string_list(
        family.get("closure_modes"),
        field_name=f"{family_id}.closure_modes",
        errors=errors,
    )
    expected_closure_modes = EXPECTED_CLOSURE_MODES.get(family_id)
    if expected_closure_modes is None:
        return
    actual_closure_modes = family.get("closure_modes")
    if actual_closure_modes != expected_closure_modes:
        errors.append(
            f"{family_id}.closure_modes must be exactly "
            f"{expected_closure_modes}, found {actual_closure_modes}"
        )


def _validate_family_exact_blocks(
    family: dict[str, Any],
    family_id: str,
    exact_block_ids: list[str],
    errors: list[str],
) -> None:
    family_exact_blocks = family.get("exact_blocks")
    if not isinstance(family_exact_blocks, dict):
        errors.append(f"{family_id}.exact_blocks must be a mapping")
        return
    for block_bucket, block_ids in family_exact_blocks.items():
        normalized_ids = as_string_list(
            block_ids,
            field_name=f"{family_id}.exact_blocks.{block_bucket}",
            errors=errors,
        )
        for block_id in normalized_ids:
            if block_id not in exact_block_ids:
                errors.append(
                    f"{family_id}.exact_blocks.{block_bucket} references unknown block `{block_id}`"
                )


def _validate_family_examples(
    family: dict[str, Any],
    family_id: str,
    generated_example_ids: list[str],
    errors: list[str],
) -> None:
    family_generated_examples = as_string_list(
        family.get("generated_examples"),
        field_name=f"{family_id}.generated_examples",
        errors=errors,
    )
    for example_id in family_generated_examples:
        if example_id not in generated_example_ids:
            errors.append(
                f"{family_id}.generated_examples references unknown example `{example_id}`"
            )


def _validate_inventory_presence(state: CatalogValidationState, errors: list[str]) -> None:
    inventory_text = INVENTORY_PATH.read_text(encoding="utf-8")
    for family_id in state.family_ids:
        if family_id not in inventory_text:
            errors.append(f"generated/inventory.md is missing prompt family `{family_id}`")
    for send_mode_id in state.send_mode_ids:
        if send_mode_id not in inventory_text:
            errors.append(f"generated/inventory.md is missing send mode `{send_mode_id}`")
    for block_id in state.exact_block_ids:
        if block_id not in inventory_text:
            errors.append(f"generated/inventory.md is missing exact block `{block_id}`")
    for artifact in state.generated_artifacts:
        artifact_id = artifact.get("id")
        if isinstance(artifact_id, str) and artifact_id not in inventory_text:
            errors.append(f"generated/inventory.md is missing generated artifact `{artifact_id}`")
    for example_id in state.generated_example_ids:
        if example_id not in inventory_text:
            errors.append(f"generated/inventory.md is missing generated example `{example_id}`")


def _validate_rendered_example_presence(
    state: CatalogValidationState,
    errors: list[str],
) -> None:
    rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
    for example in state.generated_example_records:
        if example.rendered_heading and example.rendered_heading in rendered_examples_text:
            continue
        if example.family and example.family not in rendered_examples_text:
            errors.append(
                f"generated/rendered-examples.md is missing prompt family `{example.family}`"
            )
            continue
        if example.send_mode and example.send_mode not in rendered_examples_text:
            errors.append(
                f"generated/rendered-examples.md is missing send mode `{example.send_mode}`"
            )
