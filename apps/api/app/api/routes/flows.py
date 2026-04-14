from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.presenters.runtime import (
    to_checkpoint_read,
    to_flow_inspect_response,
    to_flow_start_response,
)
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.runtime.checkpoints import list_flow_checkpoints, record_checkpoint
from app.runtime.dispatcher import acknowledge_context_manifest
from app.runtime.runner import (
    cancel_flow,
    continue_flow,
    get_flow_with_relations,
    start_flow_from_workflow,
)
from app.schemas.runtime import (
    CheckpointRead,
    CheckpointWrite,
    ContextManifestRead,
    FlowInspectResponse,
    FlowStartFromWorkflowCreate,
    FlowStartResponse,
)

router = APIRouter(prefix="/flows", tags=["flows"])


@router.post(
    "/from-workflow/{workflow_key}",
    response_model=FlowStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_flow_from_workflow_route(
    workflow_key: str,
    payload: FlowStartFromWorkflowCreate,
    session: DbSession,
) -> FlowStartResponse:
    try:
        flow, revision, flow_nodes = await start_flow_from_workflow(
            session,
            workflow_key=workflow_key,
            payload=payload,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidDefinitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await session.commit()
    return to_flow_start_response(
        task=flow.task,
        flow=flow,
        flow_revision=revision,
        flow_nodes=flow_nodes,
    )


@router.post("/{flow_id}/continue", response_model=FlowInspectResponse)
async def continue_flow_route(flow_id: UUID, session: DbSession) -> FlowInspectResponse:
    try:
        flow = await continue_flow(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return to_flow_inspect_response(flow)


@router.post("/{flow_id}/cancel", response_model=FlowInspectResponse)
async def cancel_flow_route(flow_id: UUID, session: DbSession) -> FlowInspectResponse:
    try:
        flow = await cancel_flow(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await session.commit()
    return to_flow_inspect_response(flow)


@router.get("/{flow_id}", response_model=FlowInspectResponse)
async def get_flow(flow_id: UUID, session: DbSession) -> FlowInspectResponse:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No flow found: {flow_id}"
        )
    return to_flow_inspect_response(flow)


@router.get("/{flow_id}/checkpoints", response_model=list[CheckpointRead])
async def get_flow_checkpoints(flow_id: UUID, session: DbSession) -> list[CheckpointRead]:
    try:
        checkpoints_ = await list_flow_checkpoints(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [to_checkpoint_read(cp) for cp in checkpoints_]


@router.post("/checkpoints", response_model=CheckpointRead, status_code=status.HTTP_201_CREATED)
async def post_checkpoint(payload: CheckpointWrite, session: DbSession) -> CheckpointRead:
    try:
        checkpoint = await record_checkpoint(session, payload)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if isinstance(exc, NotFoundError)
            else status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await session.commit()
    return to_checkpoint_read(checkpoint)


@router.post("/context-manifests/{manifest_id}/ack", response_model=FlowInspectResponse)
async def acknowledge_context_manifest_route(
    manifest_id: UUID,
    session: DbSession,
) -> FlowInspectResponse:
    manifest = await acknowledge_context_manifest(session, manifest_id)
    await session.commit()

    flow = await get_flow_with_relations(session, manifest.flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found after ack: {manifest.flow_id}",
        )
    return to_flow_inspect_response(flow)


@router.get("/{flow_id}/context-manifests", response_model=list[ContextManifestRead])
async def get_flow_manifests(flow_id: UUID, session: DbSession) -> list[ContextManifestRead]:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No flow found: {flow_id}"
        )
    return [ContextManifestRead.model_validate(manifest) for manifest in flow.context_manifests]
