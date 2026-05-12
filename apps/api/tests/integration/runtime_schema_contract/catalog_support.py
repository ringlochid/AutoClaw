from __future__ import annotations

import sqlite3


def insert_definition_seed_rows(connection: sqlite3.Connection, timestamp: str) -> None:
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


def insert_task_and_plan_seed_rows(connection: sqlite3.Connection, timestamp: str) -> None:
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
