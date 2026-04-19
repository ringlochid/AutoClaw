from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.presenters.runtime import to_task_read
from app.db.models.runtime import Task
from app.schemas.runtime import TaskCreate, TaskFileUploadRead, TaskRead
from app.services.task_service import create_task, upload_task_file

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    deprecated=True,
)
async def create_task_route(payload: TaskCreate, session: DbSession) -> TaskRead:
    task = await create_task(session, payload)
    await session.commit()
    await session.refresh(task)
    return to_task_read(task)


@router.post(
    "/{task_id}/uploads",
    response_model=TaskFileUploadRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_task_file_route(
    task_id: UUID,
    session: DbSession,
    file: UploadFile = File(...),
    target_slot: str = Form("context_docs"),
    relative_path: str | None = Form(None),
) -> TaskFileUploadRead:
    task = await session.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        uploaded = await upload_task_file(
            session,
            task=task,
            file=file,
            target_slot=target_slot,
            relative_path=relative_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return uploaded
