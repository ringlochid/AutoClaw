from fastapi import APIRouter

from app.api.routes.approvals import router as approvals_router
from app.api.routes.compiler import router as compiler_router
from app.api.routes.flows import router as flows_router
from app.api.routes.health import router as health_router
from app.api.routes.registry import router as registry_router
from app.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tasks_router, include_in_schema=False, tags=["internal"])
api_router.include_router(registry_router)
api_router.include_router(compiler_router)
api_router.include_router(flows_router)
api_router.include_router(approvals_router)
