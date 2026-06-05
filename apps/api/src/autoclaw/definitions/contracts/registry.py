from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from autoclaw.definitions.contracts.workflow import (
    NodeKind,
    NonEmptyText,
    WorkflowDefinitionInput,
    WorkflowIdentifier,
)


class DefinitionKind(StrEnum):
    ROLE = "role"
    POLICY = "policy"
    WORKFLOW = "workflow"


class DefinitionListSort(StrEnum):
    UPDATED_AT_DESC = "updated_at_desc"
    UPDATED_AT_ASC = "updated_at_asc"
    KEY_ASC = "key_asc"
    KEY_DESC = "key_desc"


class DefinitionHistorySort(StrEnum):
    REVISION_NO_DESC = "revision_no_desc"
    REVISION_NO_ASC = "revision_no_asc"
    UPDATED_AT_DESC = "updated_at_desc"
    UPDATED_AT_ASC = "updated_at_asc"


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

    child_assignment_limit: StrictInt | None = None
    retry_limit: StrictInt | None = None


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


type DefinitionContent = RoleDefinitionInput | PolicyDefinitionInput | WorkflowDefinitionInput


class DefinitionSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    key: NonEmptyText
    description: NonEmptyText | None = None
    current_revision_no: int = Field(ge=1)
    allowed_node_kinds: tuple[NodeKind, ...] | None = None
    applies_to: tuple[NodeKind, ...] | None = None
    budget_spec: BudgetSpec | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def validate_kind_specific_fields(self) -> Self:
        if self.allowed_node_kinds is not None and (
            self.applies_to is not None or self.budget_spec is not None
        ):
            raise ValueError("definition summaries must not mix role and policy fields")
        if self.budget_spec is not None and self.applies_to is None:
            raise ValueError("budget_spec requires applies_to")
        return self


class DefinitionListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    q: NonEmptyText | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: NonEmptyText | None = None
    sort: DefinitionListSort = DefinitionListSort.UPDATED_AT_DESC
    allowed_node_kind: NodeKind | None = None
    applies_to: NodeKind | None = None

    @model_validator(mode="after")
    def validate_route_specific_filters(self) -> Self:
        if self.allowed_node_kind is not None and self.applies_to is not None:
            raise ValueError("allowed_node_kind and applies_to cannot be combined")
        return self


class DefinitionSummaryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    kind: DefinitionKind
    items: tuple[DefinitionSummaryRead, ...]
    next_cursor: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_items_match_kind(self) -> Self:
        for item in self.items:
            if self.kind == DefinitionKind.ROLE:
                if item.allowed_node_kinds is None:
                    raise ValueError("role summaries require allowed_node_kinds")
                if item.applies_to is not None or item.budget_spec is not None:
                    raise ValueError("role summaries must not expose policy-only fields")
                continue
            if self.kind == DefinitionKind.POLICY:
                if item.applies_to is None:
                    raise ValueError("policy summaries require applies_to")
                if item.allowed_node_kinds is not None:
                    raise ValueError("policy summaries must not expose role-only fields")
                continue
            if (
                item.allowed_node_kinds is not None
                or item.applies_to is not None
                or item.budget_spec is not None
            ):
                raise ValueError("workflow summaries must not expose role or policy compatibility")
        return self


class DefinitionRevisionHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    revision_no: int = Field(ge=1)
    recorded_by: NonEmptyText | None = None
    updated_at: datetime


class DefinitionRevisionHistoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    limit: int = Field(default=50, ge=1, le=200)
    cursor: NonEmptyText | None = None
    sort: DefinitionHistorySort = DefinitionHistorySort.REVISION_NO_DESC


class DefinitionRevisionHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    key: NonEmptyText
    kind: DefinitionKind
    current_revision_no: int = Field(ge=1)
    items: tuple[DefinitionRevisionHistoryEntry, ...]
    next_cursor: NonEmptyText | None = None


class DefinitionUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: DefinitionKind
    content: DefinitionContent

    @model_validator(mode="after")
    def validate_kind_matches_content(self) -> Self:
        content_kind = _definition_kind_for_content(self.content)
        if self.kind != content_kind:
            raise ValueError(
                f"kind '{self.kind.value}' does not match content type '{content_kind.value}'"
            )
        return self


class DefinitionRevisionDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    key: NonEmptyText
    revision_no: int = Field(ge=1)
    content: DefinitionContent
    recorded_by: NonEmptyText | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def validate_key_matches_content(self) -> Self:
        if self.key != self.content.id:
            raise ValueError("definition detail key must match content.id")
        return self


def _definition_kind_for_content(content: DefinitionContent) -> DefinitionKind:
    if isinstance(content, RoleDefinitionInput):
        return DefinitionKind.ROLE
    if isinstance(content, PolicyDefinitionInput):
        return DefinitionKind.POLICY
    return DefinitionKind.WORKFLOW


__all__ = [
    "BudgetSpec",
    "DefinitionContent",
    "DefinitionHistorySort",
    "DefinitionKind",
    "DefinitionListQuery",
    "DefinitionListSort",
    "DefinitionRevisionDetailResponse",
    "DefinitionRevisionHistoryEntry",
    "DefinitionRevisionHistoryQuery",
    "DefinitionRevisionHistoryResponse",
    "DefinitionSummaryListResponse",
    "DefinitionSummaryRead",
    "DefinitionUploadRequest",
    "PolicyDefinitionFile",
    "PolicyDefinitionInput",
    "RoleDefinitionFile",
    "RoleDefinitionInput",
]
