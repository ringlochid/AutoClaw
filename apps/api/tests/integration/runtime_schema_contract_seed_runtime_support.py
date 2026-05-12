from __future__ import annotations

import sqlite3


def insert_flow_seed_rows(connection: sqlite3.Connection, timestamp: str) -> None:
    insert_flows(connection, timestamp)
    insert_flow_revisions(connection, timestamp)
    insert_flow_nodes(connection, timestamp)


def insert_assignment_attempt_seed_rows(
    connection: sqlite3.Connection,
    timestamp: str,
) -> None:
    insert_assignments(connection, timestamp)
    insert_attempts(connection, timestamp)


def insert_flows(connection: sqlite3.Connection, timestamp: str) -> None:
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


def insert_flow_revisions(connection: sqlite3.Connection, timestamp: str) -> None:
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


def insert_flow_nodes(connection: sqlite3.Connection, timestamp: str) -> None:
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
            flow_node_row(
                flow_node_id="flow-node.alpha.a.r1.root",
                flow_id="flow.alpha.a",
                flow_revision_id="flow-revision.alpha.a.1",
                description="Root node for revision 1",
            ),
            flow_node_row(
                flow_node_id="flow-node.alpha.a.r2.root",
                flow_id="flow.alpha.a",
                flow_revision_id="flow-revision.alpha.a.2",
                description="Root node for revision 2",
            ),
        ),
    )


def flow_node_row(
    *,
    flow_node_id: str,
    flow_id: str,
    flow_revision_id: str,
    description: str,
) -> tuple[object, ...]:
    return (
        flow_node_id,
        flow_id,
        flow_revision_id,
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
        description,
        "[]",
        None,
        None,
        "[]",
        None,
        "ready",
        None,
        0,
    )


def insert_assignments(connection: sqlite3.Connection, timestamp: str) -> None:
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


def insert_attempts(connection: sqlite3.Connection, timestamp: str) -> None:
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
