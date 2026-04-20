from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_fresh_schema_uses_partial_unique_binding_indexes_for_sqlite(
    test_engine: AsyncEngine,
) -> None:
    async with test_engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'task_resource_bindings'
                ORDER BY indexname
                """
            )
        )
        rows = result.fetchall()

    sql_by_name = {row[0]: row[1] for row in rows}

    for name, role in [
        ("uq_task_resource_bindings_primary_workspace", "primary_workspace"),
        ("uq_task_resource_bindings_primary_context", "primary_context"),
        ("uq_task_resource_bindings_manifest_root", "manifest_root"),
    ]:
        sql = sql_by_name.get(name)
        assert sql is not None
        assert role in sql
        assert "binding_role" in sql
