from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

_CONTROL_API_ACTOR_REF = "control_api"
_CONTROLLER_EVENT_SOURCE = "controller"
_CONTROL_API_EVENT_SOURCE = "control_api"
_TASK_CANCELLED_SUMMARY = "command run cancelled because the task was cancelled"
_TERMINAL_COMMAND_RUN_STATES = {"succeeded", "failed", "timed_out", "cancelled"}
_HUMAN_REQUEST_POLICY_BASIS_BY_RESOLUTION_KIND = {
    "answered": "task_authorized_human_request_resolution",
    "timed_out": "human_request_timeout_default_behavior",
    "cancelled": "task_cancelled",
}
_HUMAN_REQUEST_NOTE_BY_RESOLUTION_KIND = {
    "timed_out": "human request timed out before a human answered",
    "cancelled": "human request cancelled because the task was cancelled",
}


def copy_sqlite_runtime_terminal_table(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    build_row: Callable[[sqlite3.Row, list[str]], tuple[Any, ...]],
) -> None:
    _copy_sqlite_runtime_terminal_table(
        connection,
        table_name=table_name,
        build_row=build_row,
    )


def sqlite_pending_human_request_row(
    row: sqlite3.Row,
    current_columns: list[str],
) -> tuple[Any, ...]:
    return _sqlite_pending_human_request_row(row, current_columns)


def sqlite_command_run_row(
    row: sqlite3.Row,
    current_columns: list[str],
) -> tuple[Any, ...]:
    return _sqlite_command_run_row(row, current_columns)


def copy_postgres_runtime_terminal_table(
    connection: Connection,
    *,
    backup_schema: str,
    table_name: str,
    build_row: Callable[[Mapping[str, Any], list[str]], tuple[Any, ...]],
) -> None:
    _copy_postgres_runtime_terminal_table(
        connection,
        backup_schema=backup_schema,
        table_name=table_name,
        build_row=build_row,
    )


def postgres_pending_human_request_row(
    row: Mapping[str, Any],
    current_columns: list[str],
) -> tuple[Any, ...]:
    return _postgres_pending_human_request_row(row, current_columns)


def postgres_command_run_row(
    row: Mapping[str, Any],
    current_columns: list[str],
) -> tuple[Any, ...]:
    return _postgres_command_run_row(row, current_columns)


def _quote_sqlite_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _postgres_quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _row_has_key(row: sqlite3.Row | Mapping[str, Any], key: str) -> bool:
    return key in row.keys()


def _row_value(row: sqlite3.Row | Mapping[str, Any], key: str) -> Any | None:
    if not _row_has_key(row, key):
        return None
    return row[key]


def _row_text(row: sqlite3.Row | Mapping[str, Any], key: str) -> str | None:
    value = _row_value(row, key)
    if value is None:
        return None
    return str(value)


def _legacy_human_request_resolved_by_surface(
    row: sqlite3.Row | Mapping[str, Any],
) -> str | None:
    existing = _row_text(row, "resolved_by_surface")
    if existing is not None:
        return existing
    resolution_kind = _row_text(row, "resolution_kind")
    if resolution_kind is None:
        return None
    if _row_text(row, "resolved_by_actor_ref") == _CONTROL_API_ACTOR_REF:
        return _CONTROL_API_EVENT_SOURCE
    return _CONTROLLER_EVENT_SOURCE


def _legacy_human_request_resolved_by_actor_ref(
    row: sqlite3.Row | Mapping[str, Any],
) -> str | None:
    existing = _row_text(row, "resolved_by_actor_ref")
    if existing is None:
        return None
    if existing == _CONTROL_API_ACTOR_REF and not _row_has_key(row, "resolved_by_surface"):
        return None
    return existing


def _legacy_human_request_policy_basis(row: sqlite3.Row | Mapping[str, Any]) -> str | None:
    existing = _row_text(row, "resolution_policy_basis")
    if existing is not None:
        return existing
    resolution_kind = _row_text(row, "resolution_kind")
    if resolution_kind is None:
        return None
    return _HUMAN_REQUEST_POLICY_BASIS_BY_RESOLUTION_KIND.get(resolution_kind)


def _legacy_human_request_note(row: sqlite3.Row | Mapping[str, Any]) -> str | None:
    if _row_has_key(row, "resolution_note"):
        return _row_text(row, "resolution_note")
    resolution_kind = _row_text(row, "resolution_kind")
    if resolution_kind is None:
        return None
    return _HUMAN_REQUEST_NOTE_BY_RESOLUTION_KIND.get(resolution_kind)


def _legacy_command_run_terminal_event_source(
    row: sqlite3.Row | Mapping[str, Any],
) -> str | None:
    existing = _row_text(row, "terminal_event_source")
    if existing is not None:
        return existing
    if _row_text(row, "state") not in _TERMINAL_COMMAND_RUN_STATES:
        return None
    if _row_text(row, "terminal_actor_ref") == _CONTROL_API_ACTOR_REF:
        return _CONTROL_API_EVENT_SOURCE
    if _row_text(row, "terminal_summary") == _TASK_CANCELLED_SUMMARY:
        return _CONTROL_API_EVENT_SOURCE
    return _CONTROLLER_EVENT_SOURCE


def _legacy_command_run_terminal_actor_ref(
    row: sqlite3.Row | Mapping[str, Any],
) -> str | None:
    existing = _row_text(row, "terminal_actor_ref")
    if existing is not None:
        if existing == _CONTROL_API_ACTOR_REF and not _row_has_key(row, "terminal_event_source"):
            return None
        return existing
    return None


