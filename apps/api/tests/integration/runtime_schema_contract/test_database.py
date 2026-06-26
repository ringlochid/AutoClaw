from __future__ import annotations

from pathlib import Path

from tests.integration.runtime_schema_contract.support import (
    RuntimeSchemaSnapshot,
    initialize_runtime_schema_database,
    read_runtime_schema_snapshot,
)

FLOW_TARGET_EXPECTATIONS = (
    (
        "flows",
        {
            ("flow_revisions", "active_flow_revision_id"),
            ("dispatch_turns", "current_open_dispatch_id"),
        },
    ),
    (
        "flow_nodes",
        {
            ("flow_nodes", "flow_id"),
            ("flow_nodes", "flow_revision_id"),
            ("flow_nodes", "parent_flow_node_id"),
            ("flow_nodes", "parent_node_key"),
            ("role_revisions", "role_key"),
            ("role_revisions", "role_revision_no"),
            ("policy_revisions", "policy_key"),
            ("policy_revisions", "policy_revision_no"),
            ("assignments", "current_assignment_id"),
        },
    ),
    (
        "flow_edges",
        {
            ("flow_nodes", "provider_flow_node_id"),
            ("flow_nodes", "consumer_flow_node_id"),
            ("flow_nodes", "provider_node_key"),
            ("flow_nodes", "consumer_node_key"),
        },
    ),
    ("assignments", {("attempts", "current_attempt_id")}),
    ("attempts", {("attempt_checkpoints", "latest_checkpoint_id")}),
    (
        "attempt_checkpoints",
        {
            ("assignments", "assignment_id"),
            ("attempts", "attempt_id"),
            ("flow_nodes", "flow_node_id"),
        },
    ),
    (
        "dispatch_turns",
        {
            ("flow_revisions", "flow_revision_id"),
            ("flow_nodes", "flow_node_id"),
            ("assignments", "assignment_id"),
            ("attempts", "attempt_id"),
        },
    ),
    ("dispatch_delivery_states", {("dispatch_turns", "dispatch_id")}),
    ("dispatch_continuity_states", {("dispatch_turns", "dispatch_id")}),
    ("dispatch_watchdog_states", {("dispatch_turns", "dispatch_id")}),
    ("provider_event_records", {("dispatch_turns", "dispatch_id")}),
    (
        "artifact_publications",
        {
            ("assignments", "assignment_key"),
            ("flow_nodes", "flow_node_id"),
            ("attempts", "attempt_id"),
        },
    ),
    (
        "artifact_current_pointers",
        {
            ("artifact_publications", "task_id"),
            ("artifact_publications", "flow_node_id"),
            ("artifact_publications", "owner_node_key"),
            ("artifact_publications", "slot"),
        },
    ),
    (
        "node_sessions",
        {("flow_nodes", "flow_node_id"), ("dispatch_turns", "dispatch_id")},
    ),
    (
        "pending_human_requests",
        {
            ("tasks", "task_id"),
            ("flows", "flow_id"),
            ("flow_revisions", "flow_revision_id"),
            ("flow_nodes", "flow_node_id"),
            ("assignments", "assignment_id"),
            ("attempts", "attempt_id"),
            ("dispatch_turns", "dispatch_id"),
        },
    ),
    (
        "command_runs",
        {
            ("tasks", "task_id"),
            ("flows", "flow_id"),
            ("flow_revisions", "flow_revision_id"),
            ("flow_nodes", "flow_node_id"),
            ("assignments", "assignment_id"),
            ("attempts", "attempt_id"),
            ("dispatch_turns", "dispatch_id"),
        },
    ),
    (
        "flow_wait_states",
        {
            ("flows", "flow_id"),
            ("tasks", "task_id"),
            ("pending_human_requests", "pending_human_request_id"),
            ("command_runs", "command_run_id"),
            ("dispatch_turns", "created_by_dispatch_id"),
        },
    ),
    (
        "budget_counters",
        {
            ("flows", "flow_id"),
            ("flow_nodes", "flow_node_id"),
            ("assignments", "assignment_id"),
            ("attempts", "attempt_id"),
        },
    ),
)

