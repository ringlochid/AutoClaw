from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.presenters.runtime import (
    to_checkpoint_read,
    to_run_inspect_response,
    to_run_read,
    to_run_start_response,
)
from app.schemas.runtime import (
    CheckpointRead,
    CheckpointWrite,
    RunCreate,
    RunInspectResponse,
    RunRead,
    RunStartFromWorkflowCreate,
    RunStartResponse,
)
from app.services.run_service import (
    create_run,
    get_run_with_relations,
    list_run_checkpoints,
    start_run_from_workflow,
)
from app.services.run_service import record_checkpoint as service_record_checkpoint

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def create_run_route(payload: RunCreate, session: DbSession) -> RunRead:
    run = await create_run(session, payload)
    await session.commit()
    return to_run_read(run)


@router.post(
    "/from-workflow/{workflow_key}",
    response_model=RunStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_from_workflow(
    workflow_key: str,
    payload: RunStartFromWorkflowCreate,
    session: DbSession,
) -> RunStartResponse:
    try:
        task, run, attempt, flow, flow_nodes = await start_run_from_workflow(
            session,
            workflow_key=workflow_key,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await session.commit()
    return to_run_start_response(
        task=task,
        run=run,
        attempt=attempt,
        flow=flow,
        flow_nodes=flow_nodes,
    )


@router.get("/{run_id}", response_model=RunInspectResponse)
async def get_run(run_id: UUID, session: DbSession) -> RunInspectResponse:
    run = await get_run_with_relations(session, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No run found: {run_id}",
        )
    return to_run_inspect_response(run)


@router.get("/{run_id}/checkpoints", response_model=list[CheckpointRead])
async def get_run_checkpoints(run_id: UUID, session: DbSession) -> list[CheckpointRead]:
    checkpoints = await list_run_checkpoints(session, run_id)
    return [to_checkpoint_read(checkpoint) for checkpoint in checkpoints]


@router.post("/checkpoints", response_model=CheckpointRead, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(payload: CheckpointWrite, session: DbSession) -> CheckpointRead:
    checkpoint = await service_record_checkpoint(session, payload)
    await session.commit()
    return to_checkpoint_read(checkpoint)
