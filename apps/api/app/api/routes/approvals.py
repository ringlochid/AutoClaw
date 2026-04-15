from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.presenters.runtime import to_approval_read
from app.core.errors import ConflictError, NotFoundError
from app.runtime.approvals import create_approval, get_approval, resolve_approval
from app.runtime.runner import advance_flow_until_boundary
from app.schemas.runtime import ApprovalCreate, ApprovalRead, ApprovalResolve

router = APIRouter(prefix="/approvals", tags=["approvals"])
internal_router = APIRouter(prefix="/approvals", tags=["internal"])


@internal_router.post(
    "",
    response_model=ApprovalRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_approval_route(payload: ApprovalCreate, session: DbSession) -> ApprovalRead:
    try:
        approval = await create_approval(session, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return to_approval_read(approval)


@router.get("/{approval_id}", response_model=ApprovalRead)
async def get_approval_route(approval_id: UUID, session: DbSession) -> ApprovalRead:
    approval = await get_approval(session, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No approval found: {approval_id}",
        )
    return to_approval_read(approval)


@router.post("/{approval_id}/resolve", response_model=ApprovalRead)
async def resolve_approval_route(
    approval_id: UUID,
    payload: ApprovalResolve,
    session: DbSession,
) -> ApprovalRead:
    try:
        approval = await resolve_approval(session, approval_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await advance_flow_until_boundary(
        session,
        approval.flow_id,
        cause=f"approval-resolved:{payload.status.value}",
    )
    await session.commit()
    return to_approval_read(approval)
