from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, make_url

from app.cli_commands.openclaw_support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli_support import coerce_path, command_env, print_json
from app.config import OpenClawSettings, RuntimeSettings, load_settings
from app.db.session import (
    dispose_db_engine,
    ensure_database_schema,
    get_session_factory,
    ping_database,
)
from app.paths import default_data_dir, default_database_url, ensure_runtime_dirs
from app.registry import seed_definition_registry
from app.runtime.openclaw.host_setup import AUTOCLAW_OPERATOR_AGENT_ID, AUTOCLAW_WORKER_AGENT_ID


@dataclass(frozen=True)
class DatabaseRepairResult:
    repaired: bool
    backup_path: str
    migrated_tables: tuple[str, ...]
    skipped_tables: tuple[str, ...]


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Path):
        return json.dumps(str(value))
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))


def _config_sections_to_text(payload: dict[str, dict[str, Any]]) -> str:
    section_order = (
        "paths",
        "database",
        "server",
        "logging",
        "security",
        "openclaw",
        "runtime",
    )
    ordered_sections = [
        section for section in section_order if isinstance(payload.get(section), dict)
    ]
    ordered_sections.extend(
        section
        for section in payload
        if section not in ordered_sections and isinstance(payload[section], dict)
    )

    lines: list[str] = []
    for section in ordered_sections:
        values = payload[section]
        rendered_values = [
            (key, value) for key, value in values.items() if value is not None and value != ""
        ]
        if not rendered_values:
            continue
        lines.append(f"[{section}]")
        for key, value in rendered_values:
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def settings_to_config_text(
    *,
    data_dir: Path,
    database_url: str,
    host: str,
    port: int,
    log_level: str,
    api_key: str,
    internal_api_key: str,
) -> str:
    payload: dict[str, dict[str, Any]] = {
        "paths": {
            "data_dir": data_dir,
        },
        "database": {
            "url": database_url,
            "echo": False,
        },
        "server": {
            "host": host,
            "port": port,
            "console_origins": [
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ],
        },
        "logging": {
            "level": log_level,
        },
        "security": {
            "api_key": api_key,
            "internal_api_key": internal_api_key,
        },
        "openclaw": {
            "base_url": OpenClawSettings().base_url,
            "agent_id": AUTOCLAW_WORKER_AGENT_ID,
            "operator_agent_id": AUTOCLAW_OPERATOR_AGENT_ID,
            "timeout_ms": OpenClawSettings().timeout_ms,
        },
        "runtime": RuntimeSettings().model_dump(mode="json"),
    }
    return _config_sections_to_text(payload)


def update_config_sections(
    config_path: Path,
    *,
    section_updates: dict[str, dict[str, Any]],
) -> None:
    import tomllib

    if config_path.is_file():
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    else:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    for section, values in section_updates.items():
        existing = payload.get(section)
        next_values = dict(existing) if isinstance(existing, dict) else {}
        for key, value in values.items():
            if value is None or value == "":
                next_values.pop(key, None)
            else:
                next_values[key] = value
        if next_values:
            payload[section] = next_values
        else:
            payload.pop(section, None)
    config_path.write_text(
        _config_sections_to_text(
            {key: value for key, value in payload.items() if isinstance(value, dict)}
        ),
        encoding="utf-8",
    )


def sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    return Path(url.database).expanduser().resolve()


def ensure_sqlite_database(database_url: str) -> Path | None:
    database_path = sqlite_database_path(database_url)
    if database_path is None:
        return None
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(exist_ok=True)
    return database_path


def reset_sqlite_database(database_url: str) -> Path:
    database_path = sqlite_database_path(database_url)
    if database_path is None:
        raise ValueError("db reset only supports sqlite URLs during Phase 0.5")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    database_path.touch()
    return database_path


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
    from app.db import RuntimeBase

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


def _postgres_backup_schema_name(connection: Connection, base_name: str = "autoclaw_legacy") -> str:
    existing = {str(name) for name in inspect(connection).get_schema_names()}
    candidate = base_name
    suffix = 1
    while candidate in existing:
        candidate = f"{base_name}_{suffix}"
        suffix += 1
    return candidate


def _postgres_quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


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
        quoted_columns = ", ".join(_postgres_quote_identifier(name) for name in shared_columns)
        insert_target = f"public.{_postgres_quote_identifier(table_name)}"
        select_source = (
            f"{_postgres_quote_identifier(backup_schema)}.{_postgres_quote_identifier(table_name)}"
        )
        connection.execute(
            text(
                " ".join(
                    [
                        f"INSERT INTO {insert_target} ({quoted_columns})",
                        f"SELECT {quoted_columns}",
                        f"FROM {select_source}",
                        "ON CONFLICT DO NOTHING",
                    ]
                )
            )
        )
    return migrated_tables, skipped_tables


