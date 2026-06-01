from __future__ import annotations

from typing import Any

from scripts.docs.prompt_catalog.load import (
    CANONICAL_SEND_MODE_IDS,
    PROMPT_FAMILY_NODE_KINDS,
    NodeKind,
    live_instruction_block_inventory,
    prompt_family_for_node_kind,
)
from scripts.docs.prompt_catalog.validation.fields import as_string_list


def run_runtime_mapping_checks(data: dict[str, Any], errors: list[str]) -> None:
    _validate_live_prompt_family_node_kind_alignment(data, errors)
    _validate_live_instruction_block_consumption(data, errors)


def _validate_live_prompt_family_node_kind_alignment(
    data: dict[str, Any],
    errors: list[str],
) -> None:
    live_mapping = PROMPT_FAMILY_NODE_KINDS
    if not isinstance(live_mapping, dict):
        errors.append("live prompt family/node kind mapping must be a mapping")
        return

    catalog_mapping = _catalog_node_kind_mapping(data, errors)
    normalized_live_mapping = _normalize_live_prompt_family_mapping(live_mapping, errors)
    _validate_family_node_kind_pairs(catalog_mapping, normalized_live_mapping, errors)
    _validate_node_kind_routing(catalog_mapping, errors)


def _catalog_node_kind_mapping(
    data: dict[str, Any],
    errors: list[str],
) -> dict[str, tuple[str, ...]]:
    catalog_mapping: dict[str, tuple[str, ...]] = {}
    for family in data.get("prompt_families", []):
        if not isinstance(family, dict):
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            continue
        catalog_mapping[family_id] = tuple(
            as_string_list(
                family.get("node_kinds"),
                field_name=f"{family_id}.node_kinds",
                errors=errors,
            )
        )
    return catalog_mapping


def _normalize_live_prompt_family_mapping(
    live_mapping: dict[Any, Any],
    errors: list[str],
) -> dict[str, tuple[str, ...]]:
    normalized_live_mapping: dict[str, tuple[str, ...]] = {}
    for prompt_family, node_kinds in live_mapping.items():
        family_id = getattr(prompt_family, "value", None)
        if not isinstance(family_id, str):
            errors.append("live prompt family/node kind mapping contains a non-enum family key")
            continue
        normalized_node_kinds = _normalize_live_node_kind_sequence(family_id, node_kinds, errors)
        if normalized_node_kinds:
            normalized_live_mapping[family_id] = normalized_node_kinds
    return normalized_live_mapping


def _normalize_live_node_kind_sequence(
    family_id: str,
    node_kinds: Any,
    errors: list[str],
) -> tuple[str, ...]:
    if not isinstance(node_kinds, tuple):
        if isinstance(node_kinds, list):
            node_kinds = tuple(node_kinds)
        else:
            errors.append(
                f"live prompt family/node kind mapping for `{family_id}` must be a sequence"
            )
            return ()

    normalized_node_kinds: list[str] = []
    for node_kind in node_kinds:
        node_kind_id = getattr(node_kind, "value", None)
        if not isinstance(node_kind_id, str):
            errors.append(
                "live prompt family/node kind mapping for "
                f"`{family_id}` contains a non-enum node kind"
            )
            return ()
        normalized_node_kinds.append(node_kind_id)
    return tuple(normalized_node_kinds)


def _validate_family_node_kind_pairs(
    catalog_mapping: dict[str, tuple[str, ...]],
    normalized_live_mapping: dict[str, tuple[str, ...]],
    errors: list[str],
) -> None:
    for family_id, live_node_kinds in normalized_live_mapping.items():
        catalog_node_kinds = catalog_mapping.get(family_id)
        if catalog_node_kinds is None:
            errors.append(
                f"prompt catalog is missing live prompt family `{family_id}` for node-kind audit"
            )
            continue
        if catalog_node_kinds != live_node_kinds:
            errors.append(
                f"{family_id}.node_kinds must match live runtime mapping "
                f"{list(live_node_kinds)}, found {list(catalog_node_kinds)}"
            )


def _validate_node_kind_routing(
    catalog_mapping: dict[str, tuple[str, ...]],
    errors: list[str],
) -> None:
    for node_kind in NodeKind:
        node_kind_id = getattr(node_kind, "value", None)
        if not isinstance(node_kind_id, str):
            errors.append("live NodeKind enum contains a non-string value")
            continue
        live_family = prompt_family_for_node_kind(node_kind)
        live_family_id = getattr(live_family, "value", None)
        if not isinstance(live_family_id, str):
            errors.append(
                f"live prompt_family_for_node_kind returned a non-enum family for `{node_kind_id}`"
            )
            continue
        catalog_family_ids = sorted(
            family_id
            for family_id, node_kinds in catalog_mapping.items()
            if node_kind_id in node_kinds
        )
        if catalog_family_ids != [live_family_id]:
            errors.append(
                f"catalog node-kind routing drift for `{node_kind_id}`: expected only "
                f"`{live_family_id}`, found {catalog_family_ids or ['<none>']}"
            )


