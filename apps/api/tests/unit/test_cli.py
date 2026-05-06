from __future__ import annotations

import argparse
import asyncio
import sqlite3
from importlib import resources
from pathlib import Path

import pytest
from app import cli
from app.db.session import dispose_db_engine

SEED_KIND_TO_TABLE = {
    "roles": "role_definitions",
    "policies": "policy_definitions",
    "workflows": "workflow_definitions",
}


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


def _packaged_seed_counts() -> dict[str, int]:
    definitions_root = resources.files("app.resources").joinpath("definitions")
    with resources.as_file(definitions_root) as seed_root:
        return {
            kind: len(list(seed_root.joinpath(kind).glob("*.yaml"))) for kind in SEED_KIND_TO_TABLE
        }


def _seeded_registry_counts(database_path: Path) -> tuple[set[str], dict[str, int]]:
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        counts = {
            kind: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for kind, table in SEED_KIND_TO_TABLE.items()
        }
    return table_names, counts


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
    expected_seed_counts = _packaged_seed_counts()
    table_names, seeded_counts = _seeded_registry_counts(database_path)
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert seeded_counts == expected_seed_counts

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


def test_packaged_seed_definitions_are_available() -> None:
    definitions_root = resources.files("app.resources").joinpath("definitions")

    assert definitions_root.joinpath("roles").joinpath("planning_lead.yaml").is_file()
    assert definitions_root.joinpath("policies").joinpath("standard_worker.yaml").is_file()
    assert (
        definitions_root.joinpath("workflows")
        .joinpath("normal_parent_first_release.yaml")
        .is_file()
    )


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
    expected_seed_counts = _packaged_seed_counts()
    table_names, seeded_counts = _seeded_registry_counts(database_path)
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert seeded_counts == expected_seed_counts


@pytest.mark.asyncio
async def test_db_upgrade_rejects_stale_sqlite_schema_that_cannot_be_retrofitted(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.db"
    init_args = _build_init_args(config_path, data_dir)
    init_args.skip_db_upgrade = True

    try:
        await cli._cmd_init(init_args)
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
                cli._cmd_db_upgrade,
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
    database_path = data_dir / "autoclaw.db"
    init_args = _build_init_args(config_path, data_dir)
    init_args.skip_db_upgrade = True

    try:
        init_result = await cli._cmd_init(init_args)
        upgrade_result = await asyncio.to_thread(
            cli._cmd_db_upgrade,
            argparse.Namespace(
                config=str(config_path),
                revision="head",
            ),
        )
    finally:
        await dispose_db_engine()

    assert init_result == 0
    assert upgrade_result == 0
    expected_seed_counts = _packaged_seed_counts()
    table_names, seeded_counts = _seeded_registry_counts(database_path)
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert seeded_counts == expected_seed_counts