def _current_sqlite_column_names(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:
    return [
        str(row[1])
        for row in connection.execute(
            f"PRAGMA main.table_info({_quote_sqlite_identifier(table_name)})"
        ).fetchall()
    ]


def _copy_sqlite_runtime_terminal_table(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    build_row: Callable[[sqlite3.Row, list[str]], tuple[Any, ...]],
) -> None:
    current_columns = _current_sqlite_column_names(connection, table_name)
    quoted_columns = ", ".join(_quote_sqlite_identifier(name) for name in current_columns)
    placeholders = ", ".join("?" for _ in current_columns)
    rows = list(
        connection.execute(
            f"SELECT * FROM legacy.{_quote_sqlite_identifier(table_name)}"
        ).fetchall()
    )
    if not rows:
        return
    connection.executemany(
        " ".join(
            [
                f"INSERT INTO main.{_quote_sqlite_identifier(table_name)}",
                f"({quoted_columns})",
                f"VALUES ({placeholders})",
            ]
        ),
        [build_row(row, current_columns) for row in rows],
    )


def _sqlite_pending_human_request_row(
    row: sqlite3.Row,
    current_columns: list[str],
) -> tuple[Any, ...]:
    values: list[Any] = []
    for column_name in current_columns:
        if column_name == "resolved_by_actor_ref":
            values.append(_legacy_human_request_resolved_by_actor_ref(row))
            continue
        if _row_has_key(row, column_name):
            values.append(row[column_name])
            continue
        if column_name == "resolved_by_surface":
            values.append(_legacy_human_request_resolved_by_surface(row))
            continue
        if column_name == "resolution_policy_basis":
            values.append(_legacy_human_request_policy_basis(row))
            continue
        if column_name == "resolution_note":
            values.append(_legacy_human_request_note(row))
            continue
        values.append(None)
    return tuple(values)


def _sqlite_command_run_row(
    row: sqlite3.Row,
    current_columns: list[str],
) -> tuple[Any, ...]:
    values: list[Any] = []
    for column_name in current_columns:
        if column_name == "terminal_actor_ref":
            values.append(_legacy_command_run_terminal_actor_ref(row))
            continue
        if _row_has_key(row, column_name):
            values.append(row[column_name])
            continue
        if column_name == "terminal_event_source":
            values.append(_legacy_command_run_terminal_event_source(row))
            continue
        if column_name == "terminal_actor_ref":
            values.append(_legacy_command_run_terminal_actor_ref(row))
            continue
        values.append(None)
    return tuple(values)


def _postgres_current_column_names(connection: Connection, table_name: str) -> list[str]:
    from sqlalchemy import inspect

    return [
        str(column["name"])
        for column in inspect(connection).get_columns(table_name)
        if column.get("name")
    ]


def _copy_postgres_runtime_terminal_table(
    connection: Connection,
    *,
    backup_schema: str,
    table_name: str,
    build_row: Callable[[Mapping[str, Any], list[str]], tuple[Any, ...]],
) -> None:
    current_columns = _postgres_current_column_names(connection, table_name)
    rows = list(
        connection.execute(
            text(f'SELECT * FROM "{backup_schema}".{_postgres_quote_identifier(table_name)}')
        ).mappings()
    )
    if not rows:
        return
    quoted_columns = ", ".join(_postgres_quote_identifier(name) for name in current_columns)
    parameter_names = [f"value_{index}" for index in range(len(current_columns))]
    placeholders = ", ".join(f":{name}" for name in parameter_names)
    insert_statement = text(
        " ".join(
            [
                f"INSERT INTO public.{_postgres_quote_identifier(table_name)}",
                f"({quoted_columns})",
                f"VALUES ({placeholders})",
            ]
        )
    )
    for row in rows:
        values = build_row(row, current_columns)
        connection.execute(
            insert_statement,
            {
                parameter_name: value
                for parameter_name, value in zip(parameter_names, values, strict=True)
            },
        )


def _postgres_pending_human_request_row(
    row: Mapping[str, Any],
    current_columns: list[str],
) -> tuple[Any, ...]:
    values: list[Any] = []
    for column_name in current_columns:
        if column_name == "resolved_by_actor_ref":
            values.append(_legacy_human_request_resolved_by_actor_ref(row))
            continue
        if _row_has_key(row, column_name):
            values.append(row[column_name])
            continue
        if column_name == "resolved_by_surface":
            values.append(_legacy_human_request_resolved_by_surface(row))
            continue
        if column_name == "resolution_policy_basis":
            values.append(_legacy_human_request_policy_basis(row))
            continue
        if column_name == "resolution_note":
            values.append(_legacy_human_request_note(row))
            continue
        values.append(None)
    return tuple(values)


def _postgres_command_run_row(
    row: Mapping[str, Any],
    current_columns: list[str],
) -> tuple[Any, ...]:
    values: list[Any] = []
    for column_name in current_columns:
        if column_name == "terminal_actor_ref":
            values.append(_legacy_command_run_terminal_actor_ref(row))
            continue
        if _row_has_key(row, column_name):
            values.append(row[column_name])
            continue
        if column_name == "terminal_event_source":
            values.append(_legacy_command_run_terminal_event_source(row))
            continue
        if column_name == "terminal_actor_ref":
            values.append(_legacy_command_run_terminal_actor_ref(row))
            continue
        values.append(None)
    return tuple(values)


__all__ = [
    "copy_postgres_runtime_terminal_table",
    "copy_sqlite_runtime_terminal_table",
    "postgres_command_run_row",
    "postgres_pending_human_request_row",
    "sqlite_command_run_row",
    "sqlite_pending_human_request_row",
]
