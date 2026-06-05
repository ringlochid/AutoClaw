from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _run_packaged_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("AUTOCLAW_")}
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(PACKAGE_ROOT)
        if not existing_pythonpath
        else os.pathsep.join((str(PACKAGE_ROOT), existing_pythonpath))
    )
    result = subprocess.run(
        [sys.executable, "-m", "autoclaw", *args],
        cwd=PACKAGE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def test_db_reset_recreates_seeded_sqlite_database_on_packaged_cli_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.persistence"

    _run_packaged_cli(
        "init",
        "--config",
        str(config_path),
        "--data-dir",
        str(data_dir),
        "--host",
        "127.0.0.1",
        "--port",
        "8123",
        "--log-level",
        "INFO",
        "--api-key",
        "api-test-key",
        "--internal-api-key",
        "internal-test-key",
        "--force",
    )
    database_path.write_bytes(b"stale")

    _run_packaged_cli(
        "db",
        "reset",
        "--config",
        str(config_path),
    )

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
