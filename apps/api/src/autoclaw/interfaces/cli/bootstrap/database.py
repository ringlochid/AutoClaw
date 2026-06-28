from __future__ import annotations

import asyncio
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, make_url

from autoclaw.definitions.registry import seed_definition_registry
from autoclaw.interfaces.cli.bootstrap.legacy_copy import (
    copy_postgres_runtime_terminal_table,
    copy_sqlite_runtime_terminal_table,
    postgres_command_run_row,
    postgres_pending_human_request_row,
    sqlite_command_run_row,
    sqlite_pending_human_request_row,
)
from autoclaw.interfaces.cli.bootstrap.postgres_repair import (
    postgres_backup_schema_name,
    postgres_constraint_with_not_valid,
    postgres_quote_identifier,
    postgres_rebound_constraint_definition,
)
from autoclaw.interfaces.cli.progress import CliProgress
from autoclaw.persistence.session import (
    dispose_db_engine,
    ensure_database_schema,
    get_session_factory,
    ping_database,
)


@dataclass(frozen=True)
class DatabaseRepairResult:
    is_repaired: bool
    backup_path: str
    migrated_tables: tuple[str, ...]
    skipped_tables: tuple[str, ...]


async def ensure_database_ready_with_legacy_sqlite_repair(
    database_url: str,
    *,
    progress: CliProgress | None = None,
) -> DatabaseRepairResult | None:
    try:
        await ensure_database_ready(database_url, progress=progress)
        return None
    except RuntimeError as exc:
        if not _schema_reset_required(exc):
            raise
        database_path = sqlite_database_path(database_url)
        if database_path is None:
            if progress is not None:
                progress.warn("database", "Repairing legacy PostgreSQL schema")
            return await _repair_postgres_legacy_schema(database_url)

    await dispose_db_engine()
    if progress is not None:
        progress.warn("database", "Legacy SQLite schema needs repair")
    backup_path = await asyncio.to_thread(_sqlite_backup_path, database_path)
    if progress is not None:
        progress.step("database", f"Backing up legacy SQLite database to {backup_path}")
    await asyncio.to_thread(shutil.copy2, database_path, backup_path)
    if progress is not None:
        progress.step("database", "Recreating SQLite database")
    await asyncio.to_thread(reset_sqlite_database, database_url)
    await ensure_database_ready(database_url, progress=progress)
    if progress is not None:
        progress.step("database", "Copying compatible legacy rows")
    migrated_tables, skipped_tables = await asyncio.to_thread(
        _copy_sqlite_legacy_data,
        database_path,
        backup_path,
    )
    await dispose_db_engine()
    return DatabaseRepairResult(
        is_repaired=True,
        backup_path=str(backup_path),
        migrated_tables=tuple(migrated_tables),
        skipped_tables=tuple(skipped_tables),
    )


async def ensure_database_ready(
    database_url: str,
    *,
    progress: CliProgress | None = None,
) -> None:
    if progress is not None:
        progress.step("database", "Ensuring database file")
    ensure_sqlite_database(database_url)
    if progress is not None:
        progress.step("database", "Checking database connection")
    await ping_database()
    if progress is not None:
        progress.step("database", "Applying database schema")
    await ensure_database_schema()
    rebound_constraints = await _repair_postgres_public_foreign_keys_if_needed(database_url)
    if rebound_constraints and progress is not None:
        progress.step(
            "database",
            f"Rebound {len(rebound_constraints)} legacy PostgreSQL foreign keys",
        )
    async with get_session_factory()() as session:
        if progress is not None:
            progress.step("seed", "Seeding packaged definitions")
        await seed_definition_registry(session)
        await session.commit()
    await dispose_db_engine()
    if progress is not None:
        progress.done("database", "Database ready")


def reset_sqlite_database(database_url: str) -> Path:
    database_path = sqlite_database_path(database_url)
    if database_path is None:
        raise ValueError("db reset only supports sqlite URLs on the local runtime path")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    database_path.touch()
    return database_path


def ensure_sqlite_database(database_url: str) -> Path | None:
    database_path = sqlite_database_path(database_url)
    if database_path is None:
        return None
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(exist_ok=True)
    return database_path


def sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    return Path(url.database).expanduser().resolve()


def _schema_reset_required(exc: RuntimeError) -> bool:
    message = str(exc)
    return "cannot be upgraded in place" in message and "autoclaw db reset" in message


