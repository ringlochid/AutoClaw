from __future__ import annotations

import sqlite3
from pathlib import Path


def test_fresh_schema_uses_partial_unique_binding_indexes_for_sqlite() -> None:
    db_path = Path('/home/ubuntu/.local/share/autoclaw/autoclaw.db')
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA index_list('task_resource_bindings')").fetchall()
        sql_by_name: dict[str, str | None] = {}
        for _, name, *_rest in rows:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                (name,),
            ).fetchone()
            sql_by_name[name] = row[0] if row else None

        for name, role in [
            ('uq_task_resource_bindings_primary_workspace', 'primary_workspace'),
            ('uq_task_resource_bindings_primary_context', 'primary_context'),
            ('uq_task_resource_bindings_manifest_root', 'manifest_root'),
        ]:
            sql = sql_by_name.get(name)
            assert sql is not None
            assert f"WHERE binding_role = '{role}'" in sql
    finally:
        conn.close()
