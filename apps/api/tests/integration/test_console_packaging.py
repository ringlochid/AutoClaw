from __future__ import annotations

import re

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_packaged_console_index_is_served() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AutoClaw Console" in response.text
    assert "/assets/" in response.text


async def test_console_runtime_config_is_served() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/console/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["apiBaseUrl"] == ""
    assert payload["apiKey"]
    assert payload["supportsAuthoring"] is True


async def test_packaged_console_assets_and_spa_fallback_are_served() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        index_response = await client.get("/")
        assert index_response.status_code == 200

        asset_match = re.search(r'src="(?P<path>/assets/[^"]+\.js)"', index_response.text)
        assert asset_match is not None

        asset_response = await client.get(asset_match.group("path"))
        assert asset_response.status_code == 200
        assert asset_response.text

        spa_response = await client.get("/operator/flows/demo")
        assert spa_response.status_code == 200
        assert "AutoClaw Console" in spa_response.text

        reserved_response = await client.get("/flows/not-a-real-route")
        assert reserved_response.status_code == 401
