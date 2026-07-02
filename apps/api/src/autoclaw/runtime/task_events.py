from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, NamedTuple, cast

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from autoclaw.persistence.models import TaskEventModel, TaskModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    TaskEventListQuery,
    TaskEventListResponse,
    TaskEventRecord,
    TaskEventSource,
    TaskEventType,
)
from autoclaw.runtime.ids import task_event_id

_CURSOR_PREFIX = "task-event-cursor."
_HIDDEN_TASK_EVENT_TYPES = ("provider_event_normalized", "provider_resolution_recorded")


class _TaskEventAppendHead(NamedTuple):
    event_seq: int
    event_hash: str | None


class TaskEventCursorResetRequiredError(ValueError):
    code = "cursor_reset_required"

    def __init__(self, cursor: str) -> None:
        super().__init__(f"{self.code}: task event cursor cannot be resumed: {cursor}")
        self.cursor = cursor


async def append_task_event(
    session: AsyncSession,
    *,
    task_id: str,
    event_type: TaskEventType | str,
    event_source: TaskEventSource | str,
    event_id: str | None = None,
    occurred_at: datetime | None = None,
    flow_revision_id: str | None = None,
    dispatch_id: str | None = None,
    attempt_id: str | None = None,
    node_key: str | None = None,
    actor_ref: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> TaskEventRecord:
    await _lock_task_event_stream(session, task_id=task_id)
    append_head = await _latest_task_event_head(session, task_id=task_id)
    event_seq = append_head.event_seq + 1
    record = TaskEventRecord(
        event_id=event_id or task_event_id(task_id, event_seq),
        event_seq=event_seq,
        task_id=task_id,
        event_type=_task_event_type_value(event_type),
        event_source=_task_event_source_value(event_source),
        occurred_at=occurred_at or utc_now(),
        flow_revision_id=flow_revision_id,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        node_key=node_key,
        actor_ref=actor_ref,
        payload=dict(payload or {}),
        prev_event_hash=append_head.event_hash,
        event_hash="pending",
    )
    row = TaskEventModel(
        event_id=record.event_id,
        event_seq=record.event_seq,
        task_id=record.task_id,
        event_type=record.event_type.value,
        event_source=record.event_source.value,
        occurred_at=record.occurred_at,
        flow_revision_id=record.flow_revision_id,
        dispatch_id=record.dispatch_id,
        attempt_id=record.attempt_id,
        node_key=record.node_key,
        actor_ref=record.actor_ref,
        payload=record.payload,
        prev_event_hash=record.prev_event_hash,
        event_hash=compute_task_event_hash(record),
    )
    session.add(row)
    await session.flush((row,))
    return task_event_record_from_model(row)


async def list_task_events(
    session: AsyncSession,
    *,
    task_id: str,
    cursor: str | None = None,
    limit: int = 100,
    through_event_id: str | None = None,
) -> TaskEventListResponse:
    query = TaskEventListQuery(
        cursor=cursor,
        limit=limit,
        through_event_id=through_event_id,
    )
    start_after_seq = await _cursor_event_seq(session, task_id=task_id, cursor=query.cursor)
    through_event_seq = await _through_event_seq(
        session,
        task_id=task_id,
        through_event_id=query.through_event_id,
    )
    statement = _task_event_page_statement(
        task_id=task_id,
        start_after_seq=start_after_seq,
        through_event_seq=through_event_seq,
        limit=query.limit + 1,
    )
    rows = list(await session.scalars(statement))
    page_rows = rows[: query.limit]
    next_cursor = (
        encode_task_event_cursor(page_rows[-1].event_id) if len(rows) > query.limit else None
    )
    return TaskEventListResponse(
        task_id=task_id,
        items=tuple(task_event_record_from_model(row) for row in page_rows),
        next_cursor=next_cursor,
        through_event_id=query.through_event_id,
    )


async def read_task_event(
    session: AsyncSession,
    *,
    task_id: str,
    event_id: str,
) -> TaskEventRecord | None:
    row = await _task_event_by_id(session, task_id=task_id, event_id=event_id)
    if row is None:
        return None
    return task_event_record_from_model(row)


async def latest_task_event(
    session: AsyncSession,
    *,
    task_id: str,
) -> TaskEventRecord | None:
    row = await session.scalar(
        select(TaskEventModel)
        .where(TaskEventModel.task_id == task_id)
        .where(_visible_task_event_clause())
        .order_by(TaskEventModel.event_seq.desc())
        .limit(1)
    )
    if row is None:
        return None
    return task_event_record_from_model(row)


def task_event_record_from_model(row: TaskEventModel) -> TaskEventRecord:
    return TaskEventRecord.model_validate(row)


def compute_task_event_hash(event: TaskEventRecord) -> str:
    materialized = event.model_dump(mode="json")
    materialized.pop("event_hash", None)
    materialized["occurred_at"] = _task_event_hash_timestamp(event.occurred_at)
    encoded = json.dumps(materialized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def encode_task_event_cursor(event_id: str) -> str:
    payload = json.dumps(
        {"event_id": event_id, "version": 1}, sort_keys=True, separators=(",", ":")
    )
    token = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{_CURSOR_PREFIX}{token}"


def decode_task_event_cursor(cursor: str) -> str:
    if not cursor.startswith(_CURSOR_PREFIX):
        return cursor
    token = cursor.removeprefix(_CURSOR_PREFIX)
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise TaskEventCursorResetRequiredError(cursor) from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise TaskEventCursorResetRequiredError(cursor)
    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        raise TaskEventCursorResetRequiredError(cursor)
    return event_id


def clear_task_event_allocator_state() -> None:
    return None


async def _cursor_event_seq(
    session: AsyncSession,
    *,
    task_id: str,
    cursor: str | None,
) -> int:
    if cursor is None:
        return 0
    event_id = decode_task_event_cursor(cursor)
    row = await _task_event_by_id(
        session,
        task_id=task_id,
        event_id=event_id,
        include_hidden=True,
    )
    if row is None:
        raise TaskEventCursorResetRequiredError(cursor)
    return row.event_seq


async def _through_event_seq(
    session: AsyncSession,
    *,
    task_id: str,
    through_event_id: str | None,
) -> int | None:
    if through_event_id is None:
        return None
    row = await _task_event_by_id(
        session,
        task_id=task_id,
        event_id=through_event_id,
        include_hidden=True,
    )
    if row is None:
        raise TaskEventCursorResetRequiredError(through_event_id)
    return row.event_seq


def _task_event_page_statement(
    *,
    task_id: str,
    start_after_seq: int,
    through_event_seq: int | None,
    limit: int,
) -> Select[tuple[TaskEventModel]]:
    statement = (
        select(TaskEventModel)
        .where(TaskEventModel.task_id == task_id, TaskEventModel.event_seq > start_after_seq)
        .where(_visible_task_event_clause())
        .order_by(TaskEventModel.event_seq.asc())
        .limit(limit)
    )
    if through_event_seq is not None:
        statement = statement.where(TaskEventModel.event_seq <= through_event_seq)
    return statement


async def _task_event_by_id(
    session: AsyncSession,
    *,
    task_id: str,
    event_id: str,
    include_hidden: bool = False,
) -> TaskEventModel | None:
    statement = select(TaskEventModel).where(
        TaskEventModel.task_id == task_id,
        TaskEventModel.event_id == event_id,
    )
    if not include_hidden:
        statement = statement.where(_visible_task_event_clause())
    return cast(
        TaskEventModel | None,
        await session.scalar(statement),
    )


async def _latest_task_event_head(
    session: AsyncSession,
    *,
    task_id: str,
) -> _TaskEventAppendHead:
    row = await session.execute(
        select(TaskEventModel.event_seq, TaskEventModel.event_hash)
        .where(TaskEventModel.task_id == task_id)
        .order_by(TaskEventModel.event_seq.desc())
        .limit(1)
    )
    latest_row = row.first()
    if latest_row is None:
        return _TaskEventAppendHead(event_seq=0, event_hash=None)
    event_seq, event_hash = latest_row
    return _TaskEventAppendHead(event_seq=int(event_seq), event_hash=event_hash)


async def _lock_task_event_stream(session: AsyncSession, *, task_id: str) -> None:
    if _task_event_stream_row_lock_is_supported(session):
        await session.scalar(
            select(TaskModel.task_id).where(TaskModel.task_id == task_id).with_for_update()
        )
        return
    await session.execute(
        update(TaskModel)
        .where(TaskModel.task_id == task_id)
        .values(updated_at=TaskModel.updated_at)
    )


def _task_event_stream_row_lock_is_supported(session: AsyncSession) -> bool:
    return session.get_bind().dialect.name != "sqlite"


def _task_event_hash_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat()
    return value.astimezone(UTC).replace(tzinfo=None).isoformat()


def _task_event_source_value(event_source: TaskEventSource | str) -> TaskEventSource:
    return (
        event_source if isinstance(event_source, TaskEventSource) else TaskEventSource(event_source)
    )


def _task_event_type_value(event_type: TaskEventType | str) -> TaskEventType:
    return event_type if isinstance(event_type, TaskEventType) else TaskEventType(event_type)


def _visible_task_event_clause() -> ColumnElement[bool]:
    return ~TaskEventModel.event_type.in_(_HIDDEN_TASK_EVENT_TYPES)


__all__ = [
    "TaskEventCursorResetRequiredError",
    "append_task_event",
    "clear_task_event_allocator_state",
    "compute_task_event_hash",
    "decode_task_event_cursor",
    "encode_task_event_cursor",
    "latest_task_event",
    "list_task_events",
    "read_task_event",
    "task_event_record_from_model",
]
