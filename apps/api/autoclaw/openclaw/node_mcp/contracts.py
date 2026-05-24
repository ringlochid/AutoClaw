from __future__ import annotations

import json
from copy import deepcopy
from typing import Annotated, Any, Literal

from app.runtime.contracts import EgressBoundary
from app.schemas.runtime import (
    BoundaryRead,
    CheckpointRead,
    CheckpointWriteBody,
    ParentToolSuccess,
)
from app.schemas.runtime.parent_tools import (
    AddChildPayload,
    AssignChildPayload,
    ReleaseBlockedPayload,
    ReleaseGreenPayload,
    RemoveChildPayload,
    UpdateChildPayload,
)
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from autoclaw.openclaw.tool_teaching import (
    CALL_PARENT_TOOL_LEGALITY_NOTE,
    LIVE_STRUCTURAL_EDIT_LANE_NOTE,
    NODE_AUTHORITY_NOTE,
    NOT_BROAD_BROWSING_NOTE,
    RECORD_BEFORE_TERMINAL_BOUNDARY_NOTE,
    RETURN_BOUNDARY_TERMINALITY_NOTE,
    STOP_AFTER_BOUNDARY_NOTE,
    mutating_tool_teaching,
    read_only_tool_teaching,
)

NODE_TOOL_NAMES: tuple[str, ...] = (
    "search_definitions",
    "get_definition",
    "record_checkpoint",
    "return_boundary",
    "call_parent_tool",
)

SEARCH_DEFINITIONS_TEACHING = read_only_tool_teaching(
    name="search_definitions",
    summary="Search current-only role or policy definitions for the live structural-edit lane.",
    details=(LIVE_STRUCTURAL_EDIT_LANE_NOTE, NOT_BROAD_BROWSING_NOTE, NODE_AUTHORITY_NOTE),
)
GET_DEFINITION_TEACHING = read_only_tool_teaching(
    name="get_definition",
    summary="Inspect one current-only role or policy definition for the live structural-edit lane.",
    details=(LIVE_STRUCTURAL_EDIT_LANE_NOTE, NOT_BROAD_BROWSING_NOTE, NODE_AUTHORITY_NOTE),
)
RECORD_CHECKPOINT_TEACHING = mutating_tool_teaching(
    name="record_checkpoint",
    summary="Persist durable semantic progress for the current live node execution.",
    details=(RECORD_BEFORE_TERMINAL_BOUNDARY_NOTE, NODE_AUTHORITY_NOTE),
)
RETURN_BOUNDARY_TEACHING = mutating_tool_teaching(
    name="return_boundary",
    summary="Close the current dispatch turn with yield, green, retry, or blocked.",
    details=(
        RETURN_BOUNDARY_TERMINALITY_NOTE,
        STOP_AFTER_BOUNDARY_NOTE,
        "This is not a polling action.",
        NODE_AUTHORITY_NOTE,
    ),
)
CALL_PARENT_TOOL_TEACHING = mutating_tool_teaching(
    name="call_parent_tool",
    summary=(
        "Perform a dispatch-local parent or root control tool call such "
        "as assign_child or a structural edit."
    ),
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "This is not an operator-control surface or generic worker browsing tool.",
    ),
)


class NodeToolArgumentsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_key: str
    task_id: str


class NodeParentToolArgumentsBase(NodeToolArgumentsBase):
    expected_structural_revision_id: str | None = None


class NodeCheckpointArguments(NodeToolArgumentsBase):
    checkpoint: CheckpointWriteBody


class NodeBoundaryArguments(NodeToolArgumentsBase):
    boundary: EgressBoundary


class NodeAssignChildArguments(NodeParentToolArgumentsBase):
    tool_name: Literal["assign_child"] = "assign_child"
    payload: AssignChildPayload


class NodeAddChildArguments(NodeParentToolArgumentsBase):
    tool_name: Literal["add_child"] = "add_child"
    payload: AddChildPayload


class NodeUpdateChildArguments(NodeParentToolArgumentsBase):
    tool_name: Literal["update_child"] = "update_child"
    payload: UpdateChildPayload


class NodeRemoveChildArguments(NodeParentToolArgumentsBase):
    tool_name: Literal["remove_child"] = "remove_child"
    payload: RemoveChildPayload


class NodeReleaseGreenArguments(NodeParentToolArgumentsBase):
    tool_name: Literal["release_green"] = "release_green"
    payload: ReleaseGreenPayload


class NodeReleaseBlockedArguments(NodeParentToolArgumentsBase):
    tool_name: Literal["release_blocked"] = "release_blocked"
    payload: ReleaseBlockedPayload


type NodeParentToolArguments = Annotated[
    NodeAssignChildArguments
    | NodeAddChildArguments
    | NodeUpdateChildArguments
    | NodeRemoveChildArguments
    | NodeReleaseGreenArguments
    | NodeReleaseBlockedArguments,
    Field(discriminator="tool_name"),
]

NODE_PARENT_TOOL_NAMES: tuple[str, ...] = (
    "assign_child",
    "add_child",
    "update_child",
    "remove_child",
    "release_green",
    "release_blocked",
)


