from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.services.registry_service import bootstrap_registry

router = APIRouter(prefix="/registry", tags=["registry"])


@router.post("/bootstrap")
async def bootstrap(
    session: DbSession,
    publish: bool = Query(default=True),
) -> dict[str, int]:
    result = await bootstrap_registry(session, publish=publish)
    await session.commit()
    return result
