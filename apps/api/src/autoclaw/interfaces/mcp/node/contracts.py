from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter

from autoclaw.runtime import EgressBoundary
from autoclaw.runtime.contracts import (
    AddChildPayload,
    AddChildSuccess,
    AssignChildPayload,
    AssignChildSuccess,
    BoundaryRead,
    CheckpointRead,
    CheckpointWriteBody,
    HumanRequestOpenRequest,
    HumanRequestOpenResponse,
    ReleaseBlockedSuccess,
    ReleaseGreenSuccess,
    RemoveChildPayload,
    RemoveChildSuccess,
    UpdateChildPayload,
    UpdateChildSuccess,
)

from ..mcp_operation_failures import success_or_failure_output_schema
from ..tool_teaching import (
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
    "open_human_request",
    "assign_child",
    "add_child",
    "update_child",
    "remove_child",
    "release_green",
    "release_blocked",
)

NODE_STRUCTURAL_MUTATION_TOOL_NAMES: tuple[str, ...] = (
    "assign_child",
    "add_child",
    "update_child",
    "remove_child",
    "release_green",
    "release_blocked",
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
OPEN_HUMAN_REQUEST_TEACHING = mutating_tool_teaching(
    name="open_human_request",
    summary="Open a typed pending human request for the current node execution.",
    details=(
        "This creates the controller-owned waiting_for_human_request state directly; "
        "it is not a workflow boundary and does not use task continue semantics.",
        "Denied or stale attempts fail before pending request, waiting-state, or task-event "
        "side effects are created.",
        NODE_AUTHORITY_NOTE,
    ),
)
ASSIGN_CHILD_TEACHING = mutating_tool_teaching(
    name="assign_child",
    summary="Stage exactly one bounded child assignment for the current open parent/root dispatch.",
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "This is not an operator-control surface or generic worker browsing tool.",
    ),
)
ADD_CHILD_TEACHING = mutating_tool_teaching(
    name="add_child",
    summary="Add one structural child node draft to the current flow revision.",
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "Reread the regenerated manifest before deciding whether to stage a child assignment.",
    ),
)
UPDATE_CHILD_TEACHING = mutating_tool_teaching(
    name="update_child",
    summary="Update one current-flow child node definition in place.",
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "Reread the regenerated manifest before deciding whether to stage a child assignment.",
    ),
)
REMOVE_CHILD_TEACHING = mutating_tool_teaching(
    name="remove_child",
    summary="Remove one child node from the current flow revision.",
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "Reread the regenerated manifest before deciding whether to stage a child assignment.",
    ),
)
RELEASE_GREEN_TEACHING = mutating_tool_teaching(
    name="release_green",
    summary=(
        "Mark the current parent/root assignment green-release-ready "
        "once current evidence is sufficient."
    ),
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "Use this only after current evidence and required publications "
        "are present for terminal green closure.",
    ),
)
RELEASE_BLOCKED_TEACHING = mutating_tool_teaching(
    name="release_blocked",
    summary=(
        "Mark the current root assignment blocked-release-ready once "
        "whole-flow blocked evidence is sufficient."
    ),
    details=(
        CALL_PARENT_TOOL_LEGALITY_NOTE,
        NODE_AUTHORITY_NOTE,
        "Root-only. Use this only after current blocked evidence is present "
        "for whole-flow blocked closure.",
    ),
)


class NodeToolArgumentsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_key: str
    task_id: str


class NodeStructuralMutationArgumentsBase(NodeToolArgumentsBase):
    expected_structural_revision_id: str | None = None


class NodeCheckpointArguments(NodeToolArgumentsBase):
    checkpoint: CheckpointWriteBody


class NodeBoundaryArguments(NodeToolArgumentsBase):
    boundary: EgressBoundary


class NodeHumanRequestOpenArguments(NodeToolArgumentsBase):
    request: HumanRequestOpenRequest


class NodeAssignChildArguments(NodeStructuralMutationArgumentsBase):
    payload: AssignChildPayload


class NodeAddChildArguments(NodeStructuralMutationArgumentsBase):
    payload: AddChildPayload


class NodeUpdateChildArguments(NodeStructuralMutationArgumentsBase):
    payload: UpdateChildPayload


class NodeRemoveChildArguments(NodeStructuralMutationArgumentsBase):
    payload: RemoveChildPayload


class NodeReleaseGreenArguments(NodeStructuralMutationArgumentsBase):
    pass