def _sqlite_backup_path(database_path: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = database_path.with_name(f"{database_path.name}.backup-{timestamp}")
    suffix = 1
    while candidate.exists():
        candidate = database_path.with_name(f"{database_path.name}.backup-{timestamp}-{suffix}")
        suffix += 1
    return candidate


def _quote_sqlite_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sqlite_table_names(connection: sqlite3.Connection, schema: str) -> set[str]:
    rows = connection.execute(
        f"SELECT name FROM {schema}.sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _table_names(connection: Connection) -> set[str]:
    return {str(table_name) for table_name in inspect(connection).get_table_names()}


def _column_names(connection: Connection, table_name: str) -> set[str]:
    return {
        str(column["name"])
        for column in inspect(connection).get_columns(table_name)
        if column.get("name")
    }


def _required_schema_columns() -> dict[str, set[str]]:
    from autoclaw.persistence import RuntimeBase

    return {
        table_name: {str(column.name) for column in table.columns}
        for table_name, table in RuntimeBase.metadata.tables.items()
    }


def _sqlite_table_info(
    connection: sqlite3.Connection,
    schema: str,
    table_name: str,
) -> list[sqlite3.Row]:
    return connection.execute(
        f"PRAGMA {schema}.table_info({_quote_sqlite_identifier(table_name)})"
    ).fetchall()


def _sqlite_foreign_key_targets(
    connection: sqlite3.Connection,
    schema: str,
    table_name: str,
) -> set[str]:
    rows = connection.execute(
        f"PRAGMA {schema}.foreign_key_list({_quote_sqlite_identifier(table_name)})"
    ).fetchall()
    return {str(row[2]) for row in rows if row[2]}


def _sqlite_copyable_tables(connection: sqlite3.Connection) -> tuple[list[str], list[str]]:
    current_tables = _sqlite_table_names(connection, "main")
    legacy_tables = _sqlite_table_names(connection, "legacy")
    intersection = sorted(current_tables & legacy_tables)
    copyable: set[str] = set()
    skipped: set[str] = set()

    for table_name in intersection:
        current_info = _sqlite_table_info(connection, "main", table_name)
        legacy_info = _sqlite_table_info(connection, "legacy", table_name)
        current_columns = {str(row[1]): row for row in current_info}
        legacy_columns = {str(row[1]): row for row in legacy_info}
        shared_columns = [name for name in current_columns if name in legacy_columns]
        missing_required = [
            name
            for name, row in current_columns.items()
            if name not in legacy_columns
            and (int(row[3]) == 1 or int(row[5]) > 0)
            and row[4] is None
        ]
        if shared_columns and not missing_required:
            copyable.add(table_name)
        else:
            skipped.add(table_name)

    changed = True
    while changed:
        changed = False
        for table_name in tuple(copyable):
            referenced_tables = {
                target
                for target in _sqlite_foreign_key_targets(connection, "main", table_name)
                if target != table_name
            }
            if referenced_tables - copyable:
                copyable.remove(table_name)
                skipped.add(table_name)
                changed = True

    skipped.update((current_tables & legacy_tables) - copyable)
    return sorted(copyable), sorted(skipped)


def _copy_sqlite_legacy_data(database_path: Path, backup_path: Path) -> tuple[list[str], list[str]]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("ATTACH DATABASE ? AS legacy", (str(backup_path),))
        connection.execute("PRAGMA foreign_keys = OFF")
        migrated_tables, skipped_tables = _sqlite_copyable_tables(connection)
        for table_name in migrated_tables:
            if table_name == "pending_human_requests":
                copy_sqlite_runtime_terminal_table(
                    connection,
                    table_name=table_name,
                    build_row=sqlite_pending_human_request_row,
                )
                continue
            if table_name == "command_runs":
                copy_sqlite_runtime_terminal_table(
                    connection,
                    table_name=table_name,
                    build_row=sqlite_command_run_row,
                )
                continue
            current_info = _sqlite_table_info(connection, "main", table_name)
            legacy_info = _sqlite_table_info(connection, "legacy", table_name)
            legacy_columns = {str(row[1]) for row in legacy_info}
            shared_columns = [str(row[1]) for row in current_info if str(row[1]) in legacy_columns]
            quoted_columns = ", ".join(_quote_sqlite_identifier(name) for name in shared_columns)
            connection.execute(
                " ".join(
                    [
                        f"INSERT OR IGNORE INTO main.{_quote_sqlite_identifier(table_name)}",
                        f"({quoted_columns})",
                        f"SELECT {quoted_columns}",
                        f"FROM legacy.{_quote_sqlite_identifier(table_name)}",
                    ]
                )
            )
        connection.commit()
        connection.execute("DETACH DATABASE legacy")
    return migrated_tables, skipped_tables


def _postgres_missing_columns(connection: Connection) -> dict[str, list[str]]:
    actual_tables = _table_names(connection)
    missing: dict[str, list[str]] = {}
    for table_name, expected_columns in sorted(_required_schema_columns().items()):
        if table_name not in actual_tables:
            continue
        actual_columns = _column_names(connection, table_name)
        missing_columns = sorted(expected_columns - actual_columns)
        if missing_columns:
            missing[table_name] = missing_columns
    return missing


def _postgres_rebind_public_foreign_keys(
    connection: Connection,
    backup_schema: str,
) -> tuple[str, ...]:
    rows = connection.execute(
        text(
            """
            SELECT t.relname, c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE c.contype = 'f'
              AND n.nspname = 'public'
            ORDER BY t.relname, c.conname
            """
        )
    ).all()
    rebound_constraints: list[str] = []
    for table_name, constraint_name, definition in rows:
        rebound_definition = postgres_rebound_constraint_definition(
            str(definition),
            backup_schema,
        )
        if rebound_definition == definition:
            continue
        quoted_table = postgres_quote_identifier(str(table_name))
        quoted_constraint = postgres_quote_identifier(str(constraint_name))
        connection.execute(
            text(
                " ".join(
                    [
                        f"ALTER TABLE public.{quoted_table}",
                        f"DROP CONSTRAINT {quoted_constraint}",
                    ]
                )
            )
        )
        connection.execute(
            text(
                " ".join(
                    [
                        f"ALTER TABLE public.{quoted_table}",
                        f"ADD CONSTRAINT {quoted_constraint}",
                        postgres_constraint_with_not_valid(rebound_definition),
                    ]
                )
            )
        )
        rebound_constraints.append(f"{table_name}.{constraint_name}")
    return tuple(rebound_constraints)


async def _repair_postgres_public_foreign_keys_if_needed(database_url: str) -> tuple[str, ...]:
    if sqlite_database_path(database_url) is not None:
        return ()

    from autoclaw.persistence.session import get_async_engine

    engine = get_async_engine()
    async with engine.begin() as connection:
        schema_names = await connection.run_sync(
            lambda sync_connection: set(inspect(sync_connection).get_schema_names())
        )
        backup_schemas = sorted(
            schema_name
            for schema_name in schema_names
            if schema_name == "autoclaw_legacy" or schema_name.startswith("autoclaw_legacy_")
        )
        rebound_constraints: list[str] = []
        for backup_schema in backup_schemas:
            rebound_constraints.extend(
                await connection.run_sync(
                    _postgres_rebind_public_foreign_keys,
                    backup_schema,
                )
            )
    return tuple(rebound_constraints)


def _postgres_fk_validity_predicates(
    connection: Connection,
    *,
    table_name: str,
    source_alias: str,
    backup_columns: set[str],
) -> list[str]:
    predicates: list[str] = []
    for foreign_key in inspect(connection).get_foreign_keys(table_name):
        referred_table = foreign_key.get("referred_table")
        constrained_columns = [str(column) for column in foreign_key.get("constrained_columns", ())]
        referred_columns = [str(column) for column in foreign_key.get("referred_columns", ())]
        if (
            not referred_table
            or not constrained_columns
            or len(constrained_columns) != len(referred_columns)
            or any(column not in backup_columns for column in constrained_columns)
        ):
            continue
        source_null_checks = [
            f"{source_alias}.{postgres_quote_identifier(column)} IS NULL"
            for column in constrained_columns
        ]
        target_matches = [
            " = ".join(
                [
                    f"target.{postgres_quote_identifier(referred_column)}",
                    f"{source_alias}.{postgres_quote_identifier(constrained_column)}",
                ]
            )
            for constrained_column, referred_column in zip(
                constrained_columns,
                referred_columns,
                strict=True,
            )
        ]
        predicates.append(
            " OR ".join(
                [
                    *source_null_checks,
                    (
                        "EXISTS ("
                        f"SELECT 1 FROM public.{postgres_quote_identifier(str(referred_table))} "
                        f"AS target WHERE {' AND '.join(target_matches)}"
                        ")"
                    ),
                ]
            )
        )
    return predicates


def _postgres_copyable_tables(
    connection: Connection,
    backup_schema: str,
) -> tuple[list[str], list[str]]:
    current_tables = _table_names(connection)
    backup_tables = {
        str(table_name) for table_name in inspect(connection).get_table_names(schema=backup_schema)
    }
    intersection = sorted(current_tables & backup_tables)
    copyable: set[str] = set()
    skipped: set[str] = set()

    for table_name in intersection:
        current_columns = {
            str(column["name"]): column
            for column in inspect(connection).get_columns(table_name)
            if column.get("name")
        }
        backup_columns = {
            str(column["name"]): column
            for column in inspect(connection).get_columns(table_name, schema=backup_schema)
            if column.get("name")
        }
        shared_columns = [name for name in current_columns if name in backup_columns]
        missing_required = [
            name
            for name, column in current_columns.items()
            if name not in backup_columns
            and not bool(column.get("nullable", True))
            and column.get("default") is None
            and not bool(column.get("autoincrement", False))
        ]
        if shared_columns and not missing_required:
            copyable.add(table_name)
        else:
            skipped.add(table_name)

    skipped.update((current_tables & backup_tables) - copyable)
    return sorted(copyable), sorted(skipped)


def _copy_postgres_legacy_data(
    connection: Connection,
    backup_schema: str,
) -> tuple[list[str], list[str]]:
    migrated_tables, skipped_tables = _postgres_copyable_tables(connection, backup_schema)
    for table_name in migrated_tables:
        if table_name == "pending_human_requests":
            copy_postgres_runtime_terminal_table(
                connection,
                backup_schema=backup_schema,
                table_name=table_name,
                build_row=postgres_pending_human_request_row,
            )
            continue
        if table_name == "command_runs":
            copy_postgres_runtime_terminal_table(
                connection,
                backup_schema=backup_schema,
                table_name=table_name,
                build_row=postgres_command_run_row,
            )
            continue
        current_columns = {
            str(column["name"])
            for column in inspect(connection).get_columns(table_name)
            if column.get("name")
        }
        backup_columns = {
            str(column["name"])
            for column in inspect(connection).get_columns(table_name, schema=backup_schema)
            if column.get("name")
        }
        shared_columns = [name for name in current_columns if name in backup_columns]
        quoted_columns = ", ".join(postgres_quote_identifier(name) for name in shared_columns)
        insert_target = f"public.{postgres_quote_identifier(table_name)}"
        source_alias = "legacy_source"
        select_source = " ".join(
            [
                f"{postgres_quote_identifier(backup_schema)}.{postgres_quote_identifier(table_name)}",
                f"AS {source_alias}",
            ]
        )
        fk_predicates = _postgres_fk_validity_predicates(
            connection,
            table_name=table_name,
            source_alias=source_alias,
            backup_columns=backup_columns,
        )
        where_clause = (
            "WHERE " + " AND ".join(f"({predicate})" for predicate in fk_predicates)
            if fk_predicates
            else ""
        )
        connection.execute(
            text(
                " ".join(
                    [
                        f"INSERT INTO {insert_target} ({quoted_columns})",
                        f"SELECT {quoted_columns}",
                        f"FROM {select_source}",
                        where_clause,
                        "ON CONFLICT DO NOTHING",
                    ]
                )
            )
        )
    return migrated_tables, skipped_tables


async def _repair_postgres_legacy_schema(database_url: str) -> DatabaseRepairResult:
    from autoclaw.persistence import RuntimeBase
    from autoclaw.persistence.session import get_async_engine

    engine = get_async_engine()
    async with engine.begin() as connection:
        backup_schema = await connection.run_sync(postgres_backup_schema_name)
        missing_columns = await connection.run_sync(_postgres_missing_columns)
        existing_tables = await connection.run_sync(_table_names)
        moved_tables = sorted(
            table_name for table_name in missing_columns if table_name in existing_tables
        )
        if not moved_tables:
            raise RuntimeError("legacy Postgres schema repair requested without movable tables")
        await connection.execute(text(f'CREATE SCHEMA "{backup_schema}"'))
        for table_name in moved_tables:
            await connection.execute(
                text(f'ALTER TABLE public."{table_name}" SET SCHEMA "{backup_schema}"')
            )
        await connection.run_sync(RuntimeBase.metadata.create_all)
        migrated_tables, skipped_tables = await connection.run_sync(
            _copy_postgres_legacy_data,
            backup_schema,
        )
        await connection.run_sync(_postgres_rebind_public_foreign_keys, backup_schema)
    await dispose_db_engine()
    return DatabaseRepairResult(
        is_repaired=True,
        backup_path=backup_schema,
        migrated_tables=tuple(migrated_tables),
        skipped_tables=tuple(sorted(set(skipped_tables))),
    )


__all__ = [
    "DatabaseRepairResult",
    "ensure_database_ready",
    "ensure_database_ready_with_legacy_sqlite_repair",
    "ensure_sqlite_database",
    "reset_sqlite_database",
    "sqlite_database_path",
]
