from __future__ import annotations

from collections.abc import AsyncIterator
from sqlite3 import Connection as SQLiteConnection
from typing import Any
from weakref import WeakSet

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.config import get_settings
from app.runtime.effects.queue import (
    apply_post_commit_actions,
    clear_post_commit_actions,
    pop_post_commit_actions,
)

_ENGINE_BY_LOOP: dict[int, AsyncEngine] = {}
_SESSION_FACTORY_BY_LOOP: dict[int, async_sessionmaker[AsyncSession]] = {}
_OPEN_SESSIONS_BY_LOOP: dict[int, WeakSet[RuntimeAsyncSession]] = {}
SchemaForeignKeySignature = tuple[tuple[str, ...], str, tuple[str, ...]]
REQUIRED_SCHEMA_FOREIGN_KEYS: dict[str, set[SchemaForeignKeySignature]] = {
    "workflow_definitions": {
        (
            ("workflow_key", "current_revision_no"),
            "workflow_revisions",
            ("workflow_key", "revision_no"),
        )
    },
    "role_definitions": {
        (("role_key", "current_revision_no"), "role_revisions", ("role_key", "revision_no"))
    },
    "policy_definitions": {
        (("policy_key", "current_revision_no"), "policy_revisions", ("policy_key", "revision_no"))
    },
    "task_composes": {
        (
            ("workflow_key", "workflow_revision_no"),
            "workflow_revisions",
            ("workflow_key", "revision_no"),
        )
    },
    "compiled_plans": {
        (
            ("workflow_key", "definition_revision_no"),
            "workflow_revisions",
            ("workflow_key", "revision_no"),
        )
    },
    "compiled_plan_nodes": {
        (
            ("compiled_plan_id", "parent_node_key"),
            "compiled_plan_nodes",
            ("compiled_plan_id", "node_key"),
        ),
        (("role_key", "role_revision_no"), "role_revisions", ("role_key", "revision_no")),
        (("policy_key", "policy_revision_no"), "policy_revisions", ("policy_key", "revision_no")),
    },
    "compiled_plan_edges": {
        (
            ("compiled_plan_id", "provider_node_key"),
            "compiled_plan_nodes",
            ("compiled_plan_id", "node_key"),
        ),
        (
            ("compiled_plan_id", "consumer_node_key"),
            "compiled_plan_nodes",
            ("compiled_plan_id", "node_key"),
        ),
    },
    "flows": {
        (("flow_id", "active_flow_revision_id"), "flow_revisions", ("flow_id", "flow_revision_id")),
        (("flow_id", "current_open_dispatch_id"), "dispatch_turns", ("flow_id", "dispatch_id")),
    },
    "flow_nodes": {
        (("flow_revision_id", "parent_node_key"), "flow_nodes", ("flow_revision_id", "node_key")),
        (("role_key", "role_revision_no"), "role_revisions", ("role_key", "revision_no")),
        (("policy_key", "policy_revision_no"), "policy_revisions", ("policy_key", "revision_no")),
        (
            ("current_assignment_id", "flow_node_id"),
            "assignments",
            ("assignment_id", "flow_node_id"),
        ),
    },
    "flow_edges": {
        (("flow_revision_id", "provider_node_key"), "flow_nodes", ("flow_revision_id", "node_key")),
        (("flow_revision_id", "consumer_node_key"), "flow_nodes", ("flow_revision_id", "node_key")),
    },
    "node_plan_revisions": {
        (("role_key", "role_revision_no"), "role_revisions", ("role_key", "revision_no")),
        (("policy_key", "policy_revision_no"), "policy_revisions", ("policy_key", "revision_no")),
    },
    "assignments": {
        (("current_attempt_id", "assignment_id"), "attempts", ("attempt_id", "assignment_id"))
    },
    "attempts": {
        (
            ("latest_checkpoint_id", "attempt_id"),
            "attempt_checkpoints",
            ("checkpoint_id", "attempt_id"),
        )
    },
}
REQUIRED_SCHEMA_INDEXES: dict[str, set[str]] = {
    "flows": {"ix_flows_status_updated_at"},
    "attempt_checkpoints": {"ix_attempt_checkpoints_attempt_recorded_at"},
    "dispatch_turns": {"ix_dispatch_turns_task_node_rendered_at"},
    "node_sessions": {"ix_node_sessions_session_key"},
}


