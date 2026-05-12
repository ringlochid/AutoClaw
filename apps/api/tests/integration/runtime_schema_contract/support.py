from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from app import cli
from app.runtime.contracts import FlowStatus
from app.schemas.runtime import RuntimeFlowRead, WorkflowManifestRef
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty


@dataclass(frozen=True)
class RuntimeSchemaSnapshot:
    foreign_key_targets: dict[str, set[tuple[str, str]]]
    foreign_key_columns: dict[str, set[tuple[str, str, str]]]
    table_sql: dict[str, str]
    table_columns: dict[str, set[str]]
    index_names: dict[str, set[str]]


def relationship_property(
    model: type[Any],
    name: str,
) -> RelationshipProperty[Any]:
    return cast(RelationshipProperty[Any], sa_inspect(model).relationships[name])


def foreign_key_targets(connection: sqlite3.Connection, table_name: str) -> set[tuple[str, str]]:
    return {
        (row[2], row[3])
        for row in connection.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
    }


def foreign_key_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[tuple[str, str, str]]:
    return {
        (row[3], row[2], row[4])
        for row in connection.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
        if isinstance(row[3], str) and isinstance(row[2], str) and isinstance(row[4], str)
    }


def table_sql(connection: sqlite3.Connection, table_name: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    assert row is not None and isinstance(row[0], str)
    return row[0]


def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        if isinstance(row[1], str)
    }


def index_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA index_list('{table_name}')").fetchall()
        if isinstance(row[1], str)
    }


async def initialize_runtime_schema_database(tmp_path: Path) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    from app.db.session import dispose_db_engine

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=False,
                json=False,
            )
        )
    finally:
        await dispose_db_engine()

    return data_dir / "autoclaw.db"


def runtime_flow_read() -> RuntimeFlowRead:
    return RuntimeFlowRead(
        task_id="task_2026_0042",
        task_title="Schema contract task",
        task_summary="Schema contract runtime flow",
        workflow_key="normal-parent-first-release",
        status=FlowStatus.RUNNING,
        active_flow_revision_id="flow-revision.task_2026_0042.01",
        workflow_manifest_ref=WorkflowManifestRef(
            path=Path("/tmp/task/_runtime/workflow-manifest.md"),
            description="Whole-workflow visible contract for the current task.",
        ),
        current_node_key="implementation_subtree",
        active_attempt_id="attempt.implementation_subtree.01",
        updated_at=datetime(2026, 5, 5, tzinfo=UTC),
    )


def read_runtime_schema_snapshot(database_path: Path) -> RuntimeSchemaSnapshot:
    target_tables = (
        "workflow_definitions",
        "role_definitions",
        "policy_definitions",
        "task_composes",
        "compiled_plans",
        "compiled_plan_nodes",
        "compiled_plan_edges",
        "flows",
        "flow_revisions",
        "flow_nodes",
        "flow_edges",
        "assignments",
        "attempts",
        "attempt_checkpoints",
        "dispatch_turns",
        "dispatch_delivery_states",
        "dispatch_continuity_states",
        "dispatch_watchdog_states",
        "provider_event_records",
        "artifact_publications",
        "artifact_current_pointers",
        "dispatch_callback_bindings",
        "node_sessions",
        "budget_counters",
    )
    with sqlite3.connect(database_path) as connection:
        return RuntimeSchemaSnapshot(
            foreign_key_targets={
                table: foreign_key_targets(connection, table) for table in target_tables
            },
            foreign_key_columns={
                table: foreign_key_columns(connection, table) for table in target_tables
            },
            table_sql={table: table_sql(connection, table) for table in target_tables},
            table_columns={table: table_columns(connection, table) for table in target_tables},
            index_names={table: index_names(connection, table) for table in target_tables},
        )
