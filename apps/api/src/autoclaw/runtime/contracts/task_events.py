from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import (
    TaskEventSource,
    TaskEventType,
    TaskIdentifier,
)


class TaskEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    event_id: RuntimeSchemaText
    event_seq: int = Field(ge=1)
    task_id: TaskIdentifier
    event_type: TaskEventType
    event_source: TaskEventSource
    occurred_at: datetime
    flow_revision_id: RuntimeSchemaText | None = None
    dispatch_id: RuntimeSchemaText | None = None
    attempt_id: RuntimeSchemaText | None = None
    node_key: RuntimeSchemaText | None = None
    actor_ref: RuntimeSchemaText | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    prev_event_hash: RuntimeSchemaText | None = None
    event_hash: RuntimeSchemaText


class TaskEventListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cursor: RuntimeSchemaText | None = None
    limit: int = Field(default=100, ge=1, le=500)
    through_event_id: RuntimeSchemaText | None = None


class TaskEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: TaskIdentifier
    items: tuple[TaskEventRecord, ...]
    next_cursor: RuntimeSchemaText | None = None
    through_event_id: RuntimeSchemaText | None = None


__all__ = [
    "TaskEventListQuery",
    "TaskEventListResponse",
    "TaskEventRecord",
]