class RuntimeAsyncSession(AsyncSession):
    _owner_loop_id: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owner_loop_id = _loop_id()
        _register_open_session(self)

    async def commit(self) -> None:
        staged_actions = self.info.pop("_pre_popped_post_commit_actions", None)
        if staged_actions is None:
            staged_actions = pop_post_commit_actions(self)
        await super().commit()
        # Local-tool-first contract: commit controller truth first, then apply the
        # owned task-root projections synchronously in the same request path.
        # We do not keep a durable replay queue for these post-commit writes.
        await apply_post_commit_actions(self, staged_actions)

    async def rollback(self) -> None:
        clear_post_commit_actions(self)
        await super().rollback()

    async def close(self) -> None:
        try:
            await super().close()
        finally:
            _discard_open_session(self)


def _loop_id() -> int:
    import asyncio

    return id(asyncio.get_running_loop())


def _register_open_session(session: RuntimeAsyncSession) -> None:
    _OPEN_SESSIONS_BY_LOOP.setdefault(_session_loop_id(session), WeakSet()).add(session)


def _discard_open_session(session: RuntimeAsyncSession) -> None:
    sessions = _OPEN_SESSIONS_BY_LOOP.get(_session_loop_id(session))
    if sessions is None:
        return
    sessions.discard(session)
    if not sessions:
        _OPEN_SESSIONS_BY_LOOP.pop(_session_loop_id(session), None)


def _session_loop_id(session: RuntimeAsyncSession) -> int:
    return session._owner_loop_id


def open_session_info_value_present(*, key: str, value: object) -> bool:
    sessions = _OPEN_SESSIONS_BY_LOOP.get(_loop_id())
    if sessions is None:
        return False
    return any(session.info.get(key) == value for session in tuple(sessions))


def notify_runtime_effect_runner() -> None:
    from app.runtime.effects import notify_runtime_effect_runner as _notify_runtime_effect_runner

    _notify_runtime_effect_runner()


