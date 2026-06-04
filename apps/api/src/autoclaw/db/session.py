"""Temporary Phase 6 shim for the legacy DB session owner."""

from __future__ import annotations

from app.db.session import (
    REQUIRED_SCHEMA_FOREIGN_KEYS,
    REQUIRED_SCHEMA_INDEXES,
    RuntimeAsyncSession,
    SchemaForeignKeySignature,
    dispose_db_engine,
    ensure_database_schema,
    get_async_engine,
    get_db_session,
    get_session_factory,
    notify_runtime_effect_runner,
    open_session_info_value_present,
    ping_database,
    verify_database_schema,
)

__all__ = [
    "REQUIRED_SCHEMA_FOREIGN_KEYS",
    "REQUIRED_SCHEMA_INDEXES",
    "RuntimeAsyncSession",
    "SchemaForeignKeySignature",
    "dispose_db_engine",
    "ensure_database_schema",
    "get_async_engine",
    "get_db_session",
    "get_session_factory",
    "notify_runtime_effect_runner",
    "open_session_info_value_present",
    "ping_database",
    "verify_database_schema",
]
