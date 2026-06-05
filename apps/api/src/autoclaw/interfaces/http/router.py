from fastapi import APIRouter

from autoclaw.interfaces.http.routers.callback import router as callback_router
from autoclaw.interfaces.http.routers.definitions import router as definitions_router
from autoclaw.interfaces.http.routers.health import router as health_router
from autoclaw.interfaces.http.routers.observability import router as observability_router
from autoclaw.interfaces.http.routers.operator import router as operator_router
from autoclaw.interfaces.http.routers.runtime import router as runtime_router
from autoclaw.interfaces.http.routers.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(definitions_router)
api_router.include_router(tasks_router)
api_router.include_router(runtime_router)
api_router.include_router(operator_router)
api_router.include_router(callback_router)
api_router.include_router(observability_router)
