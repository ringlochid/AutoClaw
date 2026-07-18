from __future__ import annotations

import tomllib
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import Environment, get_settings
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.interfaces.http.errors import request_validation_failure
from autoclaw.interfaces.http.router import api_router
from autoclaw.interfaces.mcp.node.server import create_node_mcp_apps
from autoclaw.interfaces.mcp.operator.server import (
    OperatorEffectPublishers,
    create_operator_mcp_app,
)
from autoclaw.interfaces.mcp.transport import node_mcp_transport_policy
from autoclaw.interfaces.web_console.router import mount_packaged_web_console
from autoclaw.persistence.session import (
    dispose_db_engine,
    ensure_database_schema,
    get_session_factory,
)
from autoclaw.runtime.boundary import create_boundary_accepted_handler
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_run import create_command_run_terminal_handler
from autoclaw.runtime.dispatch.cleanup import cleanup_aged_dispatch_request_directories
from autoclaw.runtime.dispatch.preparation import DispatchOpeningDependencies
from autoclaw.runtime.human_request import create_human_request_terminal_handler
from autoclaw.runtime.launch.continuation import create_flow_start_handler
from autoclaw.runtime.node_mcp import DispatchMcpBindingRegistry
from autoclaw.runtime.node_operations import NodeOperationExecutor
from autoclaw.runtime.post_commit import (
    BoundaryAccepted,
    CommandRunTerminal,
    FlowStartCommitted,
    HumanRequestTerminal,
    RuntimeEffectRouter,
)
from autoclaw.runtime.post_commit.bootstrap import audit_startup_runtime_effects
from autoclaw.runtime.projection import SupportProjectionOwner
from autoclaw.runtime.startup_audit import audit_startup_support_projections

_RUNTIME_STARTUP_ROUTED_SIGNAL_TYPES = (
    FlowStartCommitted,
    BoundaryAccepted,
    HumanRequestTerminal,
    CommandRunTerminal,
)


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
    runtime_effect_router = _build_runtime_effect_router()
    support_projection_owner = SupportProjectionOwner(
        session_factory=_runtime_session_context,
    )
    app.state.runtime_effect_router = runtime_effect_router
    app.state.runtime_effect_publisher = runtime_effect_router
    app.state.support_projection_owner = support_projection_owner
    app.state.support_projection_publisher = support_projection_owner
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
        operator_mcp_app = create_operator_mcp_app(
            host=settings.api_host,
            effect_publishers=OperatorEffectPublishers(
                runtime_effect_publisher=runtime_effect_router,
                support_projection_publisher=support_projection_owner,
            ),
        )
        binding_registry = DispatchMcpBindingRegistry()
        node_mcp_apps = create_node_mcp_apps(
            binding_registry=binding_registry,
            operation_executor=NodeOperationExecutor(
                runtime_effect_publisher=runtime_effect_router,
                support_projection_publisher=support_projection_owner,
            ),
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
        settings = get_settings()
        app.state.dispatch_request_cleanup = await cleanup_aged_dispatch_request_directories(
            session_factory=_runtime_session_context,
            data_boundary=settings.data_dir,
            now=utc_now(),
        )
        runtime_effect_router: RuntimeEffectRouter = app.state.runtime_effect_router
        support_projection_owner: SupportProjectionOwner = app.state.support_projection_owner
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(runtime_effect_router)
            await stack.enter_async_context(support_projection_owner)
            for mcp_app in getattr(app.state, "mcp_lifespan_apps", ()):
                await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
            app.state.runtime_startup_audit = await audit_startup_runtime_effects(
                session_factory=_runtime_session_context,
                publish=runtime_effect_router.publish,
                routed_signal_types=_RUNTIME_STARTUP_ROUTED_SIGNAL_TYPES,
            )
            app.state.support_projection_startup_audit = await audit_startup_support_projections(
                session_factory=_runtime_session_context,
                publish=support_projection_owner.publish_startup,
            )
            yield
    finally:
        await dispose_db_engine()


def _build_runtime_effect_router() -> RuntimeEffectRouter:
    router = RuntimeEffectRouter(session_factory=_runtime_session_context)
    dependencies = DispatchOpeningDependencies.create(
        settings=get_settings(),
        available_adapter_kinds=tuple(ProviderKind),
        post_commit_publisher=router,
    )
    router.register(FlowStartCommitted, create_flow_start_handler(dependencies))
    router.register(BoundaryAccepted, create_boundary_accepted_handler(dependencies))
    router.register(
        HumanRequestTerminal,
        create_human_request_terminal_handler(dependencies),
    )
    router.register(
        CommandRunTerminal,
        create_command_run_terminal_handler(dependencies),
    )
    return router


def _runtime_session_context() -> AbstractAsyncContextManager[AsyncSession]:
    return get_session_factory()()


app: FastAPI = create_app()

__all__ = ["app", "create_app"]
