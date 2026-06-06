from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import sqlite3
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import DEFAULT_API_PORT, DEFAULT_LOG_LEVEL, get_settings
from autoclaw.interfaces.cli.commands.bootstrap import (
    ensure_database_ready_with_legacy_sqlite_repair,
)
from autoclaw.persistence.session import dispose_db_engine, get_async_engine
from sqlalchemy import inspect, text

from .cli_test_support import assert_seeded_registry_is_bootstrapped, build_cli_init_args


@pytest.mark.asyncio
async def test_db_reset_recreates_sqlite_database(tmp_path: Path) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.persistence"

    try:
        await cli.cmd_init(build_cli_init_args(config_path, data_dir))
        database_path.write_bytes(b"stale")
        result = await cli.cmd_db_reset(
            argparse.Namespace(config=str(config_path), revision="head", json=False)
        )
    finally:
        await dispose_db_engine()

    assert result == 0
    assert database_path.exists()
    assert_seeded_registry_is_bootstrapped(database_path)


@pytest.mark.asyncio
async def test_db_upgrade_rejects_stale_sqlite_schema_that_cannot_be_retrofitted(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.persistence"
    init_args = build_cli_init_args(config_path, data_dir)
    init_args.skip_db_upgrade = True

    try:
        await cli.cmd_init(init_args)
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE flows (
                    flow_id TEXT PRIMARY KEY,
                    task_id TEXT UNIQUE,
                    compiled_plan_id TEXT,
                    status TEXT,
                    active_flow_revision_id TEXT,
                    current_open_dispatch_id TEXT,
                    current_node_key TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.commit()

        with pytest.raises(RuntimeError, match="autoclaw db reset"):
            await asyncio.to_thread(
                cli.cmd_db_upgrade,
                argparse.Namespace(config=str(config_path)),
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.persistence"
    init_args = build_cli_init_args(config_path, data_dir)
    init_args.skip_db_upgrade = True

    try:
        init_result = await cli.cmd_init(init_args)
        upgrade_result = await asyncio.to_thread(
            cli.cmd_db_upgrade,
            argparse.Namespace(config=str(config_path), revision="head"),
        )
    finally:
        await dispose_db_engine()

    assert init_result == 0
    assert upgrade_result == 0
    assert_seeded_registry_is_bootstrapped(database_path)


@pytest.mark.asyncio
async def test_legacy_postgres_schema_repair_moves_tables_to_backup_schema(
    tmp_path: Path,
) -> None:
    if importlib.util.find_spec("asyncpg") is None:
        pytest.skip("asyncpg not installed")

    database_url = os.environ.get("AUTOCLAW_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("AUTOCLAW_TEST_POSTGRES_URL not set")

    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli.cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=database_url,
            host="127.0.0.1",
            port=DEFAULT_API_PORT,
            log_level=DEFAULT_LOG_LEVEL,
            api_key="test-api-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=True,
            json=False,
        )
    )

    with cli.command_env(config_path=config_path):
        get_settings.cache_clear()
        await dispose_db_engine()
        engine = get_async_engine()
        async with engine.begin() as connection:
            await connection.execute(text("DROP TABLE IF EXISTS flows CASCADE"))
            await connection.execute(
                text("CREATE TABLE flows (task_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
            )
        await dispose_db_engine()
        repair = await ensure_database_ready_with_legacy_sqlite_repair(database_url)
        assert repair is not None
        assert repair.is_repaired is True
        assert repair.backup_path.startswith("autoclaw_legacy")
        engine = get_async_engine()
        async with engine.begin() as connection:
            public_tables = set(
                await connection.run_sync(lambda conn: inspect(conn).get_table_names())
            )
            backup_tables = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=repair.backup_path)
                )
            )
        await dispose_db_engine()

    assert "flows" in public_tables
    assert "flow_revisions" in public_tables
    assert "flows" in backup_tables
