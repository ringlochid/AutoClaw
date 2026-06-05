from __future__ import annotations

import argparse
import json
from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.persistence import AssignmentModel
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from autoclaw.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
)
from autoclaw.runtime.projection import materialize_attempt_files
from sqlalchemy import select
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
)


async def test_materialize_attempt_files_keeps_assignment_transient_refs_before_checkpoint(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_transient_index"

    try:
        await cli.cmd_init(
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

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                result = await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-transient-index-proof",
                )

                transient_path = task_root / "tmp" / "transfers" / "root" / "bootstrap-carryover.md"
                transient_path.parent.mkdir(parents=True, exist_ok=True)
                transient_path.write_text("keep this staged carryover", encoding="utf-8")

                assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.assignment_key == result.assignment.assignment_key
                    )
                )
                assert assignment is not None
                assignment.transient_refs_json = [
                    {
                        "kind": "transient",
                        "path": str(transient_path),
                        "description": (
                            "Assignment-staged transient carryover before any checkpoint."
                        ),
                    }
                ]
                await session.flush()

                await materialize_attempt_files(
                    session,
                    task_id,
                    result.manifest.current_context.active_attempt_id,
                )

        transient_index_path = (
            task_root
            / "_runtime"
            / "attempts"
            / result.manifest.current_context.active_attempt_id
            / "transient-index.json"
        )
        assert transient_index_path.is_file()
        assert json.loads(transient_index_path.read_text(encoding="utf-8")) == [
            {
                "path": str(transient_path),
                "description": "Assignment-staged transient carryover before any checkpoint.",
            }
        ]
    finally:
        await dispose_db_engine()


async def test_materialize_attempt_files_includes_owner_node_key_in_artifact_index(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_artifact_index_owner"
    attempt_id = f"attempt.{task_id}.root.01"
    artifact_path = (
        task_root / "outputs" / "artifacts" / "root" / "release_summary" / "release_summary.v01.md"
    )

    try:
        await cli.cmd_init(
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

        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("release summary", encoding="utf-8")

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                result = await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-artifact-index-owner",
                    latest_checkpoint=CheckpointProjection(
                        checkpoint_kind=CheckpointKind.PROGRESS,
                        handoff=CheckpointHandoff(
                            summary="Root published the release summary artifact.",
                            next_step="Stage downstream review with the current durable output.",
                        ),
                        produced_artifacts=(
                            EvidenceRef(
                                kind=EvidenceKind.ARTIFACT,
                                slot="release_summary",
                                version=1,
                                path=artifact_path,
                                description="Release summary for downstream review.",
                            ),
                        ),
                    ),
                )
                await materialize_attempt_files(session, task_id, attempt_id)

        artifact_index_path = (
            task_root / "_runtime" / "attempts" / attempt_id / "artifact-index.json"
        )
        artifact_index = json.loads(artifact_index_path.read_text(encoding="utf-8"))
        assert artifact_index["attempt_id"] == attempt_id
        assert artifact_index["node_key"] == "root"
        assert artifact_index["assignment_key"] == result.assignment.assignment_key
        assert artifact_index["publications"] == [
            {
                "owner_node_key": "root",
                "slot": "release_summary",
                "version": 1,
                "path": str(artifact_path),
                "description": "Release summary for downstream review.",
                "published_at": artifact_index["publications"][0]["published_at"],
                "became_current": True,
            }
        ]
    finally:
        await dispose_db_engine()
