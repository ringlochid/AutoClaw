from __future__ import annotations

import argparse
import asyncio
import sqlite3
from pathlib import Path

import pytest
from app import cli
from app.config import get_settings
from app.db.session import dispose_db_engine
from app.main import create_app
from sqlalchemy.engine import make_url


def _write_stale_flows_schema(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE flows (task_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        connection.commit()


async def test_lifespan_fails_closed_on_stale_runtime_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    monkeypatch.setenv("AUTOCLAW_ENV", "development")

    try:
        await cli.cmd_init(
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

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            database_path = Path(make_url(get_settings().database_url).database or "")
        await dispose_db_engine()

        await asyncio.to_thread(_write_stale_flows_schema, database_path)

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            app = create_app()
            with pytest.raises(
                RuntimeError,
                match=r"flows missing column .*Run `autoclaw db reset`\.",
            ):
                async with app.router.lifespan_context(app):
                    pass
    finally:
        await dispose_db_engine()
