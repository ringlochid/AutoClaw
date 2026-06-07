from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.registry.task_start import start_task_from_definition
from autoclaw.interfaces.http.dependencies import require_api_key
from autoclaw.interfaces.http.errors import raise_runtime_exception
from autoclaw.persistence.session import get_db_session
from autoclaw.runtime.contracts import TaskStartRequest, TaskStartResponse

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_api_key)])
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/start", response_model=TaskStartResponse)
async def start_task(
    request: TaskStartRequest,
    session: DBSession,
) -> TaskStartResponse:
    try:
        return await start_task_from_definition(request, session=session)
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
