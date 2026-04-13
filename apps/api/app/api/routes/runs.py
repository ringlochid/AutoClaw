from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db_session
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
    build_run_inspect_payload,
    create_run,
    start_run_from_workflow,
)
from app.services.run_service import record_checkpoint as service_record_checkpoint

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def create_run_route(payload: RunCreate, session=Depends(get_db_session)) -> RunRead:
    run = await create_run(session, payload)
    await session.commit()
    return RunRead.model_validate(run)


@router.post("/from-workflow/{workflow_key}", response_model=RunStartResponse, status_code=status.HTTP_201_CREATED)
async def start_from_workflow(
    workflow_key: str,
    payload: RunStartFromWorkflowCreate,
    session=Depends(get_db_session),
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
        )

    await session.commit()
    first_flow_node = flow_nodes[0]
    return RunStartResponse(
        run_id=run.id,
        task_id=task.id,
        attempt_id=attempt.id,
        flow_id=flow.id,
        compiled_plan_id=run.compiled_plan_id,
        attempt_number=attempt.number,
        flow_node_count=len(flow_nodes),
        first_flow_node_id=first_flow_node.id,
    )


@router.get("/{run_id}", response_model=RunInspectResponse)
async def get_run(run_id: str, session=Depends(get_db_session)) -> RunInspectResponse:
    try:
        payload = await build_run_inspect_payload(session, run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return payload


@router.post("/checkpoints", response_model=CheckpointRead, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(payload: CheckpointWrite, session=Depends(get_db_session)) -> CheckpointRead:
    checkpoint = await service_record_checkpoint(session, payload)
    await session.commit()
    return CheckpointRead.model_validate(checkpoint)
