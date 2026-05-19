from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from tests.integration.runtime_schema_contract.lineage_support import (
    insert_dispatch_turn,
    seed_runtime_lineage_scope_fixture,
)
from tests.integration.runtime_schema_contract.support import (
    initialize_runtime_schema_database,
    table_columns,
)


async def test_runtime_schema_rejects_cross_scope_parent_flow_revision_ids(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(connection, insert_cross_scope_parent_flow_revision)


async def test_runtime_schema_rejects_cross_scope_parent_flow_node_ids(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(connection, insert_cross_scope_parent_flow_node)


async def test_runtime_schema_rejects_dispatch_flow_revision_from_another_flow(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(
            connection,
            lambda conn: insert_dispatch_turn(
                conn,
                dispatch_id="dispatch.alpha.invalid.flow-revision",
                flow_id="flow.alpha.a",
                flow_revision_id="flow-revision.alpha.b.1",
                flow_node_id=None,
                assignment_id=None,
                attempt_id=None,
            ),
        )


async def test_runtime_schema_rejects_dispatch_flow_node_from_another_revision(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(
            connection,
            lambda conn: insert_dispatch_turn(
                conn,
                dispatch_id="dispatch.alpha.invalid.flow-node",
                flow_id="flow.alpha.a",
                flow_revision_id="flow-revision.alpha.a.2",
                flow_node_id="flow-node.alpha.a.r1.root",
                assignment_id=None,
                attempt_id=None,
            ),
        )


async def test_runtime_schema_rejects_dispatch_attempt_from_another_assignment(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(
            connection,
            lambda conn: insert_dispatch_turn(
                conn,
                dispatch_id="dispatch.alpha.invalid.attempt",
                flow_id="flow.alpha.a",
                flow_revision_id="flow-revision.alpha.a.2",
                flow_node_id="flow-node.alpha.a.r2.root",
                assignment_id="assignment.alpha.a.r2.root",
                attempt_id="attempt.alpha.a.r1.root.01",
            ),
        )


async def test_runtime_schema_omits_removed_phase45_authority_and_support_columns(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            if isinstance(row[0], str)
        }
        assert "dispatch_callback_bindings" not in table_names
        assert "status" not in table_columns(connection, "dispatch_turns")
        assert "controller_observation_state" not in table_columns(
            connection, "dispatch_delivery_states"
        )
        assert "continuity_state" not in table_columns(connection, "dispatch_continuity_states")
        node_session_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info('node_sessions')").fetchall()
            if isinstance(row[1], str)
        }
        assert node_session_columns["session_key"][3] == 1


async def test_runtime_schema_rejects_mismatched_checkpoint_flow_node_ids(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(connection, insert_mismatched_checkpoint)


async def test_runtime_schema_rejects_mismatched_artifact_publication_flow_node_ids(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        expect_foreign_key_failure(connection, insert_mismatched_artifact_publication)


def expect_foreign_key_failure(
    connection: sqlite3.Connection,
    inserter: Callable[[sqlite3.Connection], None],
) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        with connection:
            inserter(connection)


def insert_cross_scope_parent_flow_revision(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO flow_revisions (
            flow_revision_id,
            flow_id,
            revision_no,
            parent_flow_revision_id,
            source_compiled_plan_id,
            cause,
            created_by_dispatch_id,
            snapshot_json,
            adopted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "flow-revision.alpha.a.3",
            "flow.alpha.a",
            3,
            "flow-revision.alpha.b.1",
            "compiled-plan.alpha.a",
            "update_child",
            None,
            "{}",
            "2026-05-06T00:00:00+00:00",
        ),
    )


def insert_cross_scope_parent_flow_node(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO flow_nodes (
            flow_node_id,
            flow_id,
            flow_revision_id,
            node_key,
            parent_flow_node_id,
            parent_node_key,
            node_kind,
            role_key,
            role_revision_no,
            role_description,
            role_instruction,
            policy_key,
            policy_revision_no,
            policy_description,
            policy_instruction,
            description,
            child_node_keys_json,
            consumes_json,
            produces_json,
            criteria_json,
            child_defaults_json,
            state,
            current_assignment_id,
            order_index
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "flow-node.alpha.a.r2.child",
            "flow.alpha.a",
            "flow-revision.alpha.a.2",
            "child",
            "flow-node.alpha.a.r1.root",
            "root",
            "worker",
            "role.worker",
            1,
            "Worker role",
            None,
            None,
            None,
            None,
            None,
            "Child node with cross-revision authoritative parent id",
            "[]",
            None,
            None,
            "[]",
            None,
            "ready",
            None,
            1,
        ),
    )


def insert_mismatched_checkpoint(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO attempt_checkpoints (
            checkpoint_id,
            assignment_id,
            assignment_key,
            attempt_id,
            flow_node_id,
            node_key,
            checkpoint_kind,
            outcome,
            summary,
            next_step,
            blockers_json,
            risks_json,
            produced_artifact_claims_json,
            produced_artifacts_json,
            artifact_refs_json,
            transient_refs_json,
            task_memory_search_hints_json,
            recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "checkpoint.alpha.invalid.owner",
            "assignment.alpha.a.r1.root",
            "assignment-key.alpha.a.r1.root",
            "attempt.alpha.a.r1.root.01",
            "flow-node.alpha.a.r2.root",
            "root",
            "progress",
            None,
            "Mismatched flow-node lineage.",
            "This row should be rejected.",
            "[]",
            "[]",
            "[]",
            "[]",
            "[]",
            "[]",
            "[]",
            "2026-05-06T00:00:00+00:00",
        ),
    )


def insert_mismatched_artifact_publication(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO artifact_publications (
            artifact_publication_id,
            task_id,
            flow_node_id,
            owner_node_key,
            slot,
            version,
            path,
            description,
            assignment_key,
            attempt_id,
            published_at,
            supersedes_version,
            supersedes_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "artifact-publication.alpha.invalid.owner",
            "task.alpha.a",
            "flow-node.alpha.a.r2.root",
            "root",
            "report",
            1,
            "/tmp/task-alpha-a/outputs/artifacts/root/report/report.v01.md",
            "Mismatched flow-node lineage.",
            "assignment-key.alpha.a.r1.root",
            "attempt.alpha.a.r1.root.01",
            "2026-05-06T00:00:00+00:00",
            None,
            None,
        ),
    )