FLOW_COLUMN_EXPECTATIONS = (
    (
        "flow_revisions",
        {
            ("flow_id", "flow_revisions", "flow_id"),
            ("parent_flow_revision_id", "flow_revisions", "flow_revision_id"),
            ("source_compiled_plan_id", "compiled_plans", "compiled_plan_id"),
            ("created_by_dispatch_id", "dispatch_turns", "dispatch_id"),
        },
    ),
    (
        "flow_nodes",
        {
            ("flow_id", "flow_nodes", "flow_id"),
            ("flow_revision_id", "flow_nodes", "flow_revision_id"),
            ("parent_flow_node_id", "flow_nodes", "flow_node_id"),
            ("flow_id", "flows", "flow_id"),
        },
    ),
    (
        "assignments",
        {
            ("flow_id", "flows", "flow_id"),
            ("flow_revision_id", "flow_revisions", "flow_revision_id"),
            ("created_by_dispatch_id", "dispatch_turns", "dispatch_id"),
        },
    ),
    (
        "attempt_checkpoints",
        {
            ("attempt_id", "attempts", "attempt_id"),
            ("assignment_id", "attempts", "assignment_id"),
            ("assignment_id", "assignments", "assignment_id"),
            ("flow_node_id", "assignments", "flow_node_id"),
            ("flow_node_id", "flow_nodes", "flow_node_id"),
        },
    ),
    (
        "artifact_publications",
        {
            ("attempt_id", "attempts", "attempt_id"),
            ("flow_node_id", "attempts", "flow_node_id"),
            ("flow_node_id", "flow_nodes", "flow_node_id"),
        },
    ),
    (
        "dispatch_delivery_states",
        {
            ("previous_dispatch_id", "dispatch_turns", "dispatch_id"),
            ("superseded_by_dispatch_id", "dispatch_turns", "dispatch_id"),
        },
    ),
    (
        "dispatch_watchdog_states",
        {
            ("recovery_dispatch_id", "dispatch_turns", "dispatch_id"),
            ("previous_dispatch_id", "dispatch_turns", "dispatch_id"),
            ("superseded_by_dispatch_id", "dispatch_turns", "dispatch_id"),
        },
    ),
    (
        "artifact_current_pointers",
        {
            ("current_version", "artifact_publications", "version"),
            ("flow_node_id", "artifact_publications", "flow_node_id"),
        },
    ),
)

CURRENTNESS_COLUMN_EXPECTATIONS = (
    (
        "flow_revisions",
        {
            "parent_flow_revision_id",
            "source_compiled_plan_id",
            "cause",
            "created_by_dispatch_id",
            "adopted_at",
        },
    ),
    ("flow_nodes", {"flow_id", "node_kind", "state"}),
    ("assignments", {"flow_id", "flow_revision_id", "superseded_at"}),
    ("artifact_publications", {"flow_node_id"}),
    (
        "dispatch_turns",
        {
            "previous_dispatch_id",
            "superseded_by_dispatch_id",
            "staged_child_assignment_id",
            "release_precondition_flow_revision_id",
            "release_precondition_assignment_id",
            "release_precondition_descendant_refs_json",
            "gateway_run_id",
        },
    ),
    (
        "artifact_current_pointers",
        {"flow_node_id", "task_id", "owner_node_key", "slot", "current_version"},
    ),
    (
        "provider_event_records",
        {
            "attempt_id",
            "event_no",
            "event_source",
            "provider_event_name",
            "summary",
            "detail",
            "observed_at",
            "provider_occurred_at",
        },
    ),
    (
        "pending_human_requests",
        {
            "requester_node_key",
            "items_json",
            "timeout_json",
            "suggested_human_instruction",
            "opened_at",
            "status",
            "resolution_kind",
            "item_responses_json",
            "resolved_at",
            "resolved_by_actor_ref",
            "resolved_by_surface",
            "resolution_policy_basis",
            "resolution_note",
        },
    ),
    (
        "flow_wait_states",
        {
            "waiting_cause",
            "pending_human_request_id",
            "command_run_id",
            "created_by_dispatch_id",
            "updated_at",
        },
    ),
    (
        "command_runs",
        {
            "requester_node_key",
            "command",
            "description",
            "workdir",
            "timeout_seconds",
            "state",
            "latest_update",
            "latest_log_ref",
            "terminal_summary",
            "terminal_exit_code",
            "terminal_signal",
            "terminal_log_ref",
            "terminal_event_source",
            "terminal_actor_ref",
            "cancellation_requested_at",
            "cancellation_requested_by_actor_ref",
            "created_at",
            "started_at",
            "ended_at",
            "updated_at",
        },
    ),
)

