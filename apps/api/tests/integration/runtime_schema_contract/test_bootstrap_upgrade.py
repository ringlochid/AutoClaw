from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import get_settings
from autoclaw.persistence.models import CommandRunModel
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from autoclaw.runtime.command_run.continuation import (
    command_run_continuation_context_for_dispatch,
)
from autoclaw.runtime.command_run.records import command_run_record_from_model
from autoclaw.runtime.human_request.continuation import (
    human_request_continuation_context_for_dispatch,
)
from autoclaw.runtime.human_request.service import list_human_requests
from tests.integration.runtime_schema_contract.lineage_support import (
    insert_dispatch_turn,
    seed_runtime_lineage_scope_fixture,
)
from tests.integration.runtime_schema_contract.support import (
    initialize_runtime_schema_database,
)

_TERMINAL_TASK_ID = "task.alpha.a"
_TERMINAL_FLOW_ID = "flow.alpha.a"
_TERMINAL_FLOW_REVISION_ID = "flow-revision.alpha.a.1"
_TERMINAL_FLOW_NODE_ID = "flow-node.alpha.a.r1.root"
_TERMINAL_ASSIGNMENT_ID = "assignment.alpha.a.r1.root"
_TERMINAL_ATTEMPT_ID = "attempt.alpha.a.r1.root.01"
_TERMINAL_DISPATCH_ID = "dispatch.alpha.a.terminal"
_TERMINAL_REQUEST_ID = "human-request.alpha.a.terminal"
_TERMINAL_COMMAND_RUN_ID = "command-run.alpha.a.terminal"
_TERMINAL_LOG_REF = "_runtime/dispatch/command-runs/command-run.alpha.a.terminal.log"
_TERMINAL_EVENT_TIME = "2026-05-06T00:05:00+00:00"
_TERMINAL_REQUEST_ITEMS_JSON = json.dumps(
    [
        {
            "item_id": "review_choice",
            "prompt": "Should the node proceed with this patch?",
            "options": [
                {"id": "approve", "title": "Approve"},
                {"id": "revise", "title": "Revise"},
            ],
            "recommended_option": "approve",
        }
    ]
)
_TERMINAL_REQUEST_RESPONSES_JSON = json.dumps(
    [
        {
            "item_id": "review_choice",
            "selected_option": "approve",
            "freeform_answer": None,
            "extra_notes": "Looks good.",
            "response_payload": None,
        }
    ]
)


async def test_db_upgrade_repairs_legacy_terminal_runtime_rows_for_readback_and_continuation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    database_path = await initialize_runtime_schema_database(tmp_path)
    await dispose_db_engine()
    _seed_terminal_runtime_rows(database_path)
    _legacyify_terminal_runtime_tables(database_path)

    try:
        upgrade_result = await asyncio.to_thread(
            cli.cmd_db_upgrade,
            argparse.Namespace(config=str(config_path), revision="head"),
        )
    finally:
        await dispose_db_engine()

    assert upgrade_result == 0
    captured = capsys.readouterr()
    assert "Database repair: legacy schema backed up and reconciled" in captured.out
    assert str(database_path) in captured.out
    assert "Skipped tables:" in captured.out

    with sqlite3.connect(database_path) as connection:
        human_request_row = connection.execute(
            """
            SELECT
                resolved_by_actor_ref,
                resolved_by_surface,
                resolution_policy_basis,
                resolution_note
            FROM pending_human_requests
            WHERE request_id = ?
            """,
            (_TERMINAL_REQUEST_ID,),
        ).fetchone()
        command_run_row = connection.execute(
            """
            SELECT terminal_event_source, terminal_actor_ref
            FROM command_runs
            WHERE run_id = ?
            """,
            (_TERMINAL_COMMAND_RUN_ID,),
        ).fetchone()

    assert human_request_row == (
        None,
        "control_api",
        "task_authorized_human_request_resolution",
        None,
    )
    assert command_run_row == ("controller", None)

    with cli.command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            human_requests = await list_human_requests(session, task_id=_TERMINAL_TASK_ID)
            human_request_context = await human_request_continuation_context_for_dispatch(
                session,
                task_id=_TERMINAL_TASK_ID,
                previous_dispatch_id=_TERMINAL_DISPATCH_ID,
            )
            command_run_context = await command_run_continuation_context_for_dispatch(
                session,
                task_id=_TERMINAL_TASK_ID,
                previous_dispatch_id=_TERMINAL_DISPATCH_ID,
            )

        await dispose_db_engine()

    assert [item.request.request_id for item in human_requests.items] == [_TERMINAL_REQUEST_ID]
    assert human_requests.items[0].resolution is not None
    assert human_requests.items[0].resolution.resolution_kind == "answered"
    assert human_requests.items[0].resolution.resolved_by_actor_ref is None
    assert human_request_context is not None
    assert human_request_context.request.request_id == _TERMINAL_REQUEST_ID
    assert human_request_context.resolution is not None
    assert human_request_context.resolution.resolution_kind == "answered"
    assert human_request_context.resolution.resolved_by_actor_ref is None
    assert command_run_context is not None
    assert command_run_context.run_id == _TERMINAL_COMMAND_RUN_ID
    assert command_run_context.terminal_event_source == "controller"
    assert command_run_context.terminal_actor_ref is None


