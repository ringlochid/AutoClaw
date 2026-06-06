from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel, ProviderEventRecordModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.ids import provider_event_record_id

_LOCKS_BY_LOOP: dict[int, dict[str, asyncio.Lock]] = {}
_ALLOCATED_EVENT_NOS_BY_LOOP: dict[int, dict[str, int]] = {}


async def append_provider_event(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    attempt_id: str,
    event_source: str,
    event_kind: str,
    summary: str,
    detail: str | None = None,
    provider_event_name: str | None = None,
    provider_occurred_at: datetime | None = None,
    event_payload_json: dict[str, object] | None = None,
) -> ProviderEventRecordModel:
    next_event_no = await _allocate_provider_event_no(
        session,
        dispatch_id=dispatch.dispatch_id,
    )
    row = ProviderEventRecordModel(
        provider_event_record_id=provider_event_record_id(
            dispatch.dispatch_id,
            next_event_no,
        ),
        dispatch_id=dispatch.dispatch_id,
        task_id=dispatch.task_id,
        attempt_id=attempt_id,
        event_no=next_event_no,
        event_source=event_source,
        event_kind=event_kind,
        provider_event_name=provider_event_name,
        summary=summary,
        detail=detail,
        event_payload_json=event_payload_json,
        occurred_at=utc_now(),
        provider_occurred_at=provider_occurred_at,
    )
    session.add(row)
    await session.flush((row,))
    return row


def clear_provider_event_allocator_state() -> None:
    _ALLOCATED_EVENT_NOS_BY_LOOP.clear()
    _LOCKS_BY_LOOP.clear()


async def _allocate_provider_event_no(
    session: AsyncSession,
    *,
    dispatch_id: str,
) -> int:
    # Reserve event numbers in-process so concurrent sessions do not depend on
    # another session committing before the next append can pick a unique value.
    async with _provider_event_lock(dispatch_id):
        loop_id = id(asyncio.get_running_loop())
        allocated_event_nos = _ALLOCATED_EVENT_NOS_BY_LOOP.setdefault(loop_id, {})
        committed_event_no = int(
            await session.scalar(
                select(func.max(ProviderEventRecordModel.event_no)).where(
                    ProviderEventRecordModel.dispatch_id == dispatch_id
                )
            )
            or 0
        )
        last_allocated_event_no = allocated_event_nos.get(dispatch_id, 0)
        next_event_no = max(committed_event_no, last_allocated_event_no) + 1
        allocated_event_nos[dispatch_id] = next_event_no
        return next_event_no


def _provider_event_lock(dispatch_id: str) -> asyncio.Lock:
    loop_id = id(asyncio.get_running_loop())
    locks = _LOCKS_BY_LOOP.setdefault(loop_id, {})
    lock = locks.get(dispatch_id)
    if lock is None:
        lock = asyncio.Lock()
        locks[dispatch_id] = lock
    return lock


__all__ = ["append_provider_event", "clear_provider_event_allocator_state"]
