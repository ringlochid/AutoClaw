from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.definitions.workflow import NodeKind, NonEmptyText, WorkflowIdentifier


class RoleDefinitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: WorkflowIdentifier
    description: NonEmptyText
    allowed_node_kinds: list[NodeKind] = Field(min_length=1)
    instruction: NonEmptyText | None = None

    @field_validator("allowed_node_kinds")
    @classmethod
    def validate_allowed_node_kinds(
        cls,
        allowed_node_kinds: list[NodeKind],
    ) -> list[NodeKind]:
        if len(set(allowed_node_kinds)) != len(allowed_node_kinds):
            raise ValueError("allowed_node_kinds must not contain duplicates")
        return allowed_node_kinds


class BudgetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_assignment_limit: int | None = None
    retry_limit: int | None = None


class PolicyDefinitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: WorkflowIdentifier
    description: NonEmptyText
    applies_to: list[NodeKind] = Field(min_length=1)
    budget_spec: BudgetSpec | None = None
    instruction: NonEmptyText | None = None

    @field_validator("applies_to")
    @classmethod
    def validate_applies_to(cls, applies_to: list[NodeKind]) -> list[NodeKind]:
        if len(set(applies_to)) != len(applies_to):
            raise ValueError("applies_to must not contain duplicates")
        return applies_to

    @model_validator(mode="after")
    def validate_budget_spec(self) -> Self:
        if self.budget_spec is None:
            return self

        has_child_limit = self.budget_spec.child_assignment_limit is not None
        has_retry_limit = self.budget_spec.retry_limit is not None

        if has_child_limit and not any(
            node_kind in {NodeKind.ROOT, NodeKind.PARENT} for node_kind in self.applies_to
        ):
            raise ValueError(
                "budget_spec.child_assignment_limit requires applies_to to include root or parent"
            )

        if has_retry_limit and NodeKind.WORKER not in self.applies_to:
            raise ValueError("budget_spec.retry_limit requires applies_to to include worker")

        if has_child_limit and has_retry_limit:
            raise ValueError("budget_spec must not mix child_assignment_limit with retry_limit")

        return self


class RoleDefinitionFile(RoleDefinitionInput):
    kind: Literal["role"]


class PolicyDefinitionFile(PolicyDefinitionInput):
    kind: Literal["policy"]


__all__ = [
    "BudgetSpec",
    "PolicyDefinitionFile",
    "PolicyDefinitionInput",
    "RoleDefinitionFile",
    "RoleDefinitionInput",
]