@pytest.mark.parametrize(
    ("state", "terminal_summary", "ended_at", "expected_terminal_event_source"),
    (
        ("cancellation_requested", None, None, None),
        ("failed", "command failed with exit code 7", _TERMINAL_EVENT_TIME, "controller"),
        ("timed_out", "command timed out after 600 seconds", _TERMINAL_EVENT_TIME, "controller"),
    ),
)
def test_command_run_record_readback_only_uses_cancel_provenance_for_cancelled_rows(
    state: str,
    terminal_summary: str | None,
    ended_at: str | None,
    expected_terminal_event_source: str | None,
) -> None:
    command_run_model = _legacy_command_run_model_for_readback(
        state=state,
        terminal_summary=terminal_summary,
        ended_at=ended_at,
        cancellation_requested_by_actor_ref="operator.alice",
    )

    command_run_record = command_run_record_from_model(command_run_model)

    assert command_run_record.terminal_event_source == expected_terminal_event_source
    assert command_run_record.terminal_actor_ref is None


def _seed_terminal_runtime_rows(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        insert_dispatch_turn(
            connection,
            dispatch_id=_TERMINAL_DISPATCH_ID,
            flow_id=_TERMINAL_FLOW_ID,
            flow_revision_id=_TERMINAL_FLOW_REVISION_ID,
            flow_node_id=_TERMINAL_FLOW_NODE_ID,
            assignment_id=_TERMINAL_ASSIGNMENT_ID,
            attempt_id=_TERMINAL_ATTEMPT_ID,
        )
        _insert_terminal_human_request(connection)
        _insert_terminal_command_run(connection)
        _insert_terminal_task_events(connection)
        connection.commit()


def _insert_terminal_human_request(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO pending_human_requests (
            request_id,
            task_id,
            flow_id,
            flow_revision_id,
            flow_node_id,
            assignment_id,
            attempt_id,
            dispatch_id,
            requester_node_key,
            kind,
            title,
            summary,
            items_json,
            timeout_json,
            suggested_human_instruction,
            status,
            resolution_kind,
            item_responses_json,
            resolved_at,
            resolved_by_actor_ref,
            resolved_by_surface,
            resolution_policy_basis,
            resolution_note,
            opened_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _TERMINAL_REQUEST_ID,
            _TERMINAL_TASK_ID,
            _TERMINAL_FLOW_ID,
            _TERMINAL_FLOW_REVISION_ID,
            _TERMINAL_FLOW_NODE_ID,
            _TERMINAL_ASSIGNMENT_ID,
            _TERMINAL_ATTEMPT_ID,
            _TERMINAL_DISPATCH_ID,
            "root",
            "review",
            "Review implementation patch",
            "The node needs a human review before continuing.",
            _TERMINAL_REQUEST_ITEMS_JSON,
            json.dumps({"due_at": None, "default_behavior": None}),
            "Inspect the patch before answering.",
            "resolved",
            "answered",
            _TERMINAL_REQUEST_RESPONSES_JSON,
            _TERMINAL_EVENT_TIME,
            "control_api",
            "control_api",
            "task_authorized_human_request_resolution",
            None,
            "2026-05-06T00:00:00+00:00",
            _TERMINAL_EVENT_TIME,
        ),
    )


def _insert_terminal_command_run(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO command_runs (
            run_id,
            task_id,
            flow_id,
            flow_revision_id,
            flow_node_id,
            assignment_id,
            attempt_id,
            dispatch_id,
            requester_node_key,
            command,
            description,
            workdir,
            timeout_seconds,
            state,
            latest_update,
            latest_log_ref,
            terminal_summary,
            terminal_exit_code,
            terminal_signal,
            terminal_log_ref,
            terminal_event_source,
            terminal_actor_ref,
            cancellation_requested_at,
            cancellation_requested_by_actor_ref,
            created_at,
            started_at,
            ended_at,
            updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            _TERMINAL_COMMAND_RUN_ID,
            _TERMINAL_TASK_ID,
            _TERMINAL_FLOW_ID,
            _TERMINAL_FLOW_REVISION_ID,
            _TERMINAL_FLOW_NODE_ID,
            _TERMINAL_ASSIGNMENT_ID,
            _TERMINAL_ATTEMPT_ID,
            _TERMINAL_DISPATCH_ID,
            "root",
            "pytest apps/api/tests/unit -q",
            "Run targeted tests.",
            "workspace",
            600,
            "failed",
            "command failed with exit code 7",
            _TERMINAL_LOG_REF,
            "command failed with exit code 7",
            7,
            None,
            _TERMINAL_LOG_REF,
            "controller",
            None,
            None,
            "operator.alice",
            "2026-05-06T00:01:00+00:00",
            "2026-05-06T00:02:00+00:00",
            _TERMINAL_EVENT_TIME,
            _TERMINAL_EVENT_TIME,
        ),
    )


def _insert_terminal_task_events(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO task_events (
            event_id,
            event_seq,
            task_id,
            event_type,
            event_source,
            occurred_at,
            flow_revision_id,
            dispatch_id,
            attempt_id,
            node_key,
            actor_ref,
            payload,
            prev_event_hash,
            event_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                "task-event.human-request.terminal",
                1,
                _TERMINAL_TASK_ID,
                "human_request_resolved",
                "control_api",
                _TERMINAL_EVENT_TIME,
                _TERMINAL_FLOW_REVISION_ID,
                _TERMINAL_DISPATCH_ID,
                _TERMINAL_ATTEMPT_ID,
                "root",
                "control_api",
                json.dumps(
                    {
                        "request_id": _TERMINAL_REQUEST_ID,
                        "status": "resolved",
                        "resolution_kind": "answered",
                        "resolved_by_actor_ref": "control_api",
                    }
                ),
                None,
                "hash.task-event.human-request.terminal",
            ),
            (
                "task-event.command-run.terminal",
                2,
                _TERMINAL_TASK_ID,
                "command_run_failed",
                "controller",
                _TERMINAL_EVENT_TIME,
                _TERMINAL_FLOW_REVISION_ID,
                _TERMINAL_DISPATCH_ID,
                _TERMINAL_ATTEMPT_ID,
                "root",
                None,
                json.dumps(
                    {
                        "run_id": _TERMINAL_COMMAND_RUN_ID,
                        "state": "failed",
                        "summary": "command failed with exit code 7",
                        "exit_code": 7,
                        "signal": None,
                        "ended_at": _TERMINAL_EVENT_TIME,
                        "log_ref": _TERMINAL_LOG_REF,
                    }
                ),
                "hash.task-event.human-request.terminal",
                "hash.task-event.command-run.terminal",
            ),
        ),
    )


