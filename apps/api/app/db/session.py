from __future__ import annotations

from collections.abc import AsyncIterator
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.runtime.effects import (
    clear_post_commit_actions,
    notify_runtime_effect_runner,
    stage_post_commit_effects,
    stop_runtime_effect_runner,
)

_ENGINE_BY_LOOP: dict[int, AsyncEngine] = {}
_SESSION_FACTORY_BY_LOOP: dict[int, async_sessionmaker[AsyncSession]] = {}
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
}


class RuntimeAsyncSession(AsyncSession):
    async def commit(self) -> None:
        staged_effects = await stage_post_commit_effects(self)
        await super().commit()
        if staged_effects:
            notify_runtime_effect_runner()

    async def rollback(self) -> None:
        clear_post_commit_actions(self)
        await super().rollback()


def _loop_id() -> int:
    import asyncio

    return id(asyncio.get_running_loop())


def get_async_engine() -> AsyncEngine:
    settings = get_settings()
    loop_id = _loop_id()
    if loop_id not in _ENGINE_BY_LOOP:
        url = make_url(settings.database_url)
        engine_kwargs: dict[str, object] = {
            "echo": settings.debug,
        }
        if url.get_backend_name() == "sqlite":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if url.database in {None, "", ":memory:"}:
                engine_kwargs["poolclass"] = StaticPool
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


async def ensure_database_schema() -> None:
    from app.db import RuntimeBase

    engine = get_async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(RuntimeBase.metadata.create_all)
        await connection.run_sync(_verify_database_schema_contract)


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
    for table_name, expected_targets in REQUIRED_SCHEMA_FOREIGN_KEYS.items():
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
    for table_name, expected_indexes in REQUIRED_SCHEMA_INDEXES.items():
        actual_indexes = _index_names(connection, table_name)
        for index_name in sorted(expected_indexes):
            if index_name in actual_indexes:
                continue
            missing.append(f"{table_name} missing index {index_name}")
    return missing


def _verify_database_schema_contract(connection: Connection) -> None:
    missing = _missing_foreign_key_messages(connection)
    missing.extend(_missing_index_messages(connection))
    if missing:
        joined = "; ".join(missing)
        raise RuntimeError(
            "existing database schema cannot be upgraded in place to the current "
            f"Phase 0-3 contract: {joined}. Run `autoclaw db reset`."
        )


async def dispose_db_engine() -> None:
    await stop_runtime_effect_runner()
    for engine in _ENGINE_BY_LOOP.values():
        await engine.dispose()
    _ENGINE_BY_LOOP.clear()
    _SESSION_FACTORY_BY_LOOP.clear()
