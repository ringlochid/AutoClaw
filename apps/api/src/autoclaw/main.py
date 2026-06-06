from __future__ import annotations

import tomllib
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from autoclaw.config import Environment, get_settings
from autoclaw.integrations.openclaw.gateway import (
    build_openclaw_gateway_adapter,
    openclaw_startup_compatibility_required,
)
from autoclaw.interfaces.http.errors import request_validation_failure
from autoclaw.interfaces.http.router import api_router
from autoclaw.interfaces.mcp import (
    create_node_mcp_mount_app,
    create_operator_mcp_app,
)
from autoclaw.persistence.session import dispose_db_engine, verify_database_schema
from autoclaw.runtime.lifecycle import shutdown_runtime_lifecycle
from autoclaw.runtime.post_commit import start_runtime_effect_runner
from autoclaw.runtime.watchdog import start_runtime_watchdog


def _package_version() -> str:
    try:
        return version("autoclaw")
    except PackageNotFoundError:
        for parent in Path(__file__).resolve().parents:
            pyproject_path = parent / "pyproject.toml"
            if not pyproject_path.is_file():
                continue
            with pyproject_path.open("rb") as handle:
                pyproject = tomllib.load(handle)
            project = pyproject.get("project", {})
            project_version = project.get("version")
            if isinstance(project_version, str):
                return project_version
            break
    return "0.0.0"


def create_app(
    *,
    should_enable_mcp_mounts: bool | None = None,
) -> FastAPI:
    settings = get_settings()
    if should_enable_mcp_mounts is None:
        should_enable_mcp_mounts = settings.env != Environment.TEST

    docs_enabled = settings.env in {Environment.DEVELOPMENT, Environment.TEST}
    app = FastAPI(
        title="AutoClaw API",
        version=_package_version(),
        lifespan=_lifespan,
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
    if should_enable_mcp_mounts:
        operator_mcp_app = create_operator_mcp_app(host=settings.api_host)
        app.state.operator_mcp_app = operator_mcp_app
        app.mount("/operator", operator_mcp_app)
        app.mount("/node/mcp", create_node_mcp_mount_app(host=settings.api_host))
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
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
            await shutdown_runtime_lifecycle()
            await dispose_db_engine()


app: FastAPI = create_app()

__all__ = ["app", "create_app"]
