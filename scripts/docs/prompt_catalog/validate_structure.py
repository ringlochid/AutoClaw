from __future__ import annotations

from typing import Any

from .load import (
    CANONICAL_SEND_MODE_IDS,
    EXACT_BLOCK_CONSUMPTION_MODES,
    PROMPT_ASSET_ROOT,
    PROMPT_LAYER_ROOT,
    ROOT,
    SECTION_HEADINGS,
    list_exact_prompt_block_assets,
)
from .validate_contracts import CatalogValidationState, GeneratedExampleRecord
from .validate_families import validate_prompt_families, validate_rule_text
from .validate_support import as_string_list, owner_doc_paths


def validate_catalog_structure(
    data: dict[str, Any],
    errors: list[str],
) -> CatalogValidationState:
    _validate_version(data, errors)
    _validate_owner_docs(data, errors)
    section_order = _validate_section_definitions(data, errors)
    send_mode_ids = _validate_send_modes(data, errors)
    exact_block_ids = _validate_exact_blocks(data, errors)
    generated_artifacts = _validate_generated_artifacts(data, errors)
    generated_example_ids, generated_example_records = _validate_generated_examples(
        data,
        send_mode_ids,
        errors,
    )
    _validate_validation_references(data, errors)
    family_ids = validate_prompt_families(
        data,
        send_mode_ids,
        section_order,
        exact_block_ids,
        generated_example_ids,
        errors,
    )
    validate_rule_text(data, send_mode_ids, errors)
    return CatalogValidationState(
        family_ids=tuple(family_ids),
        send_mode_ids=tuple(send_mode_ids),
        exact_block_ids=tuple(exact_block_ids),
        generated_artifacts=tuple(generated_artifacts),
        generated_example_ids=tuple(generated_example_ids),
        generated_example_records=tuple(generated_example_records),
    )