CURRENTNESS_SQL_EXPECTATIONS = (
    ("flows", "ck_flows_status"),
    ("flow_revisions", "ck_flow_revisions_cause"),
    ("flow_revisions", "fk_flow_revisions_parent_owner"),
    ("flow_nodes", "ck_flow_nodes_node_kind"),
    ("flow_nodes", "ck_flow_nodes_state"),
    ("flow_nodes", "fk_flow_nodes_parent_owner"),
    ("assignments", "superseded_at"),
    ("assignments", "fk_assignments_created_by_dispatch"),
    ("attempt_checkpoints", "ck_attempt_checkpoints_kind"),
    ("attempt_checkpoints", "ck_attempt_checkpoints_progress_outcome"),
    ("attempt_checkpoints", "ck_attempt_checkpoints_terminal_outcome"),
    ("attempt_checkpoints", "fk_attempt_checkpoints_attempt_owner"),
    ("attempt_checkpoints", "fk_attempt_checkpoints_assignment_owner"),
    ("artifact_publications", "fk_artifact_publications_attempt_owner"),
    ("dispatch_turns", "ck_dispatch_turns_release_precondition_kind"),
    ("dispatch_turns", "fk_dispatch_turns_flow_revision_owner"),
    ("dispatch_turns", "fk_dispatch_turns_flow_node_owner"),
    ("dispatch_turns", "fk_dispatch_turns_attempt_owner"),
    ("dispatch_turns", "fk_dispatch_turns_previous_dispatch"),
    ("dispatch_turns", "fk_dispatch_turns_superseded_by_dispatch"),
    ("dispatch_delivery_states", "fk_dispatch_delivery_states_previous_dispatch"),
    ("artifact_current_pointers", "fk_artifact_current_pointers_attempt_owner"),
    ("artifact_current_pointers", "fk_artifact_current_pointers_publication"),
    ("provider_event_records", "ck_provider_event_records_event_source"),
    ("provider_event_records", "ck_provider_event_records_event_kind"),
    ("pending_human_requests", "ck_pending_human_requests_kind"),
    ("pending_human_requests", "ck_pending_human_requests_status"),
    ("pending_human_requests", "ck_pending_human_requests_resolution_kind"),
    ("pending_human_requests", "ck_pending_human_requests_resolution_status"),
    ("pending_human_requests", "fk_pending_human_requests_flow_revision_owner"),
    ("pending_human_requests", "fk_pending_human_requests_flow_node_owner"),
    ("pending_human_requests", "fk_pending_human_requests_attempt_owner"),
    ("command_runs", "ck_command_runs_state"),
    ("command_runs", "ck_command_runs_timeout_seconds"),
    ("command_runs", "ck_command_runs_terminal_result"),
    ("command_runs", "fk_command_runs_flow_revision_owner"),
    ("command_runs", "fk_command_runs_flow_node_owner"),
    ("command_runs", "fk_command_runs_attempt_owner"),
    ("flow_wait_states", "ck_flow_wait_states_waiting_cause"),
    ("flow_wait_states", "ck_flow_wait_states_human_request_source"),
    ("flow_wait_states", "ck_flow_wait_states_command_run_source"),
)

