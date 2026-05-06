from __future__ import annotations

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from app import cli
from app.db.models.runtime.assignment import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptModel,
)
from app.db.models.runtime.dispatch import DispatchTurnModel
from app.db.models.runtime.flow import FlowModel, FlowNodeModel
from app.db.session import dispose_db_engine
from app.runtime.contracts import FlowStatus
from app.schemas.runtime import (
    DocRef,
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorSupportSurfaceRef,
    ParentToolCall,
    ReleaseGreenPayload,
    RuntimeFlowRead,
    TopActionableItem,
    WorkflowManifestRef,
)
from pydantic import ValidationError
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty, configure_mappers


def _relationship(
    model: type[Any],
    name: str,
) -> RelationshipProperty[Any]:
    return cast(RelationshipProperty[Any], sa_inspect(model).relationships[name])


def _foreign_key_targets(connection: sqlite3.Connection, table_name: str) -> set[tuple[str, str]]:
    return {
        (row[2], row[3])
        for row in connection.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
    }


def _foreign_key_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[tuple[str, str, str]]:
    return {
        (row[3], row[2], row[4])
        for row in connection.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
        if isinstance(row[3], str) and isinstance(row[2], str) and isinstance(row[4], str)
    }


def _table_sql(connection: sqlite3.Connection, table_name: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    assert row is not None and isinstance(row[0], str)
    return row[0]


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        if isinstance(row[1], str)
    }


def _index_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA index_list('{table_name}')").fetchall()
        if isinstance(row[1], str)
    }


async def _initialize_runtime_schema_database(tmp_path: Path) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

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