class NodeReleaseBlockedArguments(NodeStructuralMutationArgumentsBase):
    pass


class _SchemaRefResolver:
    @staticmethod
    def inline_local_refs(schema: dict[str, Any]) -> dict[str, Any]:
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
                    return _SchemaRefResolver.recursive_ref_placeholder(defs.get(key), title=key)
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

    @staticmethod
    def recursive_ref_placeholder(target: Any, *, title: str) -> dict[str, Any]:
        placeholder: dict[str, Any] = {"title": title}
        if isinstance(target, dict) and isinstance(target.get("type"), str):
            placeholder["type"] = target["type"]
        else:
            placeholder["type"] = "object"
        if placeholder["type"] == "object":
            placeholder["additionalProperties"] = True
        return placeholder


NODE_CHECKPOINT_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeCheckpointArguments).json_schema()
)
NODE_BOUNDARY_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeBoundaryArguments).json_schema()
)
HUMAN_REQUEST_OPEN_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeHumanRequestOpenArguments).json_schema()
)
ASSIGN_CHILD_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeAssignChildArguments).json_schema()
)
ADD_CHILD_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeAddChildArguments).json_schema()
)
UPDATE_CHILD_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeUpdateChildArguments).json_schema()
)
REMOVE_CHILD_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeRemoveChildArguments).json_schema()
)
RELEASE_GREEN_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeReleaseGreenArguments).json_schema()
)
RELEASE_BLOCKED_INPUT_SCHEMA = _SchemaRefResolver.inline_local_refs(
    TypeAdapter(NodeReleaseBlockedArguments).json_schema()
)

CHECKPOINT_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(CheckpointRead.model_json_schema())
)
BOUNDARY_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(BoundaryRead.model_json_schema())
)
HUMAN_REQUEST_OPEN_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(HumanRequestOpenResponse.model_json_schema())
)
ASSIGN_CHILD_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(AssignChildSuccess.model_json_schema())
)
ADD_CHILD_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(AddChildSuccess.model_json_schema())
)
UPDATE_CHILD_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(UpdateChildSuccess.model_json_schema())
)
REMOVE_CHILD_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(RemoveChildSuccess.model_json_schema())
)
RELEASE_GREEN_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(ReleaseGreenSuccess.model_json_schema())
)
RELEASE_BLOCKED_OUTPUT_SCHEMA = success_or_failure_output_schema(
    _SchemaRefResolver.inline_local_refs(ReleaseBlockedSuccess.model_json_schema())
)

__all__ = [
    "ADD_CHILD_INPUT_SCHEMA",
    "ADD_CHILD_OUTPUT_SCHEMA",
    "ADD_CHILD_TEACHING",
    "ASSIGN_CHILD_INPUT_SCHEMA",
    "ASSIGN_CHILD_OUTPUT_SCHEMA",
    "ASSIGN_CHILD_TEACHING",
    "BOUNDARY_OUTPUT_SCHEMA",
    "CHECKPOINT_OUTPUT_SCHEMA",
    "GET_DEFINITION_TEACHING",
    "HUMAN_REQUEST_OPEN_INPUT_SCHEMA",
    "HUMAN_REQUEST_OPEN_OUTPUT_SCHEMA",
    "NODE_BOUNDARY_INPUT_SCHEMA",
    "NODE_CHECKPOINT_INPUT_SCHEMA",
    "NODE_STRUCTURAL_MUTATION_TOOL_NAMES",
    "NODE_TOOL_NAMES",
    "OPEN_HUMAN_REQUEST_TEACHING",
    "RECORD_CHECKPOINT_TEACHING",
    "RELEASE_BLOCKED_INPUT_SCHEMA",
    "RELEASE_BLOCKED_OUTPUT_SCHEMA",
    "RELEASE_BLOCKED_TEACHING",
    "RELEASE_GREEN_INPUT_SCHEMA",
    "RELEASE_GREEN_OUTPUT_SCHEMA",
    "RELEASE_GREEN_TEACHING",
    "REMOVE_CHILD_INPUT_SCHEMA",
    "REMOVE_CHILD_OUTPUT_SCHEMA",
    "REMOVE_CHILD_TEACHING",
    "RETURN_BOUNDARY_TEACHING",
    "SEARCH_DEFINITIONS_TEACHING",
    "UPDATE_CHILD_INPUT_SCHEMA",
    "UPDATE_CHILD_OUTPUT_SCHEMA",
    "UPDATE_CHILD_TEACHING",
]
