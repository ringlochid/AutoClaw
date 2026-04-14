from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TaskStatus
from app.db.models.runtime import Task
from app.schemas.runtime import TaskCreate


async def create_task(session: AsyncSession, payload: TaskCreate) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        input_payload=payload.input_payload,
        status=TaskStatus.PENDING,
    )
    session.add(task)
    await session.flush()
    return task
