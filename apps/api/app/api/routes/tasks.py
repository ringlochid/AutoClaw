from fastapi import APIRouter, Depends

from app.db.session import get_db_session
from app.schemas.runtime import TaskCreate, TaskRead
from app.services.run_service import create_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead)
async def create_task_route(payload: TaskCreate, session=Depends(get_db_session)) -> TaskRead:
    task = await create_task(session, payload)
    await session.commit()
    return TaskRead.model_validate(task)
