from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.api.presenters.runtime import to_task_read
from app.schemas.runtime import TaskCreate, TaskRead
from app.services.task_service import create_task

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
    return to_task_read(task)
