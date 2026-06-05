from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.interfaces.http.dependencies import require_api_key
from autoclaw.interfaces.http.errors import raise_runtime_exception
from autoclaw.persistence.session import get_db_session
from autoclaw.runtime.contracts import ObservabilityFileRef
from autoclaw.runtime.observability import observability_ref

router = APIRouter(
    prefix="/observability",
    tags=["observability"],
    dependencies=[Depends(require_api_key)],
)
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/tasks/{task_id}/delivery-state", response_model=ObservabilityFileRef)
async def get_delivery_state(
    task_id: str,
    session: DBSession,
) -> ObservabilityFileRef:
    try:
        return await observability_ref(
            session,
            task_id,
            "delivery-state.json",
            "Latest task-scoped delivery-state projection.",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.get("/tasks/{task_id}/continuity-state", response_model=ObservabilityFileRef)
async def get_continuity_state(
    task_id: str,
    session: DBSession,
) -> ObservabilityFileRef:
    try:
        return await observability_ref(
            session,
            task_id,
            "continuity-state.json",
            "Latest task-scoped continuity-state projection.",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.get("/tasks/{task_id}/watchdog-state", response_model=ObservabilityFileRef)
async def get_watchdog_state(
    task_id: str,
    session: DBSession,
) -> ObservabilityFileRef:
    try:
        return await observability_ref(
            session,
            task_id,
            "watchdog-state.json",
            "Latest task-scoped watchdog-state projection.",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.get("/tasks/{task_id}/provider-events", response_model=ObservabilityFileRef)
async def get_provider_events(
    task_id: str,
    session: DBSession,
) -> ObservabilityFileRef:
    try:
        return await observability_ref(
            session,
            task_id,
            "provider-events.ndjson",
            "Normalized provider-event history for the selected task.",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
