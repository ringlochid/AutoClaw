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
from autoclaw.interfaces.http.errors import request_validation_failure
from autoclaw.interfaces.http.router import api_router
from autoclaw.interfaces.mcp.node.server import create_node_mcp_apps
from autoclaw.interfaces.mcp.operator.server import create_operator_mcp_app
from autoclaw.interfaces.mcp.transport import node_mcp_transport_policy
from autoclaw.interfaces.web_console.router import mount_packaged_web_console
from autoclaw.persistence.session import (
    dispose_db_engine,
    ensure_database_schema,
)
from autoclaw.runtime.node_mcp import DispatchMcpBindingRegistry
from autoclaw.runtime.node_operations import NodeOperationExecutor


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
    mount_packaged_web_console(app)
    if should_enable_mcp_mounts:
        operator_mcp_app = create_operator_mcp_app(host=settings.api_host)
        binding_registry = DispatchMcpBindingRegistry()
        node_mcp_apps = create_node_mcp_apps(
            binding_registry=binding_registry,
            operation_executor=NodeOperationExecutor(),
            transport_policy=node_mcp_transport_policy(
                host=settings.api_host,
                port=settings.api_port,
                allowed_origins=settings.console_origins,
            ),
        )
        app.state.dispatch_mcp_binding_registry = binding_registry
        app.state.mcp_lifespan_apps = (
            operator_mcp_app,
            node_mcp_apps.managed,
            node_mcp_apps.compatibility,
        )
        app.mount("/operator", operator_mcp_app)
        app.mount("/_internal/node", node_mcp_apps.managed)
        app.mount("/node", node_mcp_apps.compatibility)
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        await ensure_database_schema()
        async with AsyncExitStack() as stack:
            for mcp_app in getattr(app.state, "mcp_lifespan_apps", ()):
                await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
            yield
    finally:
        await dispose_db_engine()


app: FastAPI = create_app()

__all__ = ["app", "create_app"]