def _merge_discriminated_union_schema(
    schema: dict[str, Any],
    *,
    title: str,
    required_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    variants = schema.get("oneOf")
    if not isinstance(variants, list):
        return schema

    properties: dict[str, Any] = {}
    required_counts: dict[str, int] = {}
    variant_count = 0
    for variant_ref in variants:
        variant = _resolve_schema_ref(schema, variant_ref)
        variant_properties = variant.get("properties")
        if not isinstance(variant_properties, dict):
            continue
        variant_count += 1
        for key, value in variant_properties.items():
            properties[key] = _merge_property_schema(properties.get(key), value)
        for key in variant.get("required", ()):
            if isinstance(key, str):
                required_counts[key] = required_counts.get(key, 0) + 1

    required = [
        key
        for key, count in required_counts.items()
        if variant_count > 0 and count == variant_count
    ]
    required = list(dict.fromkeys([*required, *required_fields]))
    merged: dict[str, Any] = {
        "$defs": deepcopy(schema.get("$defs", {})),
        "additionalProperties": False,
        "properties": properties,
        "title": title,
        "type": "object",
    }
    if required:
        merged["required"] = required
    return merged


def _inline_local_schema_refs(schema: dict[str, Any]) -> dict[str, Any]:
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return schema

    def resolve(node: Any, seen: tuple[str, ...] = ()) -> Any:
        if isinstance(node, list):
            return [resolve(item, seen) for item in node]
        if not isinstance(node, dict):
            return node

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            key = ref.removeprefix("#/$defs/")
            if key in seen:
                return _recursive_ref_placeholder(defs.get(key), title=key)
            target = defs.get(key)
            if not isinstance(target, dict):
                return deepcopy(node)
            merged = deepcopy(target)
            for sibling_key, sibling_value in node.items():
                if sibling_key != "$ref":
                    merged[sibling_key] = sibling_value
            return resolve(merged, (*seen, key))

        return {key: resolve(value, seen) for key, value in node.items() if key != "$defs"}

    resolved = resolve(schema)
    return resolved if isinstance(resolved, dict) else schema


def _recursive_ref_placeholder(target: Any, *, title: str) -> dict[str, Any]:
    placeholder: dict[str, Any] = {"title": title}
    if isinstance(target, dict) and isinstance(target.get("type"), str):
        placeholder["type"] = target["type"]
    else:
        placeholder["type"] = "object"
    if placeholder["type"] == "object":
        placeholder["additionalProperties"] = True
    return placeholder


def _resolve_schema_ref(
    schema: dict[str, Any],
    variant_ref: Any,
) -> dict[str, Any]:
    if not isinstance(variant_ref, dict):
        return {}
    ref = variant_ref.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        return variant_ref
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return {}
    resolved = defs.get(ref.removeprefix("#/$defs/"))
    return resolved if isinstance(resolved, dict) else {}


def _merge_property_schema(existing: Any, incoming: Any) -> Any:
    if existing is None:
        return deepcopy(incoming)
    if existing == incoming:
        return existing

    enum_values = _extract_enum_values(existing) + _extract_enum_values(incoming)
    if enum_values:
        merged_enum = list(dict.fromkeys(enum_values))
        return {
            "enum": merged_enum,
            "title": _first_string_value(existing, incoming, key="title"),
            "type": _single_json_type(merged_enum),
        }

    any_of = _flatten_any_of(existing) + _flatten_any_of(incoming)
    unique: dict[str, Any] = {}
    for item in any_of:
        unique.setdefault(json.dumps(item, sort_keys=True), item)
    return {"anyOf": list(unique.values())}


def _extract_enum_values(schema: Any) -> list[Any]:
    if not isinstance(schema, dict):
        return []
    if "const" in schema:
        return [schema["const"]]
    enum = schema.get("enum")
    return enum if isinstance(enum, list) else []


def _first_string_value(*schemas: Any, key: str) -> str | None:
    for schema in schemas:
        if isinstance(schema, dict) and isinstance(schema.get(key), str):
            return str(schema[key])
    return None


def _single_json_type(values: list[Any]) -> str | None:
    types = {type(value) for value in values}
    if types == {str}:
        return "string"
    if types == {int}:
        return "integer"
    if types == {float}:
        return "number"
    if types == {bool}:
        return "boolean"
    return None


def _flatten_any_of(schema: Any) -> list[Any]:
    if isinstance(schema, dict) and isinstance(schema.get("anyOf"), list):
        return deepcopy(schema["anyOf"])
    return [deepcopy(schema)]


def _with_top_level_object_type(schema: dict[str, Any]) -> dict[str, Any]:
    typed_schema = deepcopy(schema)
    typed_schema["type"] = "object"
    return typed_schema


NODE_CHECKPOINT_INPUT_SCHEMA = _inline_local_schema_refs(
    TypeAdapter(NodeCheckpointArguments).json_schema()
)
NODE_BOUNDARY_INPUT_SCHEMA = _inline_local_schema_refs(
    TypeAdapter(NodeBoundaryArguments).json_schema()
)
NODE_PARENT_TOOL_INPUT_SCHEMA = _with_top_level_object_type(
    TypeAdapter(NodeParentToolArguments).json_schema()
)
CHECKPOINT_OUTPUT_SCHEMA = CheckpointRead.model_json_schema()
BOUNDARY_OUTPUT_SCHEMA = BoundaryRead.model_json_schema()
PARENT_TOOL_OUTPUT_SCHEMA = _with_top_level_object_type(
    TypeAdapter(ParentToolSuccess).json_schema()
)

__all__ = [
    "BOUNDARY_OUTPUT_SCHEMA",
    "CALL_PARENT_TOOL_TEACHING",
    "CHECKPOINT_OUTPUT_SCHEMA",
    "GET_DEFINITION_TEACHING",
    "NODE_BOUNDARY_INPUT_SCHEMA",
    "NODE_CHECKPOINT_INPUT_SCHEMA",
    "NODE_PARENT_TOOL_INPUT_SCHEMA",
    "NODE_PARENT_TOOL_NAMES",
    "NODE_TOOL_NAMES",
    "PARENT_TOOL_OUTPUT_SCHEMA",
    "RECORD_CHECKPOINT_TEACHING",
    "RETURN_BOUNDARY_TEACHING",
    "SEARCH_DEFINITIONS_TEACHING",
]
