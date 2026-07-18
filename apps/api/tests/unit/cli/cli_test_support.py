from __future__ import annotations

import argparse
import socket
import sqlite3
from pathlib import Path

from autoclaw.config import DEFAULT_API_PORT, DEFAULT_LOG_LEVEL
from autoclaw.definitions.seeds import resolve_packaged_seed_definitions_root

SEED_KIND_TO_TABLE = {
    "roles": "role_definitions",
    "policies": "policy_definitions",
    "workflows": "workflow_definitions",
}
SEEDED_REGISTRY_TABLES = {
    "role_definitions",
    "role_revisions",
    "policy_definitions",
    "policy_revisions",
    "workflow_definitions",
    "workflow_revisions",
    "tasks",
}


def build_cli_init_args(config_path: Path, data_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        host="127.0.0.1",
        port=DEFAULT_API_PORT,
        log_level=DEFAULT_LOG_LEVEL,
        api_key="api-test-key",
        force=True,
        skip_db_upgrade=False,
        json=True,
    )


def find_available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.bind(("127.0.0.1", 0))
        return int(probe_socket.getsockname()[1])


def count_packaged_seed_definitions() -> dict[str, int]:
    with resolve_packaged_seed_definitions_root() as definitions_root:
        return {
            kind: len(list(definitions_root.joinpath(kind).glob("*.yaml")))
            for kind in SEED_KIND_TO_TABLE
        }


def read_seeded_registry_counts(database_path: Path) -> tuple[set[str], dict[str, int]]:
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


def assert_seeded_registry_is_bootstrapped(database_path: Path) -> None:
    table_names, seeded_counts = read_seeded_registry_counts(database_path)
    assert SEEDED_REGISTRY_TABLES.issubset(table_names)
    assert seeded_counts == count_packaged_seed_definitions()


def write_systemctl_show_script(
    script_path: Path,
    log_path: Path,
    *,
    active_state: str,
    sub_state: str,
) -> None:
    show_output = "\n".join(
        [
            "LoadState=loaded",
            "UnitFileState=enabled",
            f"ActiveState={active_state}",
            f"SubState={sub_state}",
            "FragmentPath=/tmp/autoclaw.service",
        ]
    )
    script_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from pathlib import Path",
                "import sys",
                f"log_path = Path({str(log_path)!r})",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "args = sys.argv[1:]",
                "if args and args[0] == '--user':",
                "    args = args[1:]",
                "if args and args[0] == 'show':",
                f"    sys.stdout.write({show_output!r} + '\\n')",
                "sys.exit(0)",
            ]
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
