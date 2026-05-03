from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pytest
from app import cli
from app.db.session import dispose_db_engine


def _build_init_args(config_path: Path, data_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
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
        json=True,
    )


@pytest.mark.asyncio
async def test_init_writes_minimal_config_and_db_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    try:
        result = await cli._cmd_init(_build_init_args(config_path, data_dir))
    finally:
        await dispose_db_engine()

    assert result == 0
    assert config_path.exists()
    assert data_dir.joinpath("autoclaw.db").exists()

    config_text = config_path.read_text(encoding="utf-8")
    assert 'level = "INFO"' in config_text
    assert 'api_key = "api-test-key"' in config_text
    assert 'internal_api_key = "internal-test-key"' in config_text
    assert "definitions_root" not in config_text
    assert "[app]" not in config_text

    database_path = data_dir / "autoclaw.db"
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert table_names == set()

    payload = capsys.readouterr().out
    assert '"ok": true' in payload


def test_build_parser_supports_baseline_commands() -> None:
    parser = cli.build_parser()

    serve_args = parser.parse_args(["serve"])
    assert serve_args.handler is cli._cmd_serve

    init_args = parser.parse_args(["init", "--json"])
    assert init_args.handler is cli._cmd_init
    assert init_args.json is True

    db_reset_args = parser.parse_args(["db", "reset", "--json"])
    assert db_reset_args.handler is cli._cmd_db_reset
    assert db_reset_args.json is True

    service_install_args = parser.parse_args(["service", "install", "--no-start"])
    assert service_install_args.handler is cli._cmd_service_install
    assert service_install_args.no_start is True


def test_render_service_unit_uses_python_module_entrypoint(tmp_path: Path) -> None:
    rendered = cli._render_service_unit(
        python_bin=Path("/tmp/autoclaw-venv/bin/python"),
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        env_file=tmp_path / "autoclaw.env",
    )

    assert "ExecStartPre=/tmp/autoclaw-venv/bin/python -m autoclaw db upgrade" in rendered
    assert "ExecStart=/tmp/autoclaw-venv/bin/python -m autoclaw serve" in rendered


@pytest.mark.asyncio
async def test_db_reset_recreates_sqlite_database(tmp_path: Path) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.db"

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        database_path.write_bytes(b"stale")
        result = await cli._cmd_db_reset(
            argparse.Namespace(
                config=str(config_path),
                revision="head",
                json=False,
            )
        )
    finally:
        await dispose_db_engine()

    assert result == 0
    assert database_path.exists()
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert table_names == set()
