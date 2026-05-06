from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    model_validator,
)

from app.runtime.contracts import ParentRootToolName
from app.schemas.definitions.workflow import (
    ChildDefaults,
    ConsumeBuckets,
    CriteriaDeclaration,
    ProduceBuckets,
)
from app.schemas.runtime.checkpoint import TransientSurfaceWrite
from app.schemas.runtime.common import RuntimeSchemaText
from app.schemas.runtime.flow import RuntimeFlowRead
from app.schemas.runtime.refs import AssignmentFileRef, CheckpointFileRef, WorkflowManifestRef


class AssignmentIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: RuntimeSchemaText
    instruction: RuntimeSchemaText | None = None


class SupplementalSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: RuntimeSchemaText


class SupplementalDurableContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_slots: tuple[SupplementalSlot, ...] = ()
    criteria_slots: tuple[SupplementalSlot, ...] = ()


class AssignChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_key: RuntimeSchemaText
    assignment_intent: AssignmentIntent
    supplemental_durable_context: SupplementalDurableContext | None = None
    transient_surfaces: tuple[TransientSurfaceWrite, ...] = ()
    task_memory_search_hints: tuple[RuntimeSchemaText, ...] = ()


class ChildNodeDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: RuntimeSchemaText = Field(validation_alias=AliasChoices("node_key", "id"))
    parent_node_key: RuntimeSchemaText | None = Field(default=None, exclude=True)
    role: RuntimeSchemaText
    policy: RuntimeSchemaText | None = None
    description: RuntimeSchemaText
    consumes: ConsumeBuckets | None = None
    produces: ProduceBuckets | None = None
    criteria: list[CriteriaDeclaration] | None = None
    child_defaults: ChildDefaults | None = None
    children: list["ChildNodeDraft"] | None = None


class ChildNodePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RuntimeSchemaText | None = None
    policy: RuntimeSchemaText | None = None
    description: RuntimeSchemaText | None = None
    consumes: ConsumeBuckets | None = None
    produces: ProduceBuckets | None = None
    criteria: list[CriteriaDeclaration] | None = None
    child_defaults: ChildDefaults | None = None
    children: list[ChildNodeDraft] | None = None

    @model_validator(mode="after")
    def validate_children(self) -> "ChildNodePatch":
        if self.children is not None:
            raise ValueError("update_child does not support subtree patch shapes")
        return self


class AddChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child: ChildNodeDraft
    target_parent_node_key: RuntimeSchemaText | None = Field(
        default=None,
        validation_alias=AliasChoices("target_parent_node_key", "parent_node_key"),
    )

    @model_validator(mode="after")
    def bind_target_parent(self) -> "AddChildPayload":
        if self.target_parent_node_key is not None:
            self.child = self.child.model_copy(
                update={"parent_node_key": self.target_parent_node_key}
            )
        return self


class UpdateChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_key: RuntimeSchemaText
    patch: ChildNodePatch


class RemoveChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_key: RuntimeSchemaText


class ReleaseGreenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReleaseBlockedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


type ParentToolPayload = (
    AssignChildPayload
    | AddChildPayload
    | UpdateChildPayload
    | RemoveChildPayload
    | ReleaseGreenPayload
    | ReleaseBlockedPayload
)


class _ParentToolCallBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_structural_revision_id: RuntimeSchemaText | None = None


class AssignChildToolCall(_ParentToolCallBase):
    tool_name: Literal["assign_child"] = "assign_child"
    payload: AssignChildPayload


class AddChildToolCall(_ParentToolCallBase):
    tool_name: Literal["add_child"] = "add_child"
    payload: AddChildPayload


class UpdateChildToolCall(_ParentToolCallBase):
    tool_name: Literal["update_child"] = "update_child"
    payload: UpdateChildPayload


class RemoveChildToolCall(_ParentToolCallBase):
    tool_name: Literal["remove_child"] = "remove_child"
    payload: RemoveChildPayload


class ReleaseGreenToolCall(_ParentToolCallBase):
    tool_name: Literal["release_green"] = "release_green"
    payload: ReleaseGreenPayload


