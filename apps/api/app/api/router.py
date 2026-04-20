from fastapi import APIRouter, Depends

from app.api.deps import require_api_key, require_internal_api_key
from app.api.routes.approvals import internal_router as approvals_internal_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.compiler import router as compiler_router
from app.api.routes.flows import internal_router as flows_internal_router
from app.api.routes.flows import router as flows_router
from app.api.routes.health import router as health_router
from app.api.routes.registry import internal_router as registry_internal_router
from app.api.routes.registry import router as registry_router
from app.api.routes.tasks import internal_router as tasks_internal_router
from app.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(
    flows_router,
    dependencies=[Depends(require_api_key)],
)
api_router.include_router(
    tasks_router,
    dependencies=[Depends(require_api_key)],
)
api_router.include_router(
    approvals_router,
    dependencies=[Depends(require_api_key)],
)
api_router.include_router(
    registry_router,
    dependencies=[Depends(require_api_key)],
)
internal_router = APIRouter(prefix="/internal", tags=["internal"])
internal_router.include_router(registry_internal_router)
internal_router.include_router(tasks_internal_router)
internal_router.include_router(compiler_router)
internal_router.include_router(approvals_internal_router)
internal_router.include_router(flows_internal_router)

api_router.include_router(internal_router, dependencies=[Depends(require_internal_api_key)])
