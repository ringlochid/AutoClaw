from __future__ import annotations

from pathlib import Path

from autoclaw.interfaces.web_console import get_packaged_web_console_assets_root
from autoclaw.main import create_app
from httpx import ASGITransport, AsyncClient


async def test_packaged_web_console_serves_index_for_spa_routes() -> None:
    app = create_app(should_enable_mcp_mounts=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        root_response = await client.get("/")
        task_detail_response = await client.get("/tasks/task-runtime-route-copy")
        editor_response = await client.get("/definitions/editor")

    assert root_response.status_code == 200
    assert root_response.headers["content-type"].startswith("text/html")
    assert '<div id="root"></div>' in root_response.text
    assert "AutoClaw Console" in root_response.text
    assert task_detail_response.status_code == 200
    assert task_detail_response.text == root_response.text
    assert editor_response.status_code == 200
    assert editor_response.text == root_response.text


async def test_packaged_web_console_serves_static_assets() -> None:
    assets_root = get_packaged_web_console_assets_root()
    stylesheet_path = _first_asset_with_suffix(assets_root / "assets", ".css")
    app = create_app(should_enable_mcp_mounts=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        icon_response = await client.get("/app-icon.png")
        manifest_response = await client.get("/site.webmanifest")
        stylesheet_response = await client.get(f"/assets/{stylesheet_path.name}")

    assert icon_response.status_code == 200
    assert icon_response.headers["content-type"] == "image/png"
    assert manifest_response.status_code == 200
    assert manifest_response.headers["content-type"].startswith("application/manifest+json")
    assert stylesheet_response.status_code == 200
    assert stylesheet_response.headers["content-type"].startswith("text/css")
    assert "--ac-background" in stylesheet_response.text


async def test_packaged_web_console_serves_runtime_config() -> None:
    app = create_app(should_enable_mcp_mounts=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/console/config")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "apiBaseUrl": "http://test",
        "apiKey": "autoclaw-operator-test-key",
    }
    assert "internal" not in response.text


def _first_asset_with_suffix(directory: Path, suffix: str) -> Path:
    for path in sorted(directory.iterdir()):
        if path.suffix == suffix:
            return path
    raise AssertionError(f"missing packaged console asset with suffix {suffix}")
