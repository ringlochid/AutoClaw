from collections.abc import AsyncIterator
from contextlib import ExitStack, asynccontextmanager
from importlib import resources
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings
from app.core.enums import Environment
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime.watchdog_service import WatchdogService

REPO_CONSOLE_DIST_ROOT = Path(__file__).resolve().parents[2] / "console" / "dist"
PACKAGED_CONSOLE_PACKAGE = "app.resources"
_console_resource_stacks: list[ExitStack] = []
_RESERVED_CONSOLE_PREFIXES = (
    "approvals",
    "assets",
    "console",
    "docs",
    "flows",
    "healthz",
    "internal",
    "openapi.json",
    "readyz",
    "redoc",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    watchdog_service: WatchdogService | None = None
    if settings.watchdog_enabled:
        watchdog_service = WatchdogService(
            settings=settings,
            session_factory=get_session_factory(),
        )
        watchdog_service.start()
        app.state.watchdog_service = watchdog_service

    try:
        yield
    finally:
        if watchdog_service is not None:
            await watchdog_service.stop()
        console_resource_stack = getattr(app.state, "console_resource_stack", None)
        if console_resource_stack is not None:
            console_resource_stack.close()
        await dispose_db_engine()


def _resolve_packaged_console_dist_root() -> Path | None:
    try:
        resource_root = resources.files(PACKAGED_CONSOLE_PACKAGE).joinpath("web")
    except ModuleNotFoundError:
        return None
    if not resource_root.is_dir():
        return None

    resource_stack = ExitStack()
    resolved_root = Path(resource_stack.enter_context(resources.as_file(resource_root)))
    if not resolved_root.is_dir():
        resource_stack.close()
        return None

    _console_resource_stacks.append(resource_stack)
    return resolved_root


def _resolve_console_dist_root() -> Path | None:
    packaged_root = _resolve_packaged_console_dist_root()
    if packaged_root is not None:
        return packaged_root
    if REPO_CONSOLE_DIST_ROOT.is_dir():
        return REPO_CONSOLE_DIST_ROOT
    return None


def _configure_packaged_console(app: FastAPI) -> None:
    console_root = _resolve_console_dist_root()
    if console_root is None:
        return

    assets_root = console_root / "assets"
    index_path = console_root / "index.html"
    if _console_resource_stacks:
        app.state.console_resource_stack = _console_resource_stacks.pop()

    if assets_root.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_root), name="console-assets")
    if not index_path.is_file():
        return

    @app.get("/console/config", include_in_schema=False)
    async def console_runtime_config() -> dict[str, object]:
        return {
            "apiBaseUrl": "",
            "apiKey": None,
            "apiKeyHeader": "X-AutoClaw-API-Key",
            "authMode": "manual-or-proxy-header",
            "refreshIntervalMs": 5000,
            "supportsAuthoring": False,
        }

    @app.get("/", include_in_schema=False)
    async def console_index() -> FileResponse:
        return FileResponse(index_path)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def console_spa(full_path: str) -> FileResponse:
        if full_path.startswith(_RESERVED_CONSOLE_PREFIXES):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index_path)


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
    app.include_router(api_router)
    _configure_packaged_console(app)
    return app


app = create_app()