def _validate_version(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("version") != 1:
        errors.append("catalog version must be 1")


def _validate_owner_docs(data: dict[str, Any], errors: list[str]) -> None:
    owner_docs = as_string_list(data.get("owner_docs"), field_name="owner_docs", errors=errors)
    for owner_doc_path in owner_doc_paths(owner_docs):
        if not owner_doc_path.exists():
            errors.append(f"owner doc is missing: {owner_doc_path.relative_to(ROOT)}")


def _validate_section_definitions(data: dict[str, Any], errors: list[str]) -> list[str]:
    section_order = as_string_list(
        data.get("section_order"),
        field_name="section_order",
        errors=errors,
    )
    unknown_sections = [section for section in section_order if section not in SECTION_HEADINGS]
    if unknown_sections:
        errors.append(f"unknown section ids: {', '.join(unknown_sections)}")

    static_sections = as_string_list(
        data.get("static_sections"),
        field_name="static_sections",
        errors=errors,
        allow_empty=True,
    )
    for section in static_sections:
        if section not in section_order:
            errors.append(f"static section `{section}` is not in section_order")
    return section_order


def _validate_send_modes(data: dict[str, Any], errors: list[str]) -> list[str]:
    send_modes = data.get("send_modes")
    if not isinstance(send_modes, list) or not send_modes:
        errors.append("send_modes must be a non-empty list of mappings")
        return []

    send_mode_ids: list[str] = []
    for index, send_mode in enumerate(send_modes):
        prefix = f"send_modes[{index}]"
        if not isinstance(send_mode, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        send_mode_id = send_mode.get("id")
        if not isinstance(send_mode_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        send_mode_ids.append(send_mode_id)

    if len(send_mode_ids) != len(set(send_mode_ids)):
        errors.append("send mode ids contain duplicates")
    if send_mode_ids != CANONICAL_SEND_MODE_IDS:
        errors.append("send mode ids must be exactly [full_prompt, same_session_continue] in order")
    return send_mode_ids


def _validate_exact_blocks(data: dict[str, Any], errors: list[str]) -> list[str]:
    exact_blocks = data.get("exact_blocks")
    if not isinstance(exact_blocks, list) or not exact_blocks:
        errors.append("exact_blocks must be a non-empty list")
        return []

    exact_prompt_assets = {asset.id: asset for asset in list_exact_prompt_block_assets()}
    exact_block_ids: list[str] = []
    for index, block in enumerate(exact_blocks):
        prefix = f"exact_blocks[{index}]"
        if not isinstance(block, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        block_id = block.get("id")
        if not isinstance(block_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        exact_block_ids.append(block_id)
        _validate_exact_block_metadata(block, prefix, exact_prompt_assets, errors)

    if len(exact_block_ids) != len(set(exact_block_ids)):
        errors.append("exact block ids contain duplicates")
    extra_asset_ids = sorted(set(exact_prompt_assets) - set(exact_block_ids))
    if extra_asset_ids:
        errors.append(
            "app-owned prompt assets are missing from prompt-catalog.yaml exact_blocks: "
            + ", ".join(extra_asset_ids)
        )
    return exact_block_ids


def _validate_exact_block_metadata(
    block: dict[str, Any],
    prefix: str,
    exact_prompt_assets: dict[str, Any],
    errors: list[str],
) -> None:
    block_id = block["id"]
    owner_file = block.get("owner_file")
    role = block.get("role")
    purpose = block.get("purpose")
    consumption = block.get("consumption")

    if not isinstance(owner_file, str):
        errors.append(f"{prefix}.owner_file must be a string")
    else:
        owner_path = PROMPT_LAYER_ROOT / owner_file
        if not owner_path.exists():
            errors.append(f"{prefix}.owner_file is missing: {owner_path.relative_to(ROOT)}")
        elif block_id not in owner_path.read_text(encoding="utf-8"):
            errors.append(f"{prefix}.owner_file does not mention `{block_id}`")

    asset = exact_prompt_assets.get(block_id)
    if asset is None:
        errors.append(
            f"{prefix}.id is missing from app-owned prompt assets under "
            f"{PROMPT_ASSET_ROOT.relative_to(ROOT)}"
        )
    elif owner_file != asset.mirror_doc:
        errors.append(
            f"{prefix}.owner_file must match packaged prompt asset mirror doc `{asset.mirror_doc}`"
        )

    if not isinstance(role, str):
        errors.append(f"{prefix}.role must be a string")
    if not isinstance(purpose, str):
        errors.append(f"{prefix}.purpose must be a string")
    if not isinstance(consumption, str):
        errors.append(f"{prefix}.consumption must be a string")
    elif consumption not in EXACT_BLOCK_CONSUMPTION_MODES:
        errors.append(
            f"{prefix}.consumption must be one of "
            f"{sorted(EXACT_BLOCK_CONSUMPTION_MODES)}, found `{consumption}`"
        )


def _validate_generated_artifacts(data: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    generated_artifacts = data.get("generated_artifacts")
    if not isinstance(generated_artifacts, list) or not generated_artifacts:
        errors.append("generated_artifacts must be a non-empty list")
        return []

    generated_artifact_ids: list[str] = []
    for index, artifact in enumerate(generated_artifacts):
        prefix = f"generated_artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        artifact_id = artifact.get("id")
        artifact_path = artifact.get("path")
        if not isinstance(artifact_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        generated_artifact_ids.append(artifact_id)
        if not isinstance(artifact_path, str):
            errors.append(f"{prefix}.path must be a string")
            continue
        resolved_path = PROMPT_LAYER_ROOT / artifact_path
        if not resolved_path.exists():
            errors.append(f"{prefix}.path is missing: {resolved_path.relative_to(ROOT)}")

    if len(generated_artifact_ids) != len(set(generated_artifact_ids)):
        errors.append("generated artifact ids contain duplicates")
    return [artifact for artifact in generated_artifacts if isinstance(artifact, dict)]


def _validate_generated_examples(
    data: dict[str, Any],
    send_mode_ids: list[str],
    errors: list[str],
) -> tuple[list[str], list[GeneratedExampleRecord]]:
    generated_examples = data.get("generated_examples")
    if not isinstance(generated_examples, list) or not generated_examples:
        errors.append("generated_examples must be a non-empty list")
        return [], []

    generated_example_ids: list[str] = []
    generated_example_records: list[GeneratedExampleRecord] = []
    for index, example in enumerate(generated_examples):
        prefix = f"generated_examples[{index}]"
        if not isinstance(example, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        record = _validate_generated_example(example, prefix, send_mode_ids, errors)
        if record is None:
            continue
        generated_example_ids.append(record.id)
        generated_example_records.append(record)

    if len(generated_example_ids) != len(set(generated_example_ids)):
        errors.append("generated example ids contain duplicates")
    return generated_example_ids, generated_example_records


def _validate_generated_example(
    example: dict[str, Any],
    prefix: str,
    send_mode_ids: list[str],
    errors: list[str],
) -> GeneratedExampleRecord | None:
    example_id = example.get("id")
    family = example.get("family")
    send_mode = example.get("send_mode")
    rendered_heading = example.get("rendered_heading")
    source_file = example.get("source_file")

    if not isinstance(example_id, str):
        errors.append(f"{prefix}.id must be a string")
        return None
    if not isinstance(rendered_heading, str):
        errors.append(f"{prefix}.rendered_heading must be a string")
        rendered_heading = ""
    if not isinstance(family, str):
        errors.append(f"{prefix}.family must be a string")
        family = ""
    if not isinstance(send_mode, str):
        errors.append(f"{prefix}.send_mode must be a string")
        send_mode = ""
    elif send_mode not in send_mode_ids:
        errors.append(f"{prefix}.send_mode uses unknown send mode `{send_mode}`")
    if not isinstance(source_file, str):
        errors.append(f"{prefix}.source_file must be a string")
    else:
        source_path = PROMPT_LAYER_ROOT / source_file
        if not source_path.exists():
            errors.append(f"{prefix}.source_file is missing: {source_path.relative_to(ROOT)}")
    return GeneratedExampleRecord(
        id=example_id,
        family=family,
        send_mode=send_mode,
        rendered_heading=rendered_heading,
    )


def _validate_validation_references(data: dict[str, Any], errors: list[str]) -> None:
    validation_references = data.get("validation_references")
    if not isinstance(validation_references, list) or not validation_references:
        errors.append("validation_references must be a non-empty list")
        return

    validation_reference_ids: list[str] = []
    for index, reference in enumerate(validation_references):
        prefix = f"validation_references[{index}]"
        if not isinstance(reference, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        reference_id = reference.get("id")
        if not isinstance(reference_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        validation_reference_ids.append(reference_id)
        owner_doc_list = as_string_list(
            reference.get("owner_docs"),
            field_name=f"{prefix}.owner_docs",
            errors=errors,
            allow_empty=False,
        )
        for owner_doc in owner_doc_list:
            owner_path = (PROMPT_LAYER_ROOT / owner_doc).resolve()
            if not owner_path.exists():
                errors.append(
                    f"{prefix}.owner_docs entry is missing: {owner_path.relative_to(ROOT)}"
                )

    if len(validation_reference_ids) != len(set(validation_reference_ids)):
        errors.append("validation reference ids contain duplicates")
