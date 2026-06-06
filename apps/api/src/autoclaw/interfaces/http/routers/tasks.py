from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.definitions.registry.task_start import start_task_from_definition_service
from autoclaw.interfaces.http.dependencies import require_api_key
from autoclaw.interfaces.http.errors import raise_runtime_exception
from autoclaw.persistence.session import get_db_session
from autoclaw.runtime.contracts import TaskStartRequest, TaskStartResponse
from autoclaw.runtime.post_commit.operations import write_runtime_operation_and_wait

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_api_key)])
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/start", response_model=TaskStartResponse)
async def start_task(
    request: TaskStartRequest,
    session: DBSession,
) -> TaskStartResponse:
    try:
        return await write_runtime_operation_and_wait(
            lambda active_session: start_task_from_definition_service(
                active_session,
                request,
                data_dir=get_settings().data_dir,
            ),
            task_id_getter=lambda response: response.task_id,
            session=session,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
