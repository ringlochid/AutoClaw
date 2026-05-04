from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.runtime.control import observability_ref
from app.schemas.runtime import ObservabilityFileRef

router = APIRouter(prefix="/observability", tags=["observability"])
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


def _raise_runtime_error(exc: Exception) -> NoReturn:
    summary = str(exc)
    if isinstance(exc, FileNotFoundError) or "unknown " in summary or "missing " in summary:
        status_code = status.HTTP_404_NOT_FOUND
        code = "missing_target"
        retryable = False
    elif "stale" in summary:
        status_code = status.HTTP_409_CONFLICT
        code = "stale_write_conflict"
        retryable = True
    elif isinstance(exc, ValueError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "semantic_invalid"
        retryable = False
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        code = "unexpected_failure"
        retryable = False
    raise HTTPException(
        status_code=status_code,
        detail={
            "ok": False,
            "code": code,
            "summary": summary,
            "retryable": retryable,
            "field_path": None,
            "suggested_next_step": None,
        },
    ) from exc


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
        _raise_runtime_error(exc)


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
        _raise_runtime_error(exc)


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
        _raise_runtime_error(exc)


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
        _raise_runtime_error(exc)
