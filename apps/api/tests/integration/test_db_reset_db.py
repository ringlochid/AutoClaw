from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app import cli
from app.db.session import dispose_db_engine


async def test_db_reset_recreates_seeded_sqlite_database(tmp_path: Path) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    try:
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

        await cli._cmd_db_reset(
            argparse.Namespace(
                config=str(config_path),
                revision="head",
                json=False,
            )
        )
    finally:
        await dispose_db_engine()

    database_path = data_dir / "autoclaw.db"
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        role_count = connection.execute("SELECT COUNT(*) FROM role_definitions").fetchone()[0]
        policy_count = connection.execute("SELECT COUNT(*) FROM policy_definitions").fetchone()[0]
        workflow_count = connection.execute("SELECT COUNT(*) FROM workflow_definitions").fetchone()[
            0
        ]
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert role_count > 0
    assert policy_count > 0
    assert workflow_count > 0
