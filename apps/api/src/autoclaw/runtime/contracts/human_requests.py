from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import (
    HumanRequestKind,
    HumanRequestResolutionKind,
    HumanRequestStatus,
    TaskIdentifier,
)


class HumanRequestOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    id: RuntimeSchemaText
    title: RuntimeSchemaText
    description: RuntimeSchemaText | None = None


class HumanRequestItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    item_id: RuntimeSchemaText
    prompt: RuntimeSchemaText
    options: tuple[HumanRequestOption, ...] = ()
    recommended_option: RuntimeSchemaText | None = None
    input_payload_schema: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_recommended_option(self) -> HumanRequestItem:
        if self.recommended_option is None:
            return self
        option_ids = {option.id for option in self.options}
        if self.recommended_option not in option_ids:
            raise ValueError("recommended_option must match an item option id")
        return self


class HumanRequestTimeout(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    due_at: datetime | None = None
    default_behavior: RuntimeSchemaText | None = None


class HumanRequestOpenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: HumanRequestKind
    title: RuntimeSchemaText
    summary: RuntimeSchemaText
    items: tuple[HumanRequestItem, ...] = Field(min_length=1)
    timeout: HumanRequestTimeout = Field(default_factory=HumanRequestTimeout)
    suggested_human_instruction: RuntimeSchemaText

    @model_validator(mode="after")
    def validate_items_match_kind(self) -> HumanRequestOpenRequest:
        _validate_items_match_kind(kind=self.kind, items=self.items)
        return self


class HumanRequestOpenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    request_id: RuntimeSchemaText
    task_id: TaskIdentifier
    status: HumanRequestStatus = HumanRequestStatus.OPEN

    @model_validator(mode="after")
    def validate_open_status(self) -> HumanRequestOpenResponse:
        if self.status != HumanRequestStatus.OPEN:
            raise ValueError("human_request_open_response status must be open")
        return self


class PendingHumanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    request_id: RuntimeSchemaText
    task_id: TaskIdentifier
    title: RuntimeSchemaText
    summary: RuntimeSchemaText
    kind: HumanRequestKind
    requester_node: RuntimeSchemaText
    items: tuple[HumanRequestItem, ...] = Field(min_length=1)
    timeout: HumanRequestTimeout = Field(default_factory=HumanRequestTimeout)
    suggested_human_instruction: RuntimeSchemaText
    opened_at: datetime
    status: HumanRequestStatus

    @model_validator(mode="after")
    def validate_items_match_kind(self) -> PendingHumanRequest:
        _validate_items_match_kind(kind=self.kind, items=self.items)
        return self


class HumanRequestItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    item_id: RuntimeSchemaText
    selected_option: RuntimeSchemaText | None = None
    freeform_answer: RuntimeSchemaText | None = None
    extra_notes: RuntimeSchemaText | None = None
    response_payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_answer_shape(self) -> HumanRequestItemResponse:
        if self.selected_option is not None and self.freeform_answer is not None:
            raise ValueError("item response must not set both selected_option and freeform_answer")
        return self


class HumanRequestResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    request_id: RuntimeSchemaText
    task_id: TaskIdentifier
    resolution_kind: HumanRequestResolutionKind
    item_responses: tuple[HumanRequestItemResponse, ...] = ()
    resolved_at: datetime
    resolved_by_actor_ref: RuntimeSchemaText | None = None

    @model_validator(mode="after")
    def validate_resolution_shape(self) -> HumanRequestResolution:
        if self.resolution_kind == HumanRequestResolutionKind.ANSWERED:
            if not self.item_responses:
                raise ValueError("answered human request resolutions require item_responses")
            return self
        if self.item_responses:
            raise ValueError("terminal non-answer resolutions must not include item_responses")
        return self


class HumanRequestResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_responses: tuple[HumanRequestItemResponse, ...] = Field(min_length=1)


class HumanRequestResolveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: TaskIdentifier
    resolution: HumanRequestResolution


class HumanRequestRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    request: PendingHumanRequest
    resolution: HumanRequestResolution | None = None

    @model_validator(mode="after")
    def validate_resolution_status(self) -> HumanRequestRead:
        if self.request.status == HumanRequestStatus.OPEN and self.resolution is not None:
            raise ValueError("open human requests must not expose a resolution")
        if self.request.status != HumanRequestStatus.OPEN and self.resolution is None:
            raise ValueError("terminal human requests require a resolution")
        return self


class HumanRequestListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: TaskIdentifier
    items: tuple[HumanRequestRead, ...]


def _validate_items_match_kind(
    *,
    kind: HumanRequestKind,
    items: tuple[HumanRequestItem, ...],
) -> None:
    if kind == HumanRequestKind.INPUT:
        for item in items:
            if item.input_payload_schema is None:
                raise ValueError("input human request items require input_payload_schema")
        return

    for item in items:
        if not item.options:
            raise ValueError(f"{kind.value} human request items require options")
        if item.input_payload_schema is not None:
            raise ValueError(f"{kind.value} human request items must not set input_payload_schema")


__all__ = [
    "HumanRequestItem",
    "HumanRequestItemResponse",
    "HumanRequestListResponse",
    "HumanRequestOpenRequest",
    "HumanRequestOpenResponse",
    "HumanRequestOption",
    "HumanRequestRead",
    "HumanRequestResolution",
    "HumanRequestResolveRequest",
    "HumanRequestResolveResponse",
    "HumanRequestTimeout",
    "PendingHumanRequest",
]