def _validate_live_instruction_block_consumption(
    data: dict[str, Any],
    errors: list[str],
) -> None:
    inventory = live_instruction_block_inventory()
    if not isinstance(inventory, dict):
        errors.append("live instruction block inventory must be a mapping")
        return

    exact_block_consumption_by_id = _exact_block_consumption_by_id(data)
    all_consumed_block_ids: set[str] = set()
    all_listed_block_ids: set[str] = set()
    for family in data.get("prompt_families", []):
        if not isinstance(family, dict):
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            continue
        family_inventory = inventory.get(family_id)
        if not isinstance(family_inventory, dict):
            errors.append(f"live instruction block inventory is missing family `{family_id}`")
            continue
        _validate_family_instruction_inventory(
            family,
            family_id,
            family_inventory,
            exact_block_consumption_by_id,
            all_consumed_block_ids,
            all_listed_block_ids,
            errors,
        )

    _validate_global_instruction_inventory(
        exact_block_consumption_by_id,
        all_consumed_block_ids,
        all_listed_block_ids,
        errors,
    )


def _exact_block_consumption_by_id(data: dict[str, Any]) -> dict[str, str]:
    exact_block_consumption_by_id: dict[str, str] = {}
    exact_blocks = data.get("exact_blocks")
    if not isinstance(exact_blocks, list):
        return exact_block_consumption_by_id
    for block in exact_blocks:
        if not isinstance(block, dict):
            continue
        block_id = block.get("id")
        consumption = block.get("consumption")
        if isinstance(block_id, str) and isinstance(consumption, str):
            exact_block_consumption_by_id[block_id] = consumption
    return exact_block_consumption_by_id


def _validate_family_instruction_inventory(
    family: dict[str, Any],
    family_id: str,
    family_inventory: dict[str, Any],
    exact_block_consumption_by_id: dict[str, str],
    all_consumed_block_ids: set[str],
    all_listed_block_ids: set[str],
    errors: list[str],
) -> None:
    consumed_block_ids = _collect_consumed_block_ids(family_inventory, family_id, errors)
    listed_block_ids = _family_listed_block_ids(family, family_id, errors)
    all_consumed_block_ids.update(consumed_block_ids)
    all_listed_block_ids.update(listed_block_ids)

    reference_only_block_ids = sorted(
        block_id
        for block_id in listed_block_ids
        if exact_block_consumption_by_id.get(block_id) == "reference_only"
    )
    if reference_only_block_ids:
        errors.append(
            f"{family_id}.exact_blocks must not reference reference-only blocks: "
            f"{', '.join(reference_only_block_ids)}"
        )

    unconsumed_block_ids = sorted(listed_block_ids - consumed_block_ids)
    if unconsumed_block_ids:
        consumed_display = ", ".join(sorted(consumed_block_ids)) or "<none>"
        errors.append(
            f"{family_id}.exact_blocks lists blocks with no live instruction assembly path: "
            f"{', '.join(unconsumed_block_ids)}; live instruction blocks: {consumed_display}"
        )


def _collect_consumed_block_ids(
    family_inventory: dict[str, Any],
    family_id: str,
    errors: list[str],
) -> set[str]:
    consumed_block_ids: set[str] = set()
    for send_mode_id in CANONICAL_SEND_MODE_IDS:
        raw_block_ids = family_inventory.get(send_mode_id)
        if not isinstance(raw_block_ids, tuple):
            if isinstance(raw_block_ids, list):
                raw_block_ids = tuple(raw_block_ids)
            else:
                errors.append(
                    "live instruction block inventory must expose "
                    f"`{family_id}` / `{send_mode_id}` as a sequence of block ids"
                )
                continue
        if any(not isinstance(block_id, str) for block_id in raw_block_ids):
            errors.append(
                "live instruction block inventory contains non-string block ids for "
                f"`{family_id}` / `{send_mode_id}`"
            )
            continue
        consumed_block_ids.update(raw_block_ids)
    return consumed_block_ids


def _family_listed_block_ids(
    family: dict[str, Any],
    family_id: str,
    errors: list[str],
) -> set[str]:
    family_exact_blocks = family.get("exact_blocks")
    if not isinstance(family_exact_blocks, dict):
        return set()
    listed_block_ids: set[str] = set()
    for block_bucket, block_ids in family_exact_blocks.items():
        if not isinstance(block_bucket, str):
            continue
        listed_block_ids.update(
            as_string_list(
                block_ids,
                field_name=f"{family_id}.exact_blocks.{block_bucket}",
                errors=errors,
                allow_empty=True,
            )
        )
    return listed_block_ids


def _validate_global_instruction_inventory(
    exact_block_consumption_by_id: dict[str, str],
    all_consumed_block_ids: set[str],
    all_listed_block_ids: set[str],
    errors: list[str],
) -> None:
    live_block_ids = {
        block_id
        for block_id, consumption in exact_block_consumption_by_id.items()
        if consumption == "live_instruction_block"
    }
    missing_live_consumption = sorted(live_block_ids - all_consumed_block_ids)
    if missing_live_consumption:
        errors.append(
            "prompt-catalog exact_blocks marked live_instruction_block but not consumed by "
            "live runtime instruction assembly: " + ", ".join(missing_live_consumption)
        )

    mislabeled_consumed_blocks = sorted(
        block_id
        for block_id in all_consumed_block_ids
        if exact_block_consumption_by_id.get(block_id) != "live_instruction_block"
    )
    if mislabeled_consumed_blocks:
        errors.append(
            "live runtime instruction assembly consumes exact_blocks not marked "
            "live_instruction_block: " + ", ".join(mislabeled_consumed_blocks)
        )

    unlisted_live_blocks = sorted(live_block_ids - all_listed_block_ids)
    if unlisted_live_blocks:
        errors.append(
            "prompt families are missing live exact_blocks from their exact_blocks mappings: "
            + ", ".join(unlisted_live_blocks)
        )
