from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.presenters.runtime import to_task_compose_read, to_task_read
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.db.models.runtime import Task, TaskCompose
from app.runtime.runner import get_flow_with_relations, start_flow_from_task_compose
from app.schemas.runtime import (
    FlowStartResponse,
    TaskComposeStartCreate,
    TaskCreate,
    TaskFileUploadRead,
    TaskRead,
)
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


@router.post(
    "/composes/start",
    response_model=FlowStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_task_compose_route(
    payload: TaskComposeStartCreate,
    session: DbSession,
) -> FlowStartResponse:
    try:
        flow, revision, flow_nodes = await start_flow_from_task_compose(session, payload=payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidDefinitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    flow = await get_flow_with_relations(session, flow.id)
    assert flow is not None
    task_compose = await session.scalar(
        select(TaskCompose).where(TaskCompose.task_id == flow.task_id)
    )
    first_flow_node = flow_nodes[0]
    return FlowStartResponse(
        flow_id=flow.id,
        task_id=flow.task_id,
        active_flow_revision_id=revision.id,
        compiled_plan_id=revision.compiled_plan_id,
        flow_node_count=len(flow_nodes),
        first_flow_node_id=first_flow_node.id,
        task=to_task_read(flow.task),
        task_compose=to_task_compose_read(task_compose),
    )
