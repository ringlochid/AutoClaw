from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from autoclaw.persistence import RuntimeBase
from sqlalchemy import Connection, select
from sqlalchemy.exc import IntegrityError
from tests.integration.runtime_schema_contract.catalog_fixture import seed_catalog
from tests.integration.runtime_schema_contract.runtime_lineage_fixture import (
    RuntimeIds,
    seed_runtime_scope,
)
from tests.integration.runtime_schema_contract.sqlite_schema_fixture import (
    create_runtime_schema_engine,
)

NOW = datetime(2026, 7, 18, tzinfo=UTC)
Mutation = Callable[[Connection, dict[str, RuntimeIds]], None]


def _assert_rejected(
    tmp_path: Path,
    mutation: Mutation,
    *,
    suffixes: tuple[str, ...] = ("a",),
) -> None:
    engine = create_runtime_schema_engine(tmp_path)
    try:
        with engine.begin() as connection:
            seed_catalog(connection)
            scopes = {suffix: seed_runtime_scope(connection, suffix=suffix) for suffix in suffixes}
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                mutation(connection, scopes)
    finally:
        engine.dispose()


def test_staged_child_binds_direct_parent_authoring_dispatch_and_source_revision(
    tmp_path: Path,
) -> None:
    engine = create_runtime_schema_engine(tmp_path)
    try:
        with engine.begin() as connection:
            seed_catalog(connection)
            ids = seed_runtime_scope(connection)
            _set_child_authoring_dispatch(
                connection,
                ids,
                dispatch_id=ids.root_dispatch_id,
            )
            _insert_staged_child_decision(connection, ids)
        with engine.connect() as connection:
            decision = connection.execute(
                select(RuntimeBase.metadata.tables["assignment_decisions"])
            ).one()
        assert decision.staged_child_assignment_id == ids.child_assignment_id
        assert decision.source_flow_revision_id == ids.flow_revision_id
    finally:
        engine.dispose()


def test_staged_child_rejects_a_different_authoring_dispatch(tmp_path: Path) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        ids = scopes["a"]
        _set_child_authoring_dispatch(
            connection,
            ids,
            dispatch_id=ids.child_dispatch_id,
        )
        _insert_staged_child_decision(connection, ids)

    _assert_rejected(tmp_path, mutate)


def test_assignment_decision_rejects_a_different_same_flow_revision(
    tmp_path: Path,
) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        ids = scopes["a"]
        revisions = RuntimeBase.metadata.tables["flow_revisions"]
        connection.execute(
            revisions.insert(),
            {
                "flow_revision_id": "flow-revision.a.2",
                "flow_id": ids.flow_id,
                "revision_no": 2,
                "parent_flow_revision_id": ids.flow_revision_id,
                "source_compiled_plan_id": ids.compiled_plan_id,
                "cause": "update_child",
                "created_by_dispatch_id": ids.root_dispatch_id,
                "snapshot_json": {},
                "adopted_at": NOW,
            },
        )
        _insert_release_decision(
            connection,
            ids,
            decision_id="decision.wrong-source-revision",
            source_flow_revision_id="flow-revision.a.2",
        )

    _assert_rejected(tmp_path, mutate)


def test_source_dispatch_accepts_at_most_one_terminal_checkpoint(
    tmp_path: Path,
) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        ids = scopes["a"]
        connection.execute(
            RuntimeBase.metadata.tables["attempt_checkpoints"].insert(),
            {
                "checkpoint_id": "checkpoint.a.root.duplicate-terminal",
                "task_id": ids.task_id,
                "flow_id": ids.flow_id,
                "assignment_id": ids.root_assignment_id,
                "attempt_id": ids.root_attempt_id,
                "authoring_dispatch_id": ids.root_dispatch_id,
                "checkpoint_kind": "terminal",
                "outcome": "blocked",
                "summary": "A conflicting terminal checkpoint.",
                "evidence_json": {},
                "criteria_results_json": [],
                "recorded_at": NOW,
            },
        )

    _assert_rejected(tmp_path, mutate)


