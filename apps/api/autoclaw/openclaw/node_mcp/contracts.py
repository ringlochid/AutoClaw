from __future__ import annotations

from typing import Annotated, Literal

from app.runtime.contracts import ParentRootToolName
from app.schemas.runtime import BoundaryRead, CheckpointRead, ParentToolSuccess
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

NODE_PARENT_TOOL_NAMES: tuple[ParentRootToolName, ...] = (
    "assign_child",
    "add_child",
    "update_child",
    "remove_child",
    "release_green",
    "release_blocked",
)

NODE_PARENT_TOOL_INPUT_SCHEMA = TypeAdapter(NodeParentToolArguments).json_schema()
CHECKPOINT_OUTPUT_SCHEMA = CheckpointRead.model_json_schema()
BOUNDARY_OUTPUT_SCHEMA = BoundaryRead.model_json_schema()
PARENT_TOOL_OUTPUT_SCHEMA = TypeAdapter(ParentToolSuccess).json_schema()

__all__ = [
    "BOUNDARY_OUTPUT_SCHEMA",
    "CALL_PARENT_TOOL_TEACHING",
    "CHECKPOINT_OUTPUT_SCHEMA",
    "GET_DEFINITION_TEACHING",
    "NODE_PARENT_TOOL_INPUT_SCHEMA",
    "NODE_PARENT_TOOL_NAMES",
    "NODE_TOOL_NAMES",
    "PARENT_TOOL_OUTPUT_SCHEMA",
    "RECORD_CHECKPOINT_TEACHING",
    "RETURN_BOUNDARY_TEACHING",
    "SEARCH_DEFINITIONS_TEACHING",
]
