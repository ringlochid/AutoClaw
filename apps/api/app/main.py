from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from autoclaw.openclaw.node_server import create_node_mcp_mount_app
from autoclaw.openclaw.operator_server import create_operator_mcp_app
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import request_validation_failure
from app.api.router import api_router
from app.config import get_settings
from app.core.enums import Environment
from app.db.session import dispose_db_engine, verify_database_schema
from app.runtime.control.dispatch.openclaw_runtime import close_all_dispatch_runtimes
from app.runtime.effects import start_runtime_effect_runner, stop_runtime_effect_runner
from app.runtime.openclaw import (
    build_openclaw_gateway_adapter,
    openclaw_startup_compatibility_required,
)
from app.runtime.watchdog import start_runtime_watchdog, stop_runtime_watchdog


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.env != Environment.TEST:
        await verify_database_schema()
    if openclaw_startup_compatibility_required(settings):
        adapter = build_openclaw_gateway_adapter(settings)
        await adapter.check_compatibility()
    async with AsyncExitStack() as stack:
        operator_mcp_app = getattr(app.state, "operator_mcp_app", None)
        if operator_mcp_app is not None:
            await stack.enter_async_context(
                operator_mcp_app.router.lifespan_context(operator_mcp_app)
            )
        await start_runtime_effect_runner()
        await start_runtime_watchdog()
        try:
            yield
        finally:
            await stop_runtime_watchdog()
            await stop_runtime_effect_runner()
            await close_all_dispatch_runtimes()
            await dispose_db_engine()


def create_app(*, enable_mcp_mounts: bool | None = None) -> FastAPI:
    settings = get_settings()
    if enable_mcp_mounts is None:
        enable_mcp_mounts = settings.env != Environment.TEST
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
    if enable_mcp_mounts:
        operator_mcp_app = create_operator_mcp_app(host=settings.api_host)
        app.state.operator_mcp_app = operator_mcp_app
        app.mount("/operator", operator_mcp_app)
        app.mount("/node/mcp", create_node_mcp_mount_app(host=settings.api_host))
    return app


app = create_app()
