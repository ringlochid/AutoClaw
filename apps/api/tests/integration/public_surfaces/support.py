from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import autoclaw.interfaces.cli as cli
from autoclaw.config import DEFAULT_API_PORT, get_settings
from autoclaw.main import create_app
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from autoclaw.runtime import TaskComposeInput
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.operator_auth_headers import OPERATOR_HEADERS
from tests.helpers.runtime_support import initialize_runtime_from_template


@dataclass(frozen=True)
class PublicApiContext:
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
async def public_api_context(tmp_path: Path) -> AsyncIterator[PublicApiContext]:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    init_args = argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        host="127.0.0.1",
        port=DEFAULT_API_PORT,
        log_level="INFO",
        api_key="api-test-key",
        force=True,
        skip_db_upgrade=False,
        json=False,
    )
    await initialize_runtime_from_template(
        config_path=config_path,
        data_dir=data_dir,
        log_level=init_args.log_level,
        api_key=init_args.api_key,
        host=init_args.host,
        port=init_args.port,
    )
    try:
        with gateway_server.configured_env(), cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            app = create_app()
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    yield PublicApiContext(
                        client=client,
                        operator_headers=OPERATOR_HEADERS,
                        session_factory=get_session_factory(),
                        data_dir=data_dir,
                        tmp_path=tmp_path,
                    )
    finally:
        get_settings.cache_clear()
        await dispose_db_engine()
        gateway_server.close()