class ReleaseBlockedToolCall(_ParentToolCallBase):
    tool_name: Literal["release_blocked"] = "release_blocked"
    payload: ReleaseBlockedPayload


type ParentToolCallVariant = Annotated[
    AssignChildToolCall
    | AddChildToolCall
    | UpdateChildToolCall
    | RemoveChildToolCall
    | ReleaseGreenToolCall
    | ReleaseBlockedToolCall,
    Field(discriminator="tool_name"),
]

_PARENT_TOOL_CALL_ADAPTER: TypeAdapter[ParentToolCallVariant] = TypeAdapter(ParentToolCallVariant)


class ParentToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: ParentRootToolName
    payload: ParentToolPayload
    expected_structural_revision_id: RuntimeSchemaText | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_payload_by_tool(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        variant = _PARENT_TOOL_CALL_ADAPTER.validate_python(data)
        return {
            "tool_name": ParentRootToolName(variant.tool_name),
            "payload": variant.payload,
            "expected_structural_revision_id": variant.expected_structural_revision_id,
        }

    def as_variant(self) -> ParentToolCallVariant:
        return _PARENT_TOOL_CALL_ADAPTER.validate_python(
            {
                "tool_name": self.tool_name,
                "payload": self.payload,
                "expected_structural_revision_id": self.expected_structural_revision_id,
            }
        )


class AssignChildSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: Literal["assign_child"] = "assign_child"
    summary: RuntimeSchemaText | None = None
    target_node_key: RuntimeSchemaText
    target_assignment_key: RuntimeSchemaText
    target_attempt_id: RuntimeSchemaText
    child_assignment_ref: AssignmentFileRef | None = None
    flow: RuntimeFlowRead
    workflow_manifest_ref: WorkflowManifestRef | None = None
    latest_checkpoint_ref: CheckpointFileRef | None = None


class ParentToolMutationSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RuntimeSchemaText | None = None
    target_node_key: RuntimeSchemaText | None = None
    flow: RuntimeFlowRead
    workflow_manifest_ref: WorkflowManifestRef | None = None
    latest_checkpoint_ref: CheckpointFileRef | None = None


class AddChildSuccess(ParentToolMutationSuccess):
    tool_name: Literal["add_child"] = "add_child"


class UpdateChildSuccess(ParentToolMutationSuccess):
    tool_name: Literal["update_child"] = "update_child"


class RemoveChildSuccess(ParentToolMutationSuccess):
    tool_name: Literal["remove_child"] = "remove_child"


class ReleaseGreenSuccess(ParentToolMutationSuccess):
    tool_name: Literal["release_green"] = "release_green"


class ReleaseBlockedSuccess(ParentToolMutationSuccess):
    tool_name: Literal["release_blocked"] = "release_blocked"


type ParentToolSuccess = Annotated[
    AssignChildSuccess
    | AddChildSuccess
    | UpdateChildSuccess
    | RemoveChildSuccess
    | ReleaseGreenSuccess
    | ReleaseBlockedSuccess,
    Field(discriminator="tool_name"),
]


ChildNodeDraft.model_rebuild()

__all__ = [
    "AddChildPayload",
    "AddChildSuccess",
    "AddChildToolCall",
    "AssignChildPayload",
    "AssignChildSuccess",
    "AssignChildToolCall",
    "AssignmentIntent",
    "ChildNodeDraft",
    "ChildNodePatch",
    "ParentToolCall",
    "ParentToolCallVariant",
    "ParentToolMutationSuccess",
    "ParentToolPayload",
    "ParentToolSuccess",
    "ReleaseBlockedPayload",
    "ReleaseBlockedSuccess",
    "ReleaseBlockedToolCall",
    "ReleaseGreenPayload",
    "ReleaseGreenSuccess",
    "ReleaseGreenToolCall",
    "RemoveChildPayload",
    "RemoveChildSuccess",
    "RemoveChildToolCall",
    "SupplementalDurableContext",
    "SupplementalSlot",
    "UpdateChildPayload",
    "UpdateChildSuccess",
    "UpdateChildToolCall",
]
