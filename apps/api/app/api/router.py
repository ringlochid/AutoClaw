from fastapi import APIRouter

from app.api.routes.callback import router as callback_router
from app.api.routes.health import router as health_router
from app.api.routes.observability import router as observability_router
from app.api.routes.operator import router as operator_router
from app.api.routes.runtime import router as runtime_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(runtime_router)
api_router.include_router(operator_router)
api_router.include_router(callback_router)
api_router.include_router(observability_router)