def _seed_runtime_lineage_scope_fixture(connection: sqlite3.Connection) -> None:
    timestamp = "2026-05-06T00:00:00+00:00"
    connection.execute("PRAGMA foreign_keys = ON")

    with connection:
        connection.execute(
            """
            INSERT INTO workflow_definitions (
                workflow_key,
                current_revision_no,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("workflow.alpha", 1, timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO workflow_revisions (
                workflow_revision_id,
                workflow_key,
                revision_no,
                content_hash,
                content_json,
                source_path,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "workflow-revision.alpha.1",
                "workflow.alpha",
                1,
                "hash.workflow.alpha.1",
                "{}",
                None,
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO role_definitions (
                role_key,
                current_revision_no,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("role.worker", 1, timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO role_revisions (
                role_revision_id,
                role_key,
                revision_no,
                content_hash,
                content_json,
                source_path,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "role-revision.worker.1",
                "role.worker",
                1,
                "hash.role.worker.1",
                "{}",
                None,
                timestamp,
            ),
        )
        connection.executemany(
            """
            INSERT INTO tasks (
                task_id,
                task_key,
                title,
                summary,
                instruction,
                workflow_key,
                task_root_path,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    "task.alpha.a",
                    "task-key.alpha.a",
                    "Task Alpha A",
                    "Schema contract fixture task A",
                    None,
                    "workflow.alpha",
                    "/tmp/task-alpha-a",
                    timestamp,
                    timestamp,
                ),
                (
                    "task.alpha.b",
                    "task-key.alpha.b",
                    "Task Alpha B",
                    "Schema contract fixture task B",
                    None,
                    "workflow.alpha",
                    "/tmp/task-alpha-b",
                    timestamp,
                    timestamp,
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO compiled_plans (
                compiled_plan_id,
                task_id,
                workflow_key,
                definition_revision_no,
                compiler_version,
                snapshot_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    "compiled-plan.alpha.a",
                    "task.alpha.a",
                    "workflow.alpha",
                    1,
                    "test-compiler",
                    "{}",
                    timestamp,
                ),
                (
                    "compiled-plan.alpha.b",
                    "task.alpha.b",
                    "workflow.alpha",
                    1,
                    "test-compiler",
                    "{}",
                    timestamp,
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO flows (
                flow_id,
                task_id,
                compiled_plan_id,
                status,
                active_flow_revision_id,
                current_open_dispatch_id,
                current_node_key,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    "flow.alpha.a",
                    "task.alpha.a",
                    "compiled-plan.alpha.a",
                    "running",
                    None,
                    None,
                    None,
                    timestamp,
                    timestamp,
                ),
                (
                    "flow.alpha.b",
                    "task.alpha.b",
                    "compiled-plan.alpha.b",
                    "running",
                    None,
                    None,
                    None,
                    timestamp,
                    timestamp,
                ),
            ),
        )
        connection.executemany(
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
                (
                    "flow-revision.alpha.a.1",
                    "flow.alpha.a",
                    1,
                    None,
                    "compiled-plan.alpha.a",
                    "launch",
                    None,
                    "{}",
                    timestamp,
                ),
                (
                    "flow-revision.alpha.a.2",
                    "flow.alpha.a",
                    2,
                    "flow-revision.alpha.a.1",
                    "compiled-plan.alpha.a",
                    "add_child",
                    None,
                    "{}",
                    timestamp,
                ),
                (
                    "flow-revision.alpha.b.1",
                    "flow.alpha.b",
                    1,
                    None,
                    "compiled-plan.alpha.b",
                    "launch",
                    None,
                    "{}",
                    timestamp,
                ),
            ),
        )
        connection.executemany(
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
                (
                    "flow-node.alpha.a.r1.root",
                    "flow.alpha.a",
                    "flow-revision.alpha.a.1",
                    "root",
                    None,
                    None,
                    "root",
                    "role.worker",
                    1,
                    "Root role",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "Root node for revision 1",
                    "[]",
                    None,
                    None,
                    "[]",
                    None,
                    "ready",
                    None,
                    0,
                ),
                (
                    "flow-node.alpha.a.r2.root",
                    "flow.alpha.a",
                    "flow-revision.alpha.a.2",
                    "root",
                    None,
                    None,
                    "root",
                    "role.worker",
                    1,
                    "Root role",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "Root node for revision 2",
                    "[]",
                    None,
                    None,
                    "[]",
                    None,
                    "ready",
                    None,
                    0,
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO assignments (
                assignment_id,
                task_id,
                flow_id,
                flow_revision_id,
                flow_node_id,
                assignment_key,
                node_key,
                summary,
                instruction,
                criteria_json,
                consumes_json,
                produces_json,
                transient_refs_json,
                task_memory_search_hints_json,
                current_attempt_id,
                created_by_dispatch_id,
                created_at,
                superseded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    "assignment.alpha.a.r1.root",
                    "task.alpha.a",
                    "flow.alpha.a",
                    "flow-revision.alpha.a.1",
                    "flow-node.alpha.a.r1.root",
                    "assignment-key.alpha.a.r1.root",
                    "root",
                    "Revision 1 root assignment",
                    None,
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    None,
                    None,
                    timestamp,
                    None,
                ),
                (
                    "assignment.alpha.a.r2.root",
                    "task.alpha.a",
                    "flow.alpha.a",
                    "flow-revision.alpha.a.2",
                    "flow-node.alpha.a.r2.root",
                    "assignment-key.alpha.a.r2.root",
                    "root",
                    "Revision 2 root assignment",
                    None,
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    None,
                    None,
                    timestamp,
                    None,
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO attempts (
                attempt_id,
                assignment_id,
                assignment_key,
                flow_node_id,
                task_id,
                node_key,
                retry_of_attempt_id,
                status,
                opened_at,
                latest_checkpoint_id,
                terminal_outcome,
                created_at,
                closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    "attempt.alpha.a.r1.root.01",
                    "assignment.alpha.a.r1.root",
                    "assignment-key.alpha.a.r1.root",
                    "flow-node.alpha.a.r1.root",
                    "task.alpha.a",
                    "root",
                    None,
                    "running",
                    timestamp,
                    None,
                    None,
                    timestamp,
                    None,
                ),
                (
                    "attempt.alpha.a.r2.root.01",
                    "assignment.alpha.a.r2.root",
                    "assignment-key.alpha.a.r2.root",
                    "flow-node.alpha.a.r2.root",
                    "task.alpha.a",
                    "root",
                    None,
                    "running",
                    timestamp,
                    None,
                    None,
                    timestamp,
                    None,
                ),
            ),
        )


def _runtime_flow_read() -> RuntimeFlowRead:
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


def test_operator_support_surface_refs_emit_explicit_kinds_for_operator_carriers() -> None:
    manifest_ref = WorkflowManifestRef(
        path=Path("/tmp/task/_runtime/workflow-manifest.md"),
        description="Whole-workflow visible contract for the current task.",
    )
    doc_ref = DocRef(
        kind="doc",
        path=Path("/tmp/task/_runtime/dispatch"),
        description="Dispatch observability directory for task-scoped inspection.",
    )
    normalized_current_paths = (
        OperatorSupportSurfaceRef.model_validate(manifest_ref),
        OperatorSupportSurfaceRef.model_validate(doc_ref),
    )
    snapshot = OperatorFlowSnapshotResponse(
        flow=_runtime_flow_read(),
        top_actionable_items=(
            TopActionableItem(
                summary="Current runtime status is 'running'.",
                node_key="implementation_subtree",
                current_paths=normalized_current_paths,
            ),
        ),
        current_paths=normalized_current_paths,
    )

    dumped = snapshot.model_dump(mode="json")

    assert dumped["current_paths"][0]["kind"] == "manifest"
    assert dumped["current_paths"][0]["slot"] is None
    assert dumped["current_paths"][0]["version"] is None
    assert dumped["current_paths"][1]["kind"] == "doc"
    assert dumped["top_actionable_items"][0]["current_paths"][0]["kind"] == "manifest"
    assert (
        OperatorSupportSurfaceRef.model_validate(manifest_ref).model_dump(mode="json")["kind"]
        == "manifest"
    )


def test_observability_file_refs_infer_support_kinds_from_projection_paths() -> None:
    ref = ObservabilityFileRef(
        path=Path("/tmp/task/_runtime/dispatch/dispatch.parent.01/delivery-state.json"),
        description="Latest task-scoped delivery-state projection.",
    )

    assert ref.kind == "delivery_state"
    assert ref.model_dump(mode="json")["kind"] == "delivery_state"
    assert OperatorSupportSurfaceRef.model_validate(ref).kind == "delivery_state"


def test_operator_support_surface_refs_reject_conflicting_fixed_kinds() -> None:
    with pytest.raises(ValidationError, match="must use operator ref kind 'manifest'"):
        OperatorSupportSurfaceRef.model_validate(
            {
                "kind": "doc",
                "path": Path("/tmp/task/_runtime/workflow-manifest.md"),
                "description": "Conflicting kind for manifest path.",
            }
        )

    with pytest.raises(ValidationError, match="must use observability kind 'delivery_state'"):
        ObservabilityFileRef.model_validate(
            {
                "kind": "provider_events",
                "path": Path("/tmp/task/_runtime/dispatch/dispatch.parent.01/delivery-state.json"),
                "description": "Conflicting observability kind.",
            }
        )


def test_parent_tool_call_uses_tool_name_to_validate_payload_shape() -> None:
    release_green = ParentToolCall.model_validate(
        {
            "tool_name": "release_green",
            "payload": {},
        }
    )

    assert release_green.tool_name == "release_green"
    assert isinstance(release_green.payload, ReleaseGreenPayload)
    assert release_green.as_variant().tool_name == "release_green"

    with pytest.raises(ValidationError):
        ParentToolCall.model_validate(
            {
                "tool_name": "assign_child",
                "payload": {},
            }
        )


def test_runtime_mapper_exposes_currentness_chain_and_dispatch_sidecars() -> None:
    configure_mappers()

    active_flow_revision = _relationship(FlowModel, "active_flow_revision")
    current_open_dispatch = _relationship(FlowModel, "current_open_dispatch")
    current_assignment = _relationship(FlowNodeModel, "current_assignment")
    current_attempt = _relationship(AssignmentModel, "current_attempt")
    latest_checkpoint = _relationship(AttemptModel, "latest_checkpoint")
    current_publication = _relationship(ArtifactCurrentPointerModel, "current_publication")
    previous_dispatch = _relationship(DispatchTurnModel, "previous_dispatch")
    superseded_by_dispatch = _relationship(DispatchTurnModel, "superseded_by_dispatch")
    delivery_state = _relationship(DispatchTurnModel, "delivery_state")
    continuity_state = _relationship(DispatchTurnModel, "continuity_state")
    watchdog_state = _relationship(DispatchTurnModel, "watchdog_state")
    provider_events = _relationship(DispatchTurnModel, "provider_events")
    callback_binding = _relationship(DispatchTurnModel, "callback_binding")
    node_sessions = _relationship(DispatchTurnModel, "node_sessions")

    assert active_flow_revision.viewonly is True
    assert active_flow_revision.lazy == "selectin"
    assert {column.key for column in active_flow_revision.local_columns} == {
        "active_flow_revision_id",
        "flow_id",
    }
    assert current_open_dispatch.viewonly is True
    assert current_open_dispatch.lazy == "selectin"
    assert {column.key for column in current_open_dispatch.local_columns} == {
        "current_open_dispatch_id",
        "flow_id",
    }
    assert current_assignment.viewonly is True
    assert current_assignment.lazy == "selectin"
    assert {column.key for column in current_assignment.local_columns} == {
        "current_assignment_id",
        "flow_node_id",
    }
    assert current_attempt.viewonly is True
    assert current_attempt.lazy == "raise"
    assert {column.key for column in current_attempt.local_columns} == {
        "assignment_id",
        "current_attempt_id",
    }
    assert latest_checkpoint.viewonly is True
    assert latest_checkpoint.lazy == "raise"
    assert {column.key for column in latest_checkpoint.local_columns} == {
        "attempt_id",
        "latest_checkpoint_id",
    }
    assert current_publication.lazy == "raise"
    assert {column.key for column in current_publication.local_columns} == {
        "current_version",
        "flow_node_id",
        "owner_node_key",
        "slot",
        "task_id",
    }
    assert previous_dispatch.lazy == "selectin"
    assert {column.key for column in previous_dispatch.remote_side} == {"dispatch_id"}
    assert superseded_by_dispatch.lazy == "selectin"
    assert {column.key for column in superseded_by_dispatch.remote_side} == {"dispatch_id"}
    assert delivery_state.lazy == "selectin"
    assert delivery_state.uselist is False
    assert continuity_state.lazy == "selectin"
    assert continuity_state.uselist is False
    assert watchdog_state.lazy == "selectin"
    assert watchdog_state.uselist is False
    assert provider_events.lazy == "selectin"
    assert provider_events.uselist is True
    assert callback_binding.lazy == "selectin"
    assert callback_binding.uselist is False
    assert node_sessions.lazy == "selectin"
    assert node_sessions.uselist is True


async def test_runtime_schema_emits_relational_lineage_foreign_keys(tmp_path: Path) -> None:
    database_path = await _initialize_runtime_schema_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        workflow_definition_targets = _foreign_key_targets(connection, "workflow_definitions")
        role_definition_targets = _foreign_key_targets(connection, "role_definitions")
        policy_definition_targets = _foreign_key_targets(connection, "policy_definitions")
        task_compose_targets = _foreign_key_targets(connection, "task_composes")
        compiled_plan_targets = _foreign_key_targets(connection, "compiled_plans")
        compiled_plan_node_targets = _foreign_key_targets(connection, "compiled_plan_nodes")
        compiled_plan_edge_targets = _foreign_key_targets(connection, "compiled_plan_edges")
        flow_targets = _foreign_key_targets(connection, "flows")
        flow_node_targets = _foreign_key_targets(connection, "flow_nodes")
        flow_edge_targets = _foreign_key_targets(connection, "flow_edges")
        assignment_targets = _foreign_key_targets(connection, "assignments")
        attempt_targets = _foreign_key_targets(connection, "attempts")
        checkpoint_targets = _foreign_key_targets(connection, "attempt_checkpoints")
        dispatch_turn_targets = _foreign_key_targets(connection, "dispatch_turns")
        dispatch_delivery_targets = _foreign_key_targets(connection, "dispatch_delivery_states")
        dispatch_continuity_targets = _foreign_key_targets(
            connection,
            "dispatch_continuity_states",
        )
        dispatch_watchdog_targets = _foreign_key_targets(connection, "dispatch_watchdog_states")
        provider_event_targets = _foreign_key_targets(connection, "provider_event_records")
        artifact_publication_targets = _foreign_key_targets(connection, "artifact_publications")
        artifact_current_pointer_targets = _foreign_key_targets(
            connection,
            "artifact_current_pointers",
        )
        callback_binding_targets = _foreign_key_targets(connection, "dispatch_callback_bindings")
        node_session_targets = _foreign_key_targets(connection, "node_sessions")
        budget_counter_targets = _foreign_key_targets(connection, "budget_counters")
        flow_revision_fk_columns = _foreign_key_columns(connection, "flow_revisions")
        flow_node_fk_columns = _foreign_key_columns(connection, "flow_nodes")
        assignment_fk_columns = _foreign_key_columns(connection, "assignments")
        checkpoint_fk_columns = _foreign_key_columns(connection, "attempt_checkpoints")
        artifact_publication_fk_columns = _foreign_key_columns(connection, "artifact_publications")
        dispatch_turn_fk_columns = _foreign_key_columns(connection, "dispatch_turns")
        dispatch_delivery_fk_columns = _foreign_key_columns(connection, "dispatch_delivery_states")
        dispatch_watchdog_fk_columns = _foreign_key_columns(connection, "dispatch_watchdog_states")
        artifact_current_pointer_fk_columns = _foreign_key_columns(
            connection,
            "artifact_current_pointers",
        )
        flow_sql = _table_sql(connection, "flows")
        flow_revision_sql = _table_sql(connection, "flow_revisions")
        flow_node_sql = _table_sql(connection, "flow_nodes")
        assignment_sql = _table_sql(connection, "assignments")
        checkpoint_sql = _table_sql(connection, "attempt_checkpoints")
        artifact_publication_sql = _table_sql(connection, "artifact_publications")
        dispatch_sql = _table_sql(connection, "dispatch_turns")
        dispatch_delivery_sql = _table_sql(connection, "dispatch_delivery_states")
        artifact_current_pointer_sql = _table_sql(connection, "artifact_current_pointers")
        provider_event_sql = _table_sql(connection, "provider_event_records")
        callback_binding_sql = _table_sql(connection, "dispatch_callback_bindings")
        flow_revision_columns = _table_columns(connection, "flow_revisions")
        flow_node_columns = _table_columns(connection, "flow_nodes")
        assignment_columns = _table_columns(connection, "assignments")
        artifact_publication_columns = _table_columns(connection, "artifact_publications")
        dispatch_turn_columns = _table_columns(connection, "dispatch_turns")
        artifact_current_pointer_columns = _table_columns(connection, "artifact_current_pointers")
        provider_event_columns = _table_columns(connection, "provider_event_records")
        flow_indexes = _index_names(connection, "flows")
        checkpoint_indexes = _index_names(connection, "attempt_checkpoints")
        dispatch_indexes = _index_names(connection, "dispatch_turns")
        provider_event_indexes = _index_names(connection, "provider_event_records")

    assert ("workflow_revisions", "current_revision_no") in workflow_definition_targets
    assert ("role_revisions", "current_revision_no") in role_definition_targets
    assert ("policy_revisions", "current_revision_no") in policy_definition_targets
    assert ("workflow_revisions", "workflow_revision_no") in task_compose_targets
    assert ("compiled_plans", "compiled_plan_id") in task_compose_targets
    assert ("workflow_revisions", "definition_revision_no") in compiled_plan_targets
    assert ("compiled_plan_nodes", "parent_compiled_plan_node_id") in compiled_plan_node_targets
    assert ("role_revisions", "role_key") in compiled_plan_node_targets
    assert ("role_revisions", "role_revision_no") in compiled_plan_node_targets
    assert ("policy_revisions", "policy_key") in compiled_plan_node_targets
    assert ("policy_revisions", "policy_revision_no") in compiled_plan_node_targets
    assert ("compiled_plan_nodes", "parent_node_key") in compiled_plan_node_targets
    assert ("compiled_plan_nodes", "provider_compiled_plan_node_id") in compiled_plan_edge_targets
    assert ("compiled_plan_nodes", "consumer_compiled_plan_node_id") in compiled_plan_edge_targets
    assert ("compiled_plan_nodes", "provider_node_key") in compiled_plan_edge_targets
    assert ("compiled_plan_nodes", "consumer_node_key") in compiled_plan_edge_targets
    assert ("flow_revisions", "active_flow_revision_id") in flow_targets
    assert ("dispatch_turns", "current_open_dispatch_id") in flow_targets
    assert ("flow_nodes", "flow_id") in flow_node_targets
    assert ("flow_nodes", "flow_revision_id") in flow_node_targets
    assert ("flow_nodes", "parent_flow_node_id") in flow_node_targets
    assert ("flow_nodes", "parent_node_key") in flow_node_targets
    assert ("role_revisions", "role_key") in flow_node_targets
    assert ("role_revisions", "role_revision_no") in flow_node_targets
    assert ("policy_revisions", "policy_key") in flow_node_targets
    assert ("policy_revisions", "policy_revision_no") in flow_node_targets
    assert ("assignments", "current_assignment_id") in flow_node_targets
    assert ("flow_nodes", "provider_flow_node_id") in flow_edge_targets
    assert ("flow_nodes", "consumer_flow_node_id") in flow_edge_targets
    assert ("flow_nodes", "provider_node_key") in flow_edge_targets
    assert ("flow_nodes", "consumer_node_key") in flow_edge_targets
    assert ("attempts", "current_attempt_id") in assignment_targets
    assert ("attempt_checkpoints", "latest_checkpoint_id") in attempt_targets
    assert ("assignments", "assignment_id") in checkpoint_targets
    assert ("attempts", "attempt_id") in checkpoint_targets
    assert ("flow_nodes", "flow_node_id") in checkpoint_targets
    assert ("flow_revisions", "flow_revision_id") in dispatch_turn_targets
    assert ("flow_nodes", "flow_node_id") in dispatch_turn_targets
    assert ("assignments", "assignment_id") in dispatch_turn_targets
    assert ("attempts", "attempt_id") in dispatch_turn_targets
    assert ("dispatch_turns", "dispatch_id") in dispatch_delivery_targets
    assert ("dispatch_turns", "dispatch_id") in dispatch_continuity_targets
    assert ("dispatch_turns", "dispatch_id") in dispatch_watchdog_targets
    assert ("dispatch_turns", "dispatch_id") in provider_event_targets
    assert ("assignments", "assignment_key") in artifact_publication_targets
    assert ("flow_nodes", "flow_node_id") in artifact_publication_targets
    assert ("attempts", "attempt_id") in artifact_publication_targets
    assert ("artifact_publications", "task_id") in artifact_current_pointer_targets
    assert ("artifact_publications", "flow_node_id") in artifact_current_pointer_targets
    assert ("artifact_publications", "owner_node_key") in artifact_current_pointer_targets
    assert ("artifact_publications", "slot") in artifact_current_pointer_targets
    assert ("assignments", "assignment_id") in callback_binding_targets
    assert ("attempts", "attempt_id") in callback_binding_targets
    assert ("flow_nodes", "flow_node_id") in node_session_targets
    assert ("dispatch_turns", "dispatch_id") in node_session_targets
    assert ("flows", "flow_id") in budget_counter_targets
    assert ("flow_nodes", "flow_node_id") in budget_counter_targets
    assert ("assignments", "assignment_id") in budget_counter_targets
    assert ("attempts", "attempt_id") in budget_counter_targets
    assert (
        "flow_id",
        "flow_revisions",
        "flow_id",
    ) in flow_revision_fk_columns
    assert (
        "parent_flow_revision_id",
        "flow_revisions",
        "flow_revision_id",
    ) in flow_revision_fk_columns
    assert (
        "flow_id",
        "flow_nodes",
        "flow_id",
    ) in flow_node_fk_columns
    assert (
        "flow_revision_id",
        "flow_nodes",
        "flow_revision_id",
    ) in flow_node_fk_columns
    assert (
        "parent_flow_node_id",
        "flow_nodes",
        "flow_node_id",
    ) in flow_node_fk_columns
    assert (
        "source_compiled_plan_id",
        "compiled_plans",
        "compiled_plan_id",
    ) in flow_revision_fk_columns
    assert ("created_by_dispatch_id", "dispatch_turns", "dispatch_id") in flow_revision_fk_columns
    assert ("flow_id", "flows", "flow_id") in flow_node_fk_columns
    assert ("flow_id", "flows", "flow_id") in assignment_fk_columns
    assert ("flow_revision_id", "flow_revisions", "flow_revision_id") in assignment_fk_columns
    assert ("created_by_dispatch_id", "dispatch_turns", "dispatch_id") in assignment_fk_columns
    assert ("attempt_id", "attempts", "attempt_id") in checkpoint_fk_columns
    assert ("assignment_id", "attempts", "assignment_id") in checkpoint_fk_columns
    assert ("assignment_id", "assignments", "assignment_id") in checkpoint_fk_columns
    assert ("flow_node_id", "assignments", "flow_node_id") in checkpoint_fk_columns
    assert ("flow_node_id", "flow_nodes", "flow_node_id") in checkpoint_fk_columns
    assert ("attempt_id", "attempts", "attempt_id") in artifact_publication_fk_columns
    assert ("flow_node_id", "attempts", "flow_node_id") in artifact_publication_fk_columns
    assert ("flow_node_id", "flow_nodes", "flow_node_id") in artifact_publication_fk_columns
    assert ("flow_id", "flow_revisions", "flow_id") in dispatch_turn_fk_columns
    assert ("flow_revision_id", "flow_revisions", "flow_revision_id") in dispatch_turn_fk_columns
    assert ("flow_id", "flow_nodes", "flow_id") in dispatch_turn_fk_columns
    assert ("flow_revision_id", "flow_nodes", "flow_revision_id") in dispatch_turn_fk_columns
    assert ("flow_node_id", "flow_nodes", "flow_node_id") in dispatch_turn_fk_columns
    assert ("previous_dispatch_id", "dispatch_turns", "dispatch_id") in dispatch_turn_fk_columns
    assert (
        "superseded_by_dispatch_id",
        "dispatch_turns",
        "dispatch_id",
    ) in dispatch_turn_fk_columns
    assert ("assignment_id", "assignments", "assignment_id") in dispatch_turn_fk_columns
    assert (
        "staged_child_assignment_id",
        "assignments",
        "assignment_id",
    ) in dispatch_turn_fk_columns
    assert ("assignment_id", "attempts", "assignment_id") in dispatch_turn_fk_columns
    assert (
        "release_precondition_flow_revision_id",
        "flow_revisions",
        "flow_revision_id",
    ) in dispatch_turn_fk_columns
    assert ("attempt_id", "attempts", "attempt_id") in dispatch_turn_fk_columns
    assert (
        "release_precondition_assignment_id",
        "assignments",
        "assignment_id",
    ) in dispatch_turn_fk_columns
    assert (
        "previous_dispatch_id",
        "dispatch_turns",
        "dispatch_id",
    ) in dispatch_delivery_fk_columns
    assert (
        "superseded_by_dispatch_id",
        "dispatch_turns",
        "dispatch_id",
    ) in dispatch_delivery_fk_columns
    assert (
        "recovery_dispatch_id",
        "dispatch_turns",
        "dispatch_id",
    ) in dispatch_watchdog_fk_columns
    assert (
        "previous_dispatch_id",
        "dispatch_turns",
        "dispatch_id",
    ) in dispatch_watchdog_fk_columns
    assert (
        "superseded_by_dispatch_id",
        "dispatch_turns",
        "dispatch_id",
    ) in dispatch_watchdog_fk_columns
    assert (
        "current_version",
        "artifact_publications",
        "version",
    ) in artifact_current_pointer_fk_columns
    assert (
        "flow_node_id",
        "artifact_publications",
        "flow_node_id",
    ) in artifact_current_pointer_fk_columns
    assert "ck_flows_status" in flow_sql
    assert {
        "parent_flow_revision_id",
        "source_compiled_plan_id",
        "cause",
        "created_by_dispatch_id",
        "adopted_at",
    } <= flow_revision_columns
    assert {"flow_id", "node_kind", "state"} <= flow_node_columns
    assert {"flow_id", "flow_revision_id", "superseded_at"} <= assignment_columns
    assert {"flow_node_id"} <= artifact_publication_columns
    assert {
        "previous_dispatch_id",
        "superseded_by_dispatch_id",
        "staged_child_assignment_id",
        "release_precondition_flow_revision_id",
        "release_precondition_assignment_id",
        "gateway_run_id",
    } <= dispatch_turn_columns
    assert {
        "flow_node_id",
        "task_id",
        "owner_node_key",
        "slot",
        "current_version",
    } <= artifact_current_pointer_columns
    assert {
        "attempt_id",
        "event_no",
        "event_source",
        "provider_event_name",
        "summary",
        "detail",
        "observed_at",
        "provider_occurred_at",
    } <= provider_event_columns
    assert "ck_flow_revisions_cause" in flow_revision_sql
    assert "fk_flow_revisions_parent_owner" in flow_revision_sql
    assert "revision_no" in flow_revision_sql
    assert "adopted_at" in flow_revision_sql
    assert "ck_flow_nodes_node_kind" in flow_node_sql
    assert "ck_flow_nodes_state" in flow_node_sql
    assert "fk_flow_nodes_parent_owner" in flow_node_sql
    assert "node_kind" in flow_node_sql
    assert "state" in flow_node_sql
    assert "release_green_ready" not in assignment_sql
    assert "release_blocked_ready" not in assignment_sql
    assert "superseded_at" in assignment_sql
    assert "fk_assignments_created_by_dispatch" in assignment_sql
    assert "ck_attempt_checkpoints_kind" in checkpoint_sql
    assert "ck_attempt_checkpoints_progress_outcome" in checkpoint_sql
    assert "ck_attempt_checkpoints_terminal_outcome" in checkpoint_sql
    assert "fk_attempt_checkpoints_attempt_owner" in checkpoint_sql
    assert "fk_attempt_checkpoints_assignment_owner" in checkpoint_sql
    assert "fk_artifact_publications_attempt_owner" in artifact_publication_sql
    assert "ck_dispatch_turns_send_mode" in dispatch_sql
    assert "ck_dispatch_turns_release_precondition_kind" in dispatch_sql
    assert "gateway_run_id" in dispatch_sql
    assert "release_precondition_kind" in dispatch_sql
    assert "staged_continuation_kind IN ('child_assignment')" in dispatch_sql
    assert "ck_dispatch_turns_flow_node_requires_flow_revision" in dispatch_sql
    assert "ck_dispatch_turns_assignment_requires_flow_node" in dispatch_sql
    assert "ck_dispatch_turns_attempt_requires_assignment" in dispatch_sql
    assert "fk_dispatch_turns_flow_revision_owner" in dispatch_sql
    assert "fk_dispatch_turns_flow_node_owner" in dispatch_sql
    assert "fk_dispatch_turns_attempt_owner" in dispatch_sql
    assert "fk_dispatch_turns_previous_dispatch" in dispatch_sql
    assert "fk_dispatch_turns_superseded_by_dispatch" in dispatch_sql
    assert "fk_dispatch_turns_staged_child_assignment" in dispatch_sql
    assert "fk_dispatch_turns_release_precondition_flow_revision" in dispatch_sql
    assert "fk_dispatch_turns_release_precondition_assignment" in dispatch_sql
    assert "boundary_accepted_waiting_terminal" in dispatch_delivery_sql
    assert "ck_dispatch_delivery_states_send_mode" in dispatch_delivery_sql
    assert "fk_dispatch_delivery_states_previous_dispatch" in dispatch_delivery_sql
    assert "fk_dispatch_delivery_states_superseded_by_dispatch" in dispatch_delivery_sql
    assert "fk_artifact_current_pointers_attempt_owner" in artifact_current_pointer_sql
    assert "fk_artifact_current_pointers_publication" in artifact_current_pointer_sql
    assert "ck_provider_event_records_event_source" in provider_event_sql
    assert "ck_provider_event_records_event_kind" in provider_event_sql
    assert "ck_dispatch_callback_bindings_status" in callback_binding_sql
    assert "ix_flows_status_updated_at" in flow_indexes
    assert "ix_attempt_checkpoints_attempt_recorded_at" in checkpoint_indexes
    assert "ix_dispatch_turns_task_node_rendered_at" in dispatch_indexes
    assert "ix_provider_event_records_dispatch_event_no" in provider_event_indexes


async def test_runtime_schema_rejects_cross_scope_parent_links_on_authoritative_ids(
    tmp_path: Path,
) -> None:
    database_path = await _initialize_runtime_schema_database(tmp_path)

    with sqlite3.connect(database_path) as connection:
        _seed_runtime_lineage_scope_fixture(connection)

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
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

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
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
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
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


async def test_runtime_schema_rejects_cross_scope_dispatch_lineage_ids(tmp_path: Path) -> None:
    database_path = await _initialize_runtime_schema_database(tmp_path)

    def insert_dispatch_turn(
        connection: sqlite3.Connection,
        *,
        dispatch_id: str,
        flow_id: str,
        flow_revision_id: str | None,
        flow_node_id: str | None,
        assignment_id: str | None,
        attempt_id: str | None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO dispatch_turns (
                dispatch_id,
                flow_id,
                flow_revision_id,
                flow_node_id,
                task_id,
                node_key,
                assignment_id,
                assignment_key,
                attempt_id,
                phase,
                status,
                prompt_name,
                send_mode,
                delivery_status,
                control_state,
                gateway_session_key,
                gateway_run_id,
                control_state_reason,
                control_deadline_at,
                abort_requested_at,
                fenced_at,
                prompt_path,
                content_hash,
                previous_dispatch_id,
                superseded_by_dispatch_id,
                staged_child_assignment_id,
                staged_continuation_kind,
                release_precondition_kind,
                release_precondition_flow_revision_id,
                release_precondition_assignment_id,
                release_precondition_recorded_at,
                accepted_boundary,
                closed_by_boundary,
                opened_at,
                rendered_at,
                closed_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                dispatch_id,
                flow_id,
                flow_revision_id,
                flow_node_id,
                "task.alpha.a",
                "root",
                assignment_id,
                (
                    None
                    if assignment_id is None
                    else (
                        "assignment-key.alpha.a.r2.root"
                        if assignment_id == "assignment.alpha.a.r2.root"
                        else "assignment-key.alpha.a.r1.root"
                    )
                ),
                attempt_id,
                "execution",
                "accepted",
                "runtime_dispatch_turn",
                "full_prompt",
                "accepted",
                "launching",
                None,
                None,
                None,
                None,
                None,
                None,
                "/tmp/task-alpha-a/_runtime/dispatch/prompt.md",
                f"hash.{dispatch_id}",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "2026-05-06T00:00:00+00:00",
                "2026-05-06T00:00:00+00:00",
                None,
            ),
        )

    with sqlite3.connect(database_path) as connection:
        _seed_runtime_lineage_scope_fixture(connection)

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
                insert_dispatch_turn(
                    connection,
                    dispatch_id="dispatch.alpha.invalid.flow-revision",
                    flow_id="flow.alpha.a",
                    flow_revision_id="flow-revision.alpha.b.1",
                    flow_node_id=None,
                    assignment_id=None,
                    attempt_id=None,
                )

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
                insert_dispatch_turn(
                    connection,
                    dispatch_id="dispatch.alpha.invalid.flow-node",
                    flow_id="flow.alpha.a",
                    flow_revision_id="flow-revision.alpha.a.2",
                    flow_node_id="flow-node.alpha.a.r1.root",
                    assignment_id=None,
                    attempt_id=None,
                )

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
                insert_dispatch_turn(
                    connection,
                    dispatch_id="dispatch.alpha.invalid.attempt",
                    flow_id="flow.alpha.a",
                    flow_revision_id="flow-revision.alpha.a.2",
                    flow_node_id="flow-node.alpha.a.r2.root",
                    assignment_id="assignment.alpha.a.r2.root",
                    attempt_id="attempt.alpha.a.r1.root.01",
                )


async def test_runtime_schema_rejects_mismatched_checkpoint_and_artifact_flow_nodes(
    tmp_path: Path,
) -> None:
    database_path = await _initialize_runtime_schema_database(tmp_path)

    with sqlite3.connect(database_path) as connection:
        _seed_runtime_lineage_scope_fixture(connection)

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
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

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            with connection:
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