def _legacyify_terminal_runtime_tables(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        _rewrite_table_without_columns(
            connection,
            table_name="pending_human_requests",
            removed_columns=(
                "resolved_by_surface",
                "resolution_policy_basis",
                "resolution_note",
            ),
        )
        _rewrite_table_without_columns(
            connection,
            table_name="command_runs",
            removed_columns=("terminal_event_source", "terminal_actor_ref"),
        )
        connection.commit()


def _rewrite_table_without_columns(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    removed_columns: tuple[str, ...],
) -> None:
    current_columns = [
        row[1]
        for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        if isinstance(row[1], str) and row[1] not in removed_columns
    ]
    projection = ", ".join(f'"{column_name}"' for column_name in current_columns)
    legacy_table_name = f"{table_name}_legacy"
    connection.execute(
        f'CREATE TABLE "{legacy_table_name}" AS SELECT {projection} FROM "{table_name}"'
    )
    connection.execute(f'DROP TABLE "{table_name}"')
    connection.execute(f'ALTER TABLE "{legacy_table_name}" RENAME TO "{table_name}"')


def _legacy_command_run_model_for_readback(
    *,
    state: str,
    terminal_summary: str | None,
    ended_at: str | None,
    cancellation_requested_by_actor_ref: str | None,
) -> CommandRunModel:
    created_at = datetime(2026, 5, 6, 0, 1, tzinfo=UTC)
    started_at = datetime(2026, 5, 6, 0, 2, tzinfo=UTC)
    ended_at_value = datetime.fromisoformat(ended_at) if ended_at is not None else None
    terminal_log_ref = _TERMINAL_LOG_REF if terminal_summary is not None else None
    latest_update = terminal_summary or "operator requested command-run cancellation"
    return cast(
        CommandRunModel,
        SimpleNamespace(
            run_id="command-run.legacy.readback",
            task_id=_TERMINAL_TASK_ID,
            dispatch_id=_TERMINAL_DISPATCH_ID,
            attempt_id=_TERMINAL_ATTEMPT_ID,
            command="pytest apps/api/tests/unit -q",
            description="Run targeted tests.",
            workdir="workspace",
            state=state,
            created_at=created_at,
            started_at=started_at,
            ended_at=ended_at_value,
            timeout_seconds=600,
            latest_update=latest_update,
            latest_log_ref=_TERMINAL_LOG_REF,
            cancellation_requested_at=created_at,
            cancellation_requested_by_actor_ref=cancellation_requested_by_actor_ref,
            terminal_summary=terminal_summary,
            terminal_exit_code=7 if state == "failed" else None,
            terminal_signal=None,
            terminal_log_ref=terminal_log_ref,
            terminal_event_source=None,
            terminal_actor_ref=None,
        ),
    )
