from __future__ import annotations

import argparse
import asyncio
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import get_settings
from autoclaw.persistence import RuntimeBase, TaskEventModel, TaskModel
from autoclaw.persistence.session import (
    dispose_db_engine,
    get_session_factory,
    verify_database_schema,
)
from autoclaw.runtime.contracts import TaskEventRecord
from autoclaw.runtime.task_events import (
    TaskEventCursorResetRequiredError,
    append_task_event,
    compute_task_event_hash,
    encode_task_event_cursor,
    list_task_events,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tests.integration.runtime_schema_contract.support import (
    initialize_runtime_schema_database,
    read_runtime_schema_snapshot,
)


async def test_task_event_schema_persists_timeline_fields_and_query_indexes(
    tmp_path: Path,
) -> None:
    database_path = await initialize_runtime_schema_database(tmp_path)
    snapshot = read_runtime_schema_snapshot(database_path)

    assert {
        "event_id",
        "event_seq",
        "task_id",
        "event_type",
        "event_source",
        "occurred_at",
        "flow_revision_id",
        "dispatch_id",
        "attempt_id",
        "node_key",
        "actor_ref",
        "payload",
        "prev_event_hash",
        "event_hash",
    } <= snapshot.table_columns["task_events"]
    assert {
        ("tasks", "task_id"),
        ("flow_revisions", "flow_revision_id"),
        ("dispatch_turns", "dispatch_id"),
        ("attempts", "attempt_id"),
    } <= snapshot.foreign_key_targets["task_events"]
    assert "ck_task_events_event_source" in snapshot.table_sql["task_events"]
    assert "ck_task_events_event_type" in snapshot.table_sql["task_events"]
    assert "ix_task_events_task_seq" in snapshot.index_names["task_events"]
    assert "ix_task_events_task_event" in snapshot.index_names["task_events"]


async def test_task_event_schema_verification_and_upgrade_repair_stale_event_type_constraint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    database_path = await initialize_runtime_schema_database(tmp_path)
    await dispose_db_engine()
    legacyify_task_event_type_constraint(
        database_path,
        removed_event_type="structural_revision_adopted",
    )

    try:
        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            with pytest.raises(
                RuntimeError,
                match=(
                    "task_events missing check constraint ck_task_events_event_type token "
                    "structural_revision_adopted"
                ),
            ):
                await verify_database_schema()
    finally:
        await dispose_db_engine()

    try:
        upgrade_result = await asyncio.to_thread(
            cli.cmd_db_upgrade,
            argparse.Namespace(config=str(config_path), revision="head"),
        )
    finally:
        await dispose_db_engine()

    assert upgrade_result == 0
    assert "Database repair: legacy schema backed up and reconciled" in capsys.readouterr().out
    assert (
        "structural_revision_adopted"
        in read_runtime_schema_snapshot(database_path).table_sql["task_events"]
    )

    try:
        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            await seed_task(session_factory, task_id="task_event_constraint_repaired")
            async with session_factory() as session:
                repaired_event = await append_task_event(
                    session,
                    task_id="task_event_constraint_repaired",
                    event_type="structural_revision_adopted",
                    event_source="controller",
                    payload={"operation": "update_child"},
                )
                await session.commit()
    finally:
        await dispose_db_engine()

    assert repaired_event.event_type == "structural_revision_adopted"


async def test_task_event_rows_keep_task_stream_sequence_and_hash_chain(
    tmp_path: Path,
) -> None:
    task_id = "task_event_stream_sequence"
    other_task_id = "task_event_other_stream"

    async with task_event_session_factory(tmp_path) as session_factory:
        await seed_task(session_factory, task_id=task_id)
        await seed_task(session_factory, task_id=other_task_id)

        async with session_factory() as session:
            first = await append_task_event(
                session,
                task_id=task_id,
                event_type="task_started",
                event_source="controller",
                payload={"summary": "started"},
                occurred_at=datetime(2026, 6, 25, 1, 0, tzinfo=UTC),
            )
            second = await append_task_event(
                session,
                task_id=task_id,
                event_type="dispatch_opened",
                event_source="controller",
                payload={"dispatch_id": "dispatch.task_event_stream_sequence.root.01"},
                occurred_at=datetime(2026, 6, 25, 1, 1, tzinfo=UTC),
            )
            other = await append_task_event(
                session,
                task_id=other_task_id,
                event_type="task_started",
                event_source="controller",
                payload={"summary": "other task started"},
                occurred_at=datetime(2026, 6, 25, 1, 2, tzinfo=UTC),
            )
            await session.commit()

        assert [first.event_seq, second.event_seq, other.event_seq] == [1, 2, 1]
        assert first.prev_event_hash is None
        assert second.prev_event_hash == first.event_hash
        assert first.event_hash == compute_task_event_hash(first)
        assert second.event_hash == compute_task_event_hash(second)

        async with session_factory() as session:
            persisted = list(
                await session.scalars(
                    select(TaskEventModel)
                    .where(TaskEventModel.task_id == task_id)
                    .order_by(TaskEventModel.event_seq.asc())
                )
            )

        assert [event.event_id for event in persisted] == [first.event_id, second.event_id]
        assert [event.event_hash for event in persisted] == [first.event_hash, second.event_hash]


async def test_overlapping_task_event_appends_keep_task_stream_hash_chain(
    tmp_path: Path,
) -> None:
    task_id = "task_event_overlapping_stream"

    async with task_event_session_factory(tmp_path) as session_factory:
        await seed_task(session_factory, task_id=task_id)

        first_writer_flushed = asyncio.Event()
        race_release = asyncio.Event()
        first_task = asyncio.create_task(
            append_labeled_event_with_deferred_commit(
                session_factory,
                task_id=task_id,
                label="first",
                flushed=first_writer_flushed,
                release=race_release,
            )
        )
        await asyncio.wait_for(first_writer_flushed.wait(), timeout=5)
        overlapping_tasks = [
            asyncio.create_task(
                append_labeled_event_with_deferred_commit(
                    session_factory,
                    task_id=task_id,
                    label=label,
                )
            )
            for label in ("second", "third", "fourth")
        ]

        await asyncio.sleep(0.1)
        race_release.set()
        await asyncio.wait_for(
            asyncio.gather(first_task, *overlapping_tasks),
            timeout=10,
        )

        async with session_factory() as session:
            persisted = list(
                await session.scalars(
                    select(TaskEventModel)
                    .where(TaskEventModel.task_id == task_id)
                    .order_by(TaskEventModel.event_seq.asc())
                )
            )

        persisted_records = tuple(TaskEventRecord.model_validate(row) for row in persisted)
        assert [event.event_seq for event in persisted_records] == [1, 2, 3, 4]
        assert {event.payload["label"] for event in persisted_records} == {
            "first",
            "second",
            "third",
            "fourth",
        }
        assert persisted_records[0].prev_event_hash is None
        assert persisted_records[0].event_hash == compute_task_event_hash(persisted_records[0])
        for previous_event, current_event in pairwise(persisted_records):
            assert current_event.prev_event_hash == previous_event.event_hash
            assert current_event.event_hash == compute_task_event_hash(current_event)


async def test_task_event_appends_ignore_rolled_back_stream_heads(
    tmp_path: Path,
) -> None:
    task_id = "task_event_rollback_stream_head"

    async with task_event_session_factory(tmp_path) as session_factory:
        await seed_task(session_factory, task_id=task_id)

        rolled_back_writer_flushed = asyncio.Event()
        race_release = asyncio.Event()
        rolled_back_task = asyncio.create_task(
            append_labeled_event_with_deferred_commit(
                session_factory,
                task_id=task_id,
                label="rolled-back",
                flushed=rolled_back_writer_flushed,
                release=race_release,
                should_rollback=True,
            )
        )
        await asyncio.wait_for(rolled_back_writer_flushed.wait(), timeout=5)
        committed_tasks = [
            asyncio.create_task(
                append_labeled_event_with_deferred_commit(
                    session_factory,
                    task_id=task_id,
                    label=label,
                )
            )
            for label in ("first-committed", "second-committed")
        ]

        await asyncio.sleep(0.1)
        race_release.set()
        await asyncio.wait_for(
            asyncio.gather(rolled_back_task, *committed_tasks),
            timeout=10,
        )

        async with session_factory() as session:
            persisted = list(
                await session.scalars(
                    select(TaskEventModel)
                    .where(TaskEventModel.task_id == task_id)
                    .order_by(TaskEventModel.event_seq.asc())
                )
            )

        persisted_records = tuple(TaskEventRecord.model_validate(row) for row in persisted)
        assert [event.event_seq for event in persisted_records] == [1, 2]
        assert {event.payload["label"] for event in persisted_records} == {
            "first-committed",
            "second-committed",
        }
        assert persisted_records[0].prev_event_hash is None
        assert persisted_records[0].event_hash == compute_task_event_hash(persisted_records[0])
        for previous_event, current_event in pairwise(persisted_records):
            assert current_event.prev_event_hash == previous_event.event_hash
            assert current_event.event_hash == compute_task_event_hash(current_event)


async def test_task_event_reads_resume_after_cursor_and_stop_at_through_event(
    tmp_path: Path,
) -> None:
    task_id = "task_event_cursor_read"

    async with task_event_session_factory(tmp_path) as session_factory:
        await seed_task(session_factory, task_id=task_id)

        async with session_factory() as session:
            first = await append_labeled_event(session, task_id=task_id, label="first")
            second = await append_labeled_event(session, task_id=task_id, label="second")
            third = await append_labeled_event(session, task_id=task_id, label="third")
            fourth = await append_labeled_event(session, task_id=task_id, label="fourth")
            await session.commit()

        async with session_factory() as session:
            first_page = await list_task_events(session, task_id=task_id, limit=1)
            resumed = await list_task_events(
                session,
                task_id=task_id,
                cursor=first_page.next_cursor,
                through_event_id=third.event_id,
            )

        assert [event.event_id for event in first_page.items] == [first.event_id]
        assert first_page.next_cursor is not None
        assert [event.event_id for event in resumed.items] == [second.event_id, third.event_id]
        assert fourth.event_id not in {event.event_id for event in resumed.items}
        assert resumed.through_event_id == third.event_id
        assert resumed.next_cursor is None


async def test_task_event_reads_require_cursor_reset_when_cursor_is_unknown(
    tmp_path: Path,
) -> None:
    task_id = "task_event_unknown_cursor"

    async with task_event_session_factory(tmp_path) as session_factory:
        await seed_task(session_factory, task_id=task_id)

        async with session_factory() as session:
            await append_labeled_event(session, task_id=task_id, label="first")
            await session.commit()

        async with session_factory() as session:
            with pytest.raises(TaskEventCursorResetRequiredError, match="cursor_reset_required"):
                await list_task_events(
                    session,
                    task_id=task_id,
                    cursor=encode_task_event_cursor("task-event.missing.00000001"),
                )


async def append_labeled_event(
    session: AsyncSession,
    *,
    task_id: str,
    label: str,
) -> TaskEventRecord:
    return await append_task_event(
        session,
        task_id=task_id,
        event_type="provider_event_normalized",
        event_source="controller",
        payload={"label": label},
    )


async def append_labeled_event_with_deferred_commit(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    label: str,
    flushed: asyncio.Event | None = None,
    release: asyncio.Event | None = None,
    should_rollback: bool = False,
) -> TaskEventRecord:
    async with session_factory() as session:
        event = await append_labeled_event(session, task_id=task_id, label=label)
        if flushed is not None:
            flushed.set()
        if release is not None:
            await release.wait()
        if should_rollback:
            await session.rollback()
        else:
            await session.commit()
        return event


@asynccontextmanager
async def task_event_session_factory(
    tmp_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'task-events.sqlite'}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(RuntimeBase.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def seed_task(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> None:
    async with session_factory() as session:
        session.add(
            TaskModel(
                task_id=task_id,
                task_key=task_id,
                title=f"Task event fixture {task_id}",
                summary="Task event substrate fixture.",
                instruction=None,
                workflow_key=None,
                task_root_path=str(Path("/tmp") / task_id),
            )
        )
        await session.commit()


def legacyify_task_event_type_constraint(
    database_path: Path,
    *,
    removed_event_type: str,
) -> None:
    with sqlite3.connect(database_path) as connection:
        table_sql_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'task_events'"
        ).fetchone()
        assert table_sql_row is not None and isinstance(table_sql_row[0], str)
        legacy_table_sql = table_sql_row[0].replace(f", '{removed_event_type}'", "")
        index_sql = [
            row[0]
            for row in connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'index'
                  AND tbl_name = 'task_events'
                  AND sql IS NOT NULL
                """
            ).fetchall()
            if isinstance(row[0], str)
        ]
        current_columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info('task_events')").fetchall()
            if isinstance(row[1], str)
        ]
        projection = ", ".join(f'"{column_name}"' for column_name in current_columns)
        connection.execute('ALTER TABLE "task_events" RENAME TO "task_events_legacy"')
        connection.execute(legacy_table_sql)
        connection.execute(
            f'INSERT INTO "task_events" ({projection}) '
            f'SELECT {projection} FROM "task_events_legacy"'
        )
        connection.execute('DROP TABLE "task_events_legacy"')
        for statement in index_sql:
            connection.execute(statement)
        connection.commit()
