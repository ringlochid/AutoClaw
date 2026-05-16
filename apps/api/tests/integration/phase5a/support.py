from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import cli
from app.config import get_settings
from app.db.session import dispose_db_engine, get_session_factory
from app.main import create_app
from app.runtime import TaskComposeInput
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase4a.support import LocalGatewayTestServer


@dataclass(frozen=True)
class Phase5aHttpContext:
    client: AsyncClient
    operator_headers: dict[str, str]
    session_factory: async_sessionmaker[AsyncSession]
    data_dir: Path
    tmp_path: Path


def task_start_payload(
    workflow_key: str = "minimal-implement-change",
    **roots: Any,
) -> TaskComposeInput:
    payload: dict[str, Any] = {
        "task": {
            "key": "auth-refresh-hardening",
            "title": "Harden auth refresh flow",
            "summary": "Investigate and fix the auth refresh regression.",
            "instruction": "Stay scoped to the auth refresh failure path only.",
        },
        "workflow": {"key": workflow_key},
    }
    if roots:
        payload["roots"] = roots
    return TaskComposeInput.model_validate(payload)


@asynccontextmanager
async def phase5a_http_context(tmp_path: Path) -> AsyncIterator[Phase5aHttpContext]:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    await cli._cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=None,
            host="127.0.0.1",
            port=8123,
            log_level="INFO",
            api_key="api-test-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=False,
            json=False,
        )
    )
    try:
        with gateway_server.configured_env(), cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            app = create_app()
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    yield Phase5aHttpContext(
                        client=client,
                        operator_headers={"X-AutoClaw-API-Key": "api-test-key"},
                        session_factory=get_session_factory(),
                        data_dir=data_dir,
                        tmp_path=tmp_path,
                    )
    finally:
        get_settings.cache_clear()
        await dispose_db_engine()
        gateway_server.close()
