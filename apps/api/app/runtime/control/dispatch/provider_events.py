from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel, ProviderEventRecordModel
from app.runtime.control.clock import utc_now
from app.runtime.ids import provider_event_record_id


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
    for _ in range(5):
        next_event_no = (
            int(
                await session.scalar(
                    select(func.max(ProviderEventRecordModel.event_no)).where(
                        ProviderEventRecordModel.dispatch_id == dispatch.dispatch_id
                    )
                )
                or 0
            )
            + 1
        )
        record_id = provider_event_record_id(dispatch.dispatch_id, next_event_no)
        try:
            async with session.begin_nested():
                await session.execute(
                    insert(ProviderEventRecordModel).values(
                        provider_event_record_id=record_id,
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
                )
        except IntegrityError:
            continue
        row = await session.get(ProviderEventRecordModel, record_id)
        if row is None:
            break
        return row
    raise RuntimeError(
        "failed to persist provider event after concurrent event_no allocation retries"
    )
