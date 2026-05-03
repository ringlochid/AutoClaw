from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    model_validator,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
WorkflowIdentifier = NonEmptyText
SlotIdentifier = NonEmptyText


class NodeKind(StrEnum):
    ROOT = "root"
    PARENT = "parent"
    WORKER = "worker"


class ConsumeSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: SlotIdentifier
    required: bool = True


class ConsumeBuckets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifacts: list[ConsumeSelector] | None = None
    criteria: list[ConsumeSelector] | None = None


class ProduceSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: SlotIdentifier
    description: NonEmptyText
    file_hint: NonEmptyText | None = None


class ProduceBuckets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifacts: list[ProduceSlot] | None = None


class CriteriaDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: SlotIdentifier
    description: NonEmptyText
    criteria: list[NonEmptyText] = Field(min_length=1)


class ChildDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consumes: ConsumeBuckets | None = None
    criteria: list[SlotIdentifier] | None = None


class NodeDefinitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: WorkflowIdentifier
    role: WorkflowIdentifier
    policy: WorkflowIdentifier | None = None
    description: NonEmptyText
    consumes: ConsumeBuckets | None = None
    produces: ProduceBuckets | None = None
    criteria: list[CriteriaDeclaration] | None = None
    child_defaults: ChildDefaults | None = None
    children: list[NodeDefinitionInput] | None = None


class RootNodeDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["root"]
    role: WorkflowIdentifier
    policy: WorkflowIdentifier | None = None
    description: NonEmptyText
    produces: ProduceBuckets | None = None
    criteria: list[CriteriaDeclaration] | None = None
    child_defaults: ChildDefaults | None = None
    children: list[NodeDefinitionInput] | None = None


type WorkflowNode = RootNodeDefinition | NodeDefinitionInput


class WorkflowDefinitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: WorkflowIdentifier
    description: NonEmptyText
    root: RootNodeDefinition

    @model_validator(mode="after")
    def validate_workflow(self, info: ValidationInfo) -> Self:
        from app.schemas.workflow_validation import validate_workflow_definition

        return validate_workflow_definition(self, info)


class WorkflowDefinitionFile(WorkflowDefinitionInput):
    kind: Literal["workflow"]


NodeDefinitionInput.model_rebuild()
