from fastapi import APIRouter, Depends, Query

from app.db.session import get_db_session
from app.services.registry_service import bootstrap_registry

router = APIRouter(prefix="/registry", tags=["registry"])


@router.post("/bootstrap")
async def bootstrap(
    session=Depends(get_db_session),
    publish: bool = Query(default=True),
) -> dict[str, int]:
    result = await bootstrap_registry(session, publish=publish)
    await session.commit()
    return result