def test_root_release_decision_can_select_exact_descendant_evidence(
    tmp_path: Path,
) -> None:
    engine = create_runtime_schema_engine(tmp_path)
    try:
        with engine.begin() as connection:
            seed_catalog(connection)
            ids = seed_runtime_scope(connection)
            _insert_release_decision(connection, ids, decision_id="decision.release-blocked")
            connection.execute(
                RuntimeBase.metadata.tables["assignment_decision_checkpoints"].insert(),
                {
                    "assignment_decision_checkpoint_id": "decision-checkpoint.child",
                    "assignment_decision_id": "decision.release-blocked",
                    "task_id": ids.task_id,
                    "flow_id": ids.flow_id,
                    "evidence_assignment_id": ids.child_assignment_id,
                    "evidence_attempt_id": ids.child_attempt_id,
                    "checkpoint_id": ids.child_checkpoint_id,
                    "order_index": 0,
                },
            )
            _insert_publication(
                connection,
                ids,
                publication_id="publication.child.result.1",
                version=1,
                slot="result",
                assignment_id=ids.child_assignment_id,
                attempt_id=ids.child_attempt_id,
                checkpoint_id=ids.child_checkpoint_id,
            )
            connection.execute(
                RuntimeBase.metadata.tables["assignment_decision_artifacts"].insert(),
                {
                    "assignment_decision_artifact_id": "decision-artifact.child",
                    "assignment_decision_id": "decision.release-blocked",
                    "task_id": ids.task_id,
                    "flow_id": ids.flow_id,
                    "evidence_assignment_id": ids.child_assignment_id,
                    "evidence_attempt_id": ids.child_attempt_id,
                    "checkpoint_id": ids.child_checkpoint_id,
                    "slot": "result",
                    "version": 1,
                    "artifact_publication_id": "publication.child.result.1",
                    "order_index": 0,
                },
            )
        with engine.connect() as connection:
            row = connection.execute(
                select(RuntimeBase.metadata.tables["assignment_decision_checkpoints"])
            ).one()
        assert row.evidence_assignment_id == ids.child_assignment_id
        assert row.evidence_attempt_id == ids.child_attempt_id
    finally:
        engine.dispose()


def test_release_decision_rejects_evidence_from_another_task_or_flow(
    tmp_path: Path,
) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        owner = scopes["a"]
        evidence = scopes["b"]
        _insert_release_decision(connection, owner, decision_id="decision.cross-flow")
        connection.execute(
            RuntimeBase.metadata.tables["assignment_decision_checkpoints"].insert(),
            {
                "assignment_decision_checkpoint_id": "decision-checkpoint.cross-flow",
                "assignment_decision_id": "decision.cross-flow",
                "task_id": owner.task_id,
                "flow_id": owner.flow_id,
                "evidence_assignment_id": evidence.child_assignment_id,
                "evidence_attempt_id": evidence.child_attempt_id,
                "checkpoint_id": evidence.child_checkpoint_id,
                "order_index": 0,
            },
        )

    _assert_rejected(tmp_path, mutate, suffixes=("a", "b"))


def test_artifact_versions_supersede_only_the_same_assignment_slot(
    tmp_path: Path,
) -> None:
    engine = create_runtime_schema_engine(tmp_path)
    try:
        with engine.begin() as connection:
            seed_catalog(connection)
            ids = seed_runtime_scope(connection)
            _insert_publication(
                connection,
                ids,
                publication_id="publication.root.output.1",
                version=1,
            )
            _insert_publication(
                connection,
                ids,
                publication_id="publication.root.output.2",
                version=2,
                supersedes_publication_id="publication.root.output.1",
                supersedes_version=1,
            )
            connection.execute(
                RuntimeBase.metadata.tables["artifact_current_pointers"].insert(),
                {
                    "artifact_current_pointer_id": "current.root.output",
                    "task_id": ids.task_id,
                    "flow_id": ids.flow_id,
                    "assignment_id": ids.root_assignment_id,
                    "slot": "output",
                    "current_publication_id": "publication.root.output.2",
                    "current_version": 2,
                    "attempt_id": ids.root_attempt_id,
                    "checkpoint_id": ids.root_checkpoint_id,
                    "updated_at": NOW,
                },
            )
        with engine.connect() as connection:
            pointer = connection.execute(
                select(RuntimeBase.metadata.tables["artifact_current_pointers"])
            ).one()
        assert pointer.current_publication_id == "publication.root.output.2"
        assert pointer.current_version == 2
    finally:
        engine.dispose()


def test_artifact_cannot_supersede_a_different_slot(tmp_path: Path) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        ids = scopes["a"]
        _insert_publication(
            connection,
            ids,
            publication_id="publication.output.1",
            version=1,
        )
        _insert_publication(
            connection,
            ids,
            publication_id="publication.other.2",
            version=2,
            slot="other",
            supersedes_publication_id="publication.output.1",
            supersedes_version=1,
        )

    _assert_rejected(tmp_path, mutate)


def test_artifact_current_pointer_requires_the_exact_publication_version(
    tmp_path: Path,
) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        ids = scopes["a"]
        _insert_publication(
            connection,
            ids,
            publication_id="publication.output.1",
            version=1,
        )
        connection.execute(
            RuntimeBase.metadata.tables["artifact_current_pointers"].insert(),
            {
                "artifact_current_pointer_id": "current.invalid-version",
                "task_id": ids.task_id,
                "flow_id": ids.flow_id,
                "assignment_id": ids.root_assignment_id,
                "slot": "output",
                "current_publication_id": "publication.output.1",
                "current_version": 2,
                "attempt_id": ids.root_attempt_id,
                "checkpoint_id": ids.root_checkpoint_id,
                "updated_at": NOW,
            },
        )

    _assert_rejected(tmp_path, mutate)