INDEX_EXPECTATIONS = (
    ("flows", "ix_flows_status_updated_at"),
    ("attempt_checkpoints", "ix_attempt_checkpoints_attempt_recorded_at"),
    ("dispatch_turns", "ix_dispatch_turns_task_node_rendered_at"),
    ("node_sessions", "ix_node_sessions_session_key"),
    ("provider_event_records", "ix_provider_event_records_dispatch_event_no"),
    ("pending_human_requests", "ix_pending_human_requests_task_status"),
    ("command_runs", "ix_command_runs_task_created"),
    ("command_runs", "ix_command_runs_task_state"),
    ("flow_wait_states", "ix_flow_wait_states_task_cause"),
)


async def test_runtime_schema_emits_definition_plan_and_task_lineage_foreign_keys(
    tmp_path: Path,
) -> None:
    snapshot = await load_schema_snapshot(tmp_path)

    assert_targets(
        snapshot, "workflow_definitions", {("workflow_revisions", "current_revision_no")}
    )
    assert_targets(snapshot, "role_definitions", {("role_revisions", "current_revision_no")})
    assert_targets(snapshot, "policy_definitions", {("policy_revisions", "current_revision_no")})
    assert_targets(
        snapshot,
        "task_composes",
        {("workflow_revisions", "workflow_revision_no"), ("compiled_plans", "compiled_plan_id")},
    )
    assert_targets(snapshot, "compiled_plans", {("workflow_revisions", "definition_revision_no")})
    assert_targets(
        snapshot,
        "compiled_plan_nodes",
        {
            ("compiled_plan_nodes", "parent_compiled_plan_node_id"),
            ("role_revisions", "role_key"),
            ("role_revisions", "role_revision_no"),
            ("policy_revisions", "policy_key"),
            ("policy_revisions", "policy_revision_no"),
            ("compiled_plan_nodes", "parent_node_key"),
        },
    )
    assert_targets(
        snapshot,
        "compiled_plan_edges",
        {
            ("compiled_plan_nodes", "provider_compiled_plan_node_id"),
            ("compiled_plan_nodes", "consumer_compiled_plan_node_id"),
            ("compiled_plan_nodes", "provider_node_key"),
            ("compiled_plan_nodes", "consumer_node_key"),
        },
    )


async def test_runtime_schema_emits_flow_assignment_and_dispatch_lineage_foreign_keys(
    tmp_path: Path,
) -> None:
    snapshot = await load_schema_snapshot(tmp_path)

    for table_name, expected_targets in FLOW_TARGET_EXPECTATIONS:
        assert_targets(snapshot, table_name, expected_targets)
    for table_name, expected_columns in FLOW_COLUMN_EXPECTATIONS:
        assert_columns(snapshot, table_name, expected_columns)


async def test_runtime_schema_emits_columns_and_constraints_for_runtime_currentness(
    tmp_path: Path,
) -> None:
    snapshot = await load_schema_snapshot(tmp_path)

    for table_name, expected_columns in CURRENTNESS_COLUMN_EXPECTATIONS:
        assert expected_columns <= snapshot.table_columns[table_name]
    for table_name, expected_sql in CURRENTNESS_SQL_EXPECTATIONS:
        assert expected_sql in snapshot.table_sql[table_name]


async def test_runtime_schema_emits_indexes_and_removes_legacy_release_flags(
    tmp_path: Path,
) -> None:
    snapshot = await load_schema_snapshot(tmp_path)

    assert "release_green_ready" not in snapshot.table_sql["assignments"]
    assert "release_blocked_ready" not in snapshot.table_sql["assignments"]
    for table_name, expected_index in INDEX_EXPECTATIONS:
        assert expected_index in snapshot.index_names[table_name]


async def load_schema_snapshot(tmp_path: Path) -> RuntimeSchemaSnapshot:
    database_path = await initialize_runtime_schema_database(tmp_path)
    return read_runtime_schema_snapshot(database_path)


def assert_targets(
    snapshot: RuntimeSchemaSnapshot,
    table_name: str,
    expected_targets: set[tuple[str, str]],
) -> None:
    assert expected_targets <= snapshot.foreign_key_targets[table_name]


def assert_columns(
    snapshot: RuntimeSchemaSnapshot,
    table_name: str,
    expected_columns: set[tuple[str, str, str]],
) -> None:
    assert expected_columns <= snapshot.foreign_key_columns[table_name]
