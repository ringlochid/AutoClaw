from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.api.errors import raise_runtime_exception
from app.config import get_settings
from app.db.session import get_db_session
from app.registry.task_start import start_task_from_definition_service
from app.runtime.effects import (
    commit_runtime_session,
    rollback_runtime_session,
    wait_for_runtime_effects,
)
from app.schemas.runtime import TaskStartRequest, TaskStartResponse

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_api_key)])
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/start", response_model=TaskStartResponse)
async def start_task(
    request: TaskStartRequest,
    session: DBSession,
) -> TaskStartResponse:
    try:
        response = await start_task_from_definition_service(
            session,
            request,
            data_dir=get_settings().data_dir,
        )
        await commit_runtime_session(session)
        await wait_for_runtime_effects(task_id=response.task_id)
        return response
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)