def test_work_plan_rejects_more_than_one_in_progress_step(tmp_path: Path) -> None:
    def mutate(connection: Connection, scopes: dict[str, RuntimeIds]) -> None:
        ids = scopes["a"]
        assignments = RuntimeBase.metadata.tables["assignments"]
        connection.execute(
            assignments.update()
            .where(assignments.c.assignment_id == ids.root_assignment_id)
            .values(work_plan_revision=1)
        )
        connection.execute(
            RuntimeBase.metadata.tables["assignment_work_plans"].insert(),
            {
                "assignment_id": ids.root_assignment_id,
                "revision": 1,
                "explanation": "Target plan",
                "authoring_dispatch_id": ids.current_dispatch_id,
                "committed_at": NOW,
            },
        )
        steps = RuntimeBase.metadata.tables["assignment_work_plan_steps"]
        connection.execute(
            steps.insert(),
            [
                {
                    "work_plan_step_id": "plan-step.1",
                    "assignment_id": ids.root_assignment_id,
                    "order_index": 0,
                    "step": "First",
                    "status": "in_progress",
                },
                {
                    "work_plan_step_id": "plan-step.2",
                    "assignment_id": ids.root_assignment_id,
                    "order_index": 1,
                    "step": "Second",
                    "status": "in_progress",
                },
            ],
        )

    _assert_rejected(tmp_path, mutate)


def _insert_release_decision(
    connection: Connection,
    ids: RuntimeIds,
    *,
    decision_id: str,
    source_flow_revision_id: str | None = None,
) -> None:
    connection.execute(
        RuntimeBase.metadata.tables["assignment_decisions"].insert(),
        {
            "assignment_decision_id": decision_id,
            "source_dispatch_id": ids.root_dispatch_id,
            "task_id": ids.task_id,
            "flow_id": ids.flow_id,
            "assignment_id": ids.root_assignment_id,
            "attempt_id": ids.root_attempt_id,
            "source_flow_revision_id": source_flow_revision_id or ids.flow_revision_id,
            "decision_kind": "release_blocked",
            "staged_child_assignment_id": None,
            "staged_child_attempt_id": None,
            "recorded_at": NOW,
        },
    )


def _set_child_authoring_dispatch(
    connection: Connection,
    ids: RuntimeIds,
    *,
    dispatch_id: str,
) -> None:
    assignments = RuntimeBase.metadata.tables["assignments"]
    connection.execute(
        assignments.update()
        .where(assignments.c.assignment_id == ids.child_assignment_id)
        .values(created_by_dispatch_id=dispatch_id)
    )


def _insert_staged_child_decision(connection: Connection, ids: RuntimeIds) -> None:
    connection.execute(
        RuntimeBase.metadata.tables["assignment_decisions"].insert(),
        {
            "assignment_decision_id": "decision.staged-child",
            "source_dispatch_id": ids.root_dispatch_id,
            "task_id": ids.task_id,
            "flow_id": ids.flow_id,
            "assignment_id": ids.root_assignment_id,
            "attempt_id": ids.root_attempt_id,
            "source_flow_revision_id": ids.flow_revision_id,
            "decision_kind": "staged_child",
            "staged_child_assignment_id": ids.child_assignment_id,
            "staged_child_attempt_id": ids.child_attempt_id,
            "recorded_at": NOW,
        },
    )


def _insert_publication(
    connection: Connection,
    ids: RuntimeIds,
    *,
    publication_id: str,
    version: int,
    slot: str = "output",
    assignment_id: str | None = None,
    attempt_id: str | None = None,
    checkpoint_id: str | None = None,
    supersedes_publication_id: str | None = None,
    supersedes_version: int | None = None,
) -> None:
    connection.execute(
        RuntimeBase.metadata.tables["artifact_publications"].insert(),
        {
            "artifact_publication_id": publication_id,
            "task_id": ids.task_id,
            "flow_id": ids.flow_id,
            "assignment_id": assignment_id or ids.root_assignment_id,
            "attempt_id": attempt_id or ids.root_attempt_id,
            "checkpoint_id": checkpoint_id or ids.root_checkpoint_id,
            "slot": slot,
            "version": version,
            "logical_path": f"outputs/artifacts/{slot}/{version}",
            "description": "Target artifact.",
            "supersedes_publication_id": supersedes_publication_id,
            "supersedes_version": supersedes_version,
            "published_at": NOW,
        },
    )
