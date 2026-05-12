from __future__ import annotations

import sqlite3

from tests.integration.runtime_schema_contract_seed_catalog_support import (
    insert_definition_seed_rows,
    insert_task_and_plan_seed_rows,
)
from tests.integration.runtime_schema_contract_seed_runtime_support import (
    insert_assignment_attempt_seed_rows,
    insert_flow_seed_rows,
)


def seed_runtime_lineage_scope_fixture(connection: sqlite3.Connection) -> None:
    timestamp = "2026-05-06T00:00:00+00:00"
    connection.execute("PRAGMA foreign_keys = ON")
    with connection:
        insert_definition_seed_rows(connection, timestamp)
        insert_task_and_plan_seed_rows(connection, timestamp)
        insert_flow_seed_rows(connection, timestamp)
        insert_assignment_attempt_seed_rows(connection, timestamp)


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
            release_precondition_descendant_refs_json,
            accepted_boundary,
            closed_by_boundary,
            opened_at,
            rendered_at,
            closed_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        dispatch_turn_values(
            dispatch_id=dispatch_id,
            flow_id=flow_id,
            flow_revision_id=flow_revision_id,
            flow_node_id=flow_node_id,
            assignment_id=assignment_id,
            attempt_id=attempt_id,
        ),
    )


def dispatch_turn_values(
    *,
    dispatch_id: str,
    flow_id: str,
    flow_revision_id: str | None,
    flow_node_id: str | None,
    assignment_id: str | None,
    attempt_id: str | None,
) -> tuple[object, ...]:
    return (
        dispatch_id,
        flow_id,
        flow_revision_id,
        flow_node_id,
        "task.alpha.a",
        "root",
        assignment_id,
        assignment_key_for(assignment_id),
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
        None,
        "2026-05-06T00:00:00+00:00",
        "2026-05-06T00:00:00+00:00",
        None,
    )


def assignment_key_for(assignment_id: str | None) -> str | None:
    if assignment_id is None:
        return None
    if assignment_id == "assignment.alpha.a.r2.root":
        return "assignment-key.alpha.a.r2.root"
    return "assignment-key.alpha.a.r1.root"
