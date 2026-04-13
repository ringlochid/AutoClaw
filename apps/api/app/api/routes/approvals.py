from fastapi import APIRouter, Depends

from app.db.session import get_db_session
from app.schemas.runtime import ApprovalCreate, ApprovalRead
from app.services.run_service import create_approval

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalRead)
async def create_approval_route(payload: ApprovalCreate, session=Depends(get_db_session)) -> ApprovalRead:
    approval = await create_approval(session, payload)
    await session.commit()
    return ApprovalRead.model_validate(approval)