async def _repair_postgres_legacy_schema(database_url: str) -> DatabaseRepairResult:
    from app.db import RuntimeBase
    from app.db.session import get_async_engine

    engine = get_async_engine()
    async with engine.begin() as connection:
        backup_schema = await connection.run_sync(_postgres_backup_schema_name)
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
    await dispose_db_engine()
    return DatabaseRepairResult(
        repaired=True,
        backup_path=backup_schema,
        migrated_tables=tuple(migrated_tables),
        skipped_tables=tuple(sorted(set(skipped_tables))),
    )


async def ensure_database_ready(database_url: str) -> None:
    ensure_sqlite_database(database_url)
    await ping_database()
    await ensure_database_schema()
    async with get_session_factory()() as session:
        await seed_definition_registry(session)
        await session.commit()
    await dispose_db_engine()


async def ensure_database_ready_with_legacy_sqlite_repair(
    database_url: str,
) -> DatabaseRepairResult | None:
    try:
        await ensure_database_ready(database_url)
        return None
    except RuntimeError as exc:
        if not _schema_reset_required(exc):
            raise
        database_path = sqlite_database_path(database_url)
        if database_path is None:
            return await _repair_postgres_legacy_schema(database_url)

    await dispose_db_engine()
    backup_path = await asyncio.to_thread(_sqlite_backup_path, database_path)
    await asyncio.to_thread(shutil.copy2, database_path, backup_path)
    await asyncio.to_thread(reset_sqlite_database, database_url)
    await ensure_database_ready(database_url)
    migrated_tables, skipped_tables = await asyncio.to_thread(
        _copy_sqlite_legacy_data,
        database_path,
        backup_path,
    )
    await dispose_db_engine()
    return DatabaseRepairResult(
        repaired=True,
        backup_path=str(backup_path),
        migrated_tables=tuple(migrated_tables),
        skipped_tables=tuple(skipped_tables),
    )


async def cmd_init(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    data_dir = coerce_path(args.data_dir or default_data_dir())
    database_url = args.database_url or default_database_url(data_dir)
    api_key = args.api_key or secrets.token_urlsafe(24)
    internal_api_key = args.internal_api_key or secrets.token_urlsafe(24)

    if config_path.exists() and not args.force:
        raise FileExistsError(
            f"Refusing to overwrite existing config without --force: {config_path}"
        )

    ensure_runtime_dirs(config_dir=config_path.parent, data_dir=data_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        settings_to_config_text(
            data_dir=data_dir,
            database_url=database_url,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            api_key=api_key,
            internal_api_key=internal_api_key,
        ),
        encoding="utf-8",
    )

    with command_env(
        config_path=config_path,
        data_dir=data_dir,
        database_url=database_url,
        api_host=args.host,
        api_port=args.port,
        log_level=args.log_level,
        api_key=api_key,
        internal_api_key=internal_api_key,
    ):
        if not args.skip_db_upgrade:
            await ensure_database_ready(database_url)

    payload = {
        "ok": True,
        "config_path": str(config_path),
        "data_dir": str(data_dir),
        "database_url": database_url,
    }
    if args.json:
        print_json(payload)
    else:
        print(f"Initialized config at {config_path}")
    return 0


def cmd_db_upgrade(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
        asyncio.run(ensure_database_ready(settings.database_url))
    return 0


async def cmd_db_reset(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
        await dispose_db_engine()
        await asyncio.to_thread(reset_sqlite_database, settings.database_url)
        await ensure_database_ready(settings.database_url)

    payload = {
        "ok": True,
        "database_url": settings.database_url,
    }
    if args.json:
        print_json(payload)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    preflight = collect_openclaw_preflight(config_path=config_path)
    if preflight.host_state.support_status != "supported":
        return emit_openclaw_preflight_failure(
            command_name="AutoClaw serve",
            args=args,
            openclaw_payload=preflight.payload,
            stopped_before="stopped before API startup",
        )
    with command_env(config_path=config_path):
        settings = load_settings()
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            reload=False,
        )
    return 0


__all__ = [
    "DatabaseRepairResult",
    "cmd_db_reset",
    "cmd_db_upgrade",
    "cmd_init",
    "cmd_serve",
    "ensure_database_ready",
    "ensure_database_ready_with_legacy_sqlite_repair",
    "ensure_sqlite_database",
    "reset_sqlite_database",
    "settings_to_config_text",
    "sqlite_database_path",
    "update_config_sections",
]