def get_async_engine() -> AsyncEngine:
    settings = get_settings()
    loop_id = _loop_id()
    if loop_id not in _ENGINE_BY_LOOP:
        url = make_url(settings.database_url)
        engine_kwargs: dict[str, object] = {
            "echo": settings.database_echo,
        }
        if url.get_backend_name() == "sqlite":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if url.database in {None, "", ":memory:"}:
                engine_kwargs["poolclass"] = StaticPool
            else:
                engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_pre_ping"] = True

        engine = create_async_engine(
            settings.database_url,
            **engine_kwargs,
        )
        if url.get_backend_name() == "sqlite":

            @event.listens_for(engine.sync_engine, "connect")
            def _set_sqlite_pragma(
                dbapi_connection: SQLiteConnection,
                connection_record: object,
            ) -> None:
                del connection_record
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _ENGINE_BY_LOOP[loop_id] = engine
    return _ENGINE_BY_LOOP[loop_id]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    loop_id = _loop_id()
    if loop_id not in _SESSION_FACTORY_BY_LOOP:
        _SESSION_FACTORY_BY_LOOP[loop_id] = async_sessionmaker(
            bind=get_async_engine(),
            class_=RuntimeAsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SESSION_FACTORY_BY_LOOP[loop_id]


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def ping_database() -> None:
    async with get_session_factory()() as session:
        await session.execute(text("SELECT 1"))


async def verify_database_schema() -> None:
    engine = get_async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(_verify_database_schema_contract)


async def ensure_database_schema() -> None:
    from app.db import RuntimeBase

    engine = get_async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(RuntimeBase.metadata.create_all)
        await connection.run_sync(_verify_database_schema_contract)


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


def _missing_table_or_column_messages(connection: Connection) -> list[str]:
    missing: list[str] = []
    actual_tables = _table_names(connection)
    for table_name, expected_columns in sorted(_required_schema_columns().items()):
        if table_name not in actual_tables:
            missing.append(f"missing table {table_name}")
            continue
        actual_columns = _column_names(connection, table_name)
        for column_name in sorted(expected_columns - actual_columns):
            missing.append(f"{table_name} missing column {column_name}")
    return missing


def _foreign_key_signatures(
    connection: Connection,
    table_name: str,
) -> set[tuple[tuple[str, ...], str, tuple[str, ...]]]:
    signatures: set[tuple[tuple[str, ...], str, tuple[str, ...]]] = set()
    for foreign_key in inspect(connection).get_foreign_keys(table_name):
        signatures.add(
            (
                tuple(str(column) for column in foreign_key.get("constrained_columns") or []),
                str(foreign_key.get("referred_table")),
                tuple(str(column) for column in foreign_key.get("referred_columns") or []),
            )
        )
    return signatures


def _index_names(connection: Connection, table_name: str) -> set[str]:
    return {
        str(index["name"])
        for index in inspect(connection).get_indexes(table_name)
        if index.get("name")
    }


def _missing_foreign_key_messages(connection: Connection) -> list[str]:
    missing: list[str] = []
    actual_tables = _table_names(connection)
    for table_name, expected_targets in REQUIRED_SCHEMA_FOREIGN_KEYS.items():
        if table_name not in actual_tables:
            continue
        actual_targets = _foreign_key_signatures(connection, table_name)
        for constrained_columns, referred_table, referred_columns in sorted(expected_targets):
            if (constrained_columns, referred_table, referred_columns) in actual_targets:
                continue
            missing.append(
                f"{table_name} missing foreign key "
                f"{constrained_columns}->{referred_table}{referred_columns}"
            )
    return missing


def _missing_index_messages(connection: Connection) -> list[str]:
    missing: list[str] = []
    actual_tables = _table_names(connection)
    for table_name, expected_indexes in REQUIRED_SCHEMA_INDEXES.items():
        if table_name not in actual_tables:
            continue
        actual_indexes = _index_names(connection, table_name)
        for index_name in sorted(expected_indexes):
            if index_name in actual_indexes:
                continue
            missing.append(f"{table_name} missing index {index_name}")
    return missing


def _verify_database_schema_contract(connection: Connection) -> None:
    missing = _missing_table_or_column_messages(connection)
    missing.extend(_missing_foreign_key_messages(connection))
    missing.extend(_missing_index_messages(connection))
    if missing:
        joined = "; ".join(missing)
        raise RuntimeError(
            "existing database schema cannot be upgraded in place to the current "
            f"Phase 0-3 contract: {joined}. Run `autoclaw db reset`."
        )


async def dispose_db_engine() -> None:
    import asyncio
    from contextlib import suppress

    from app.runtime.control.dispatch.openclaw_runtime import close_all_dispatch_runtimes
    from app.runtime.effects.worker import stop_all_runtime_effect_runners
    from app.runtime.watchdog.manager import stop_all_runtime_watchdogs

    await stop_all_runtime_watchdogs()
    await stop_all_runtime_effect_runners()
    await close_all_dispatch_runtimes()
    sessions_by_loop = tuple(tuple(sessions) for sessions in _OPEN_SESSIONS_BY_LOOP.values())
    _OPEN_SESSIONS_BY_LOOP.clear()
    await asyncio.sleep(0.05)
    for sessions in sessions_by_loop:
        for session in sessions:
            with suppress(Exception):
                await session.close()
    for engine in tuple(_ENGINE_BY_LOOP.values()):
        await engine.dispose()
    _ENGINE_BY_LOOP.clear()
    _SESSION_FACTORY_BY_LOOP.clear()
    # Let aiosqlite worker threads deliver their final close callbacks before
    # pytest inspects unraisable exceptions at the end of the current test.
    await asyncio.sleep(0.2)
