from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from autoclaw.runtime.errors import illegal_state_error

NodeSnapshot = dict[str, Any]


def refresh_descendant_defaults(
    nodes: list[NodeSnapshot],
    *,
    previous_parent: NodeSnapshot,
    updated_parent: NodeSnapshot,
) -> None:
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    children_by_parent: defaultdict[str, list[NodeSnapshot]] = defaultdict(list)
    for node in nodes:
        parent_node_key = node.get("parent_node_key")
        if parent_node_key is not None:
            children_by_parent[str(parent_node_key)].append(node)

    queue: deque[str] = deque()
    for child in children_by_parent.get(str(updated_parent["node_key"]), []):
        _remove_child_defaults(previous_parent, child)
        apply_child_defaults(updated_parent, child)
        queue.append(str(child["node_key"]))

    while queue:
        parent_node_key = queue.popleft()
        parent_node = nodes_by_key[parent_node_key]
        for child in children_by_parent.get(parent_node_key, []):
            apply_child_defaults(parent_node, child)
            queue.append(str(child["node_key"]))


def apply_child_defaults(parent: NodeSnapshot, child: NodeSnapshot) -> None:
    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return
    _remove_child_defaults(parent, child)
    criteria_defaults = _validated_child_default_criteria_slots(parent)
    if criteria_defaults:
        criteria_by_slot = {
            str(criteria["slot"]): dict(criteria) for criteria in parent.get("criteria_json", [])
        }
        local_criteria = [dict(criteria) for criteria in child["criteria_json"]]
        child["criteria_json"] = [
            criteria_by_slot[slot] for slot in criteria_defaults
        ] + local_criteria

    consumes_defaults = child_defaults.get("consumes")
    if isinstance(consumes_defaults, dict):
        local_consumes = child.get("consumes_json") or {}
        merged_artifacts = _merge_consume_selectors(
            consumes_defaults.get("artifacts") or [],
            local_consumes.get("artifacts") or [],
        )
        merged_criteria = _merge_consume_selectors(
            consumes_defaults.get("criteria") or [],
            local_consumes.get("criteria") or [],
        )
        if merged_artifacts or merged_criteria:
            child["consumes_json"] = {
                "artifacts": merged_artifacts or None,
                "criteria": merged_criteria or None,
            }
        else:
            child["consumes_json"] = None


def _validated_child_default_criteria_slots(parent: NodeSnapshot) -> tuple[str, ...]:
    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return ()
    criteria_defaults = list(child_defaults.get("criteria", []))
    if not criteria_defaults:
        return ()
    criteria_by_slot = {
        str(criteria["slot"]): dict(criteria) for criteria in parent.get("criteria_json", [])
    }
    validated_slots: list[str] = []
    seen_slots: set[str] = set()
    for slot in criteria_defaults:
        slot_key = str(slot)
        if slot_key in seen_slots:
            continue
        if slot_key not in criteria_by_slot:
            raise illegal_state_error(
                "child_defaults.criteria on node "
                f"'{parent['node_key']}' references unknown local criteria slot '{slot_key}'"
            )
        seen_slots.add(slot_key)
        validated_slots.append(slot_key)
    return tuple(validated_slots)


def _remove_child_defaults(parent: NodeSnapshot, child: NodeSnapshot) -> None:
    inherited_criteria_slots = set(_validated_child_default_criteria_slots(parent))
    if inherited_criteria_slots:
        child["criteria_json"] = [
            dict(criteria)
            for criteria in child["criteria_json"]
            if str(criteria["slot"]) not in inherited_criteria_slots
        ]

    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return
    consumes_defaults = child_defaults.get("consumes")
    if not isinstance(consumes_defaults, dict):
        return
    local_consumes = child.get("consumes_json") or {}
    default_artifact_slots = {
        str(selector["slot"]) for selector in consumes_defaults.get("artifacts") or []
    }
    default_criteria_slots = {
        str(selector["slot"]) for selector in consumes_defaults.get("criteria") or []
    }
    cleaned_consumes = {
        "artifacts": [
            dict(selector)
            for selector in local_consumes.get("artifacts") or []
            if str(selector["slot"]) not in default_artifact_slots
        ]
        or None,
        "criteria": [
            dict(selector)
            for selector in local_consumes.get("criteria") or []
            if str(selector["slot"]) not in default_criteria_slots
        ]
        or None,
    }
    child["consumes_json"] = (
        cleaned_consumes
        if cleaned_consumes["artifacts"] is not None or cleaned_consumes["criteria"] is not None
        else None
    )


def _merge_consume_selectors(
    default_selectors: list[dict[str, object]],
    local_selectors: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    index_by_slot: dict[str, int] = {}

    for selector in default_selectors:
        slot = str(selector["slot"])
        if slot in index_by_slot:
            continue
        index_by_slot[slot] = len(merged)
        merged.append(dict(selector))

    for selector in local_selectors:
        slot = str(selector["slot"])
        if slot in index_by_slot:
            merged[index_by_slot[slot]] = dict(selector)
            continue
        index_by_slot[slot] = len(merged)
        merged.append(dict(selector))

    return merged
