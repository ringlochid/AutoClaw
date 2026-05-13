from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import request_validation_failure
from app.api.router import api_router
from app.config import get_settings
from app.core.enums import Environment
from app.db.session import dispose_db_engine
from app.runtime.effects import start_runtime_effect_runner, stop_runtime_effect_runner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    await start_runtime_effect_runner()
    try:
        yield
    finally:
        await stop_runtime_effect_runner()
        await dispose_db_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.env in {Environment.DEVELOPMENT, Environment.TEST}
    app = FastAPI(
        title="AutoClaw API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.console_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def _request_validation_handler(
        _request: object,
        exc: RequestValidationError,
    ) -> JSONResponse:
        failure = request_validation_failure(exc)
        return JSONResponse(
            status_code=400,
            content=failure.model_dump(mode="json"),
        )

    app.include_router(api_router)
    return app


app = create_app()
