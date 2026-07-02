from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from autoclaw.interfaces.web_console import (
    get_packaged_web_console_assets_root,
    is_packaged_web_console_available,
)

web_console_router = APIRouter(include_in_schema=False)


def mount_packaged_web_console(app: FastAPI) -> None:
    if not is_packaged_web_console_available():
        return

    assets_root = get_packaged_web_console_assets_root()
    nested_assets_root = assets_root / "assets"
    if nested_assets_root.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=nested_assets_root),
            name="web-console-assets",
        )
    app.include_router(web_console_router)


@web_console_router.get("/")
@web_console_router.get("/tasks")
@web_console_router.get("/tasks/{console_path:path}")
@web_console_router.get("/definitions")
@web_console_router.get("/definitions/{console_path:path}")
@web_console_router.get("/task-start")
@web_console_router.get("/fixtures")
async def get_web_console_index(console_path: str = "") -> FileResponse:
    del console_path
    return _packaged_asset_response("index.html", media_type="text/html")


@web_console_router.get("/app-icon.png")
async def get_web_console_app_icon() -> FileResponse:
    return _packaged_asset_response("app-icon.png", media_type="image/png")


@web_console_router.get("/site.webmanifest")
async def get_web_console_manifest() -> FileResponse:
    return _packaged_asset_response("site.webmanifest", media_type="application/manifest+json")


@web_console_router.get("/mockServiceWorker.js")
async def get_web_console_mock_service_worker() -> FileResponse:
    return _packaged_asset_response("mockServiceWorker.js", media_type="text/javascript")


def _packaged_asset_response(relative_path: str, *, media_type: str) -> FileResponse:
    asset_path = get_packaged_web_console_assets_root() / relative_path
    if not _is_packaged_asset_file(asset_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(asset_path, media_type=media_type)


def _is_packaged_asset_file(path: Path) -> bool:
    assets_root = get_packaged_web_console_assets_root().resolve()
    resolved_path = path.resolve()
    return resolved_path.is_file() and resolved_path.is_relative_to(assets_root)
