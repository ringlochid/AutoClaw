from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autoclaw.definitions.contracts import DefinitionKind
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode


class DefinitionDraftSetState(StrEnum):
    OPEN = "open"
    APPLIED = "applied"
    STALE = "stale"


class DefinitionDraftFileStatus(StrEnum):
    CLEAN = "clean"
    MODIFIED = "modified"
    ADDED = "added"
    STALE = "stale"
    INVALID = "invalid"


class DefinitionDraftSetListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


class DefinitionDraftBaselineRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    revision_no: int | None = Field(default=None, ge=1)
    content_hash: str | None = None
    source_path: str | None = None


class DefinitionDraftFileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    kind: DefinitionKind
    key: str
    draft_path: str
    normalized_path: str
    body_format: Literal["yaml"] = "yaml"
    content_hash: str
    based_on: DefinitionDraftBaselineRead
    status: DefinitionDraftFileStatus


class DefinitionDraftFileDetail(DefinitionDraftFileSummary):
    body: str
    normalized_content: dict[str, Any] | None = None
    baseline_body: str | None = None
    baseline_normalized_content: dict[str, Any] | None = None


class DefinitionDraftSetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    draft_set_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    state: DefinitionDraftSetState
    files: tuple[DefinitionDraftFileSummary, ...]
    preview_task_compose_path: str | None = None


class DefinitionDraftSetDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    draft_set_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    state: DefinitionDraftSetState
    files: tuple[DefinitionDraftFileDetail, ...]
    preview_task_compose_path: str | None = None
    preview_task_compose_body: str | None = None


class DefinitionDraftSetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    items: tuple[DefinitionDraftSetSummary, ...]
    next_cursor: str | None = None


class DefinitionDraftSetCreateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: DefinitionKind
    key: str


class DefinitionDraftSetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str | None = None
    materialize: tuple[DefinitionDraftSetCreateItem, ...] = ()
    preview_task_compose: str | None = None


class DefinitionDraftMaterializeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    definitions: tuple[DefinitionDraftSetCreateItem, ...]


class DefinitionDraftFileWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    body: str
    body_format: Literal["yaml"] = "yaml"


class DefinitionDraftFileResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    discard_local_changes: Literal[True]


class DefinitionDraftFileRematerializeCurrentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    discard_local_changes: Literal[True]


class DefinitionDraftSetDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    draft_set: DefinitionDraftSetDetail


class DefinitionDraftValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    code: str
    message: str
    path: str | None = None
    kind: Literal["schema", "cross_reference", "stale", "preview"]


class DefinitionDraftValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    draft_set_id: str
    status: Literal["valid", "invalid", "stale"]
    errors: tuple[DefinitionDraftValidationIssue, ...]
    warnings: tuple[DefinitionDraftValidationIssue, ...]


class DefinitionDraftPublishedRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    kind: DefinitionKind
    key: str
    revision_no: int = Field(ge=1)
    content_hash: str


class DefinitionDraftApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    should_start_task_after_apply: bool = False


class DefinitionDraftTaskStartStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    STARTED = "started"
    FAILED = "failed"


class DefinitionDraftTaskStartFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: OperationFailureCode
    summary: str
    is_retryable: bool
    suggested_next_step: str | None = None


class DefinitionDraftApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    draft_set_id: str
    status: Literal["applied", "stale", "invalid"]
    published_revisions: tuple[DefinitionDraftPublishedRevision, ...]
    started_task_id: str | None = None
    task_start_status: DefinitionDraftTaskStartStatus = DefinitionDraftTaskStartStatus.NOT_REQUESTED
    task_start_failure: DefinitionDraftTaskStartFailure | None = None
    validation: DefinitionDraftValidationResponse

    @model_validator(mode="after")
    def validate_task_start_outcome(self) -> DefinitionDraftApplyResponse:
        if self.task_start_status == DefinitionDraftTaskStartStatus.STARTED:
            if self.started_task_id is None:
                raise ValueError("started task start outcome requires started_task_id")
            if self.task_start_failure is not None:
                raise ValueError("started task start outcome must not set task_start_failure")
            return self

        if self.task_start_status == DefinitionDraftTaskStartStatus.FAILED:
            if self.started_task_id is not None:
                raise ValueError("failed task start outcome must not set started_task_id")
            if self.task_start_failure is None:
                raise ValueError("failed task start outcome requires task_start_failure")
            return self

        if self.started_task_id is not None:
            raise ValueError("not_requested task start outcome must not set started_task_id")
        if self.task_start_failure is not None:
            raise ValueError("not_requested task start outcome must not set task_start_failure")
        return self


class DefinitionDraftTaskComposePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    body: str
    body_format: Literal["yaml"] = "yaml"


class DefinitionDraftTaskComposePreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    status: Literal["valid", "invalid"]
    validation: DefinitionDraftValidationResponse


__all__ = [
    "DefinitionDraftApplyRequest",
    "DefinitionDraftApplyResponse",
    "DefinitionDraftBaselineRead",
    "DefinitionDraftFileDetail",
    "DefinitionDraftFileRematerializeCurrentRequest",
    "DefinitionDraftFileResetRequest",
    "DefinitionDraftFileStatus",
    "DefinitionDraftFileSummary",
    "DefinitionDraftFileWriteRequest",
    "DefinitionDraftMaterializeRequest",
    "DefinitionDraftPublishedRevision",
    "DefinitionDraftSetCreateItem",
    "DefinitionDraftSetCreateRequest",
    "DefinitionDraftSetDetail",
    "DefinitionDraftSetDetailResponse",
    "DefinitionDraftSetListQuery",
    "DefinitionDraftSetListResponse",
    "DefinitionDraftSetState",
    "DefinitionDraftSetSummary",
    "DefinitionDraftTaskComposePreviewRequest",
    "DefinitionDraftTaskComposePreviewResponse",
    "DefinitionDraftTaskStartFailure",
    "DefinitionDraftTaskStartStatus",
    "DefinitionDraftValidationIssue",
    "DefinitionDraftValidationResponse",
]
