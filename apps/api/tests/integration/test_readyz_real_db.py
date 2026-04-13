from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_readyz_uses_real_database() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "autoclaw-api"}
