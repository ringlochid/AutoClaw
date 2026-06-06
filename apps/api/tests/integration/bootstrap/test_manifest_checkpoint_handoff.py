from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from autoclaw.persistence.models import AttemptConsumedRefModel
from autoclaw.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    NodeRuntimeFileKind,
    PromptSendMode,
)
from autoclaw.runtime.ids import dispatch_id_for_task
from autoclaw.runtime.projection import current_runtime_state, materialize_manifest
from autoclaw.runtime.projection.manifest import build_dispatch_manifest_projection
from tests.integration.bootstrap.fixtures import task_compose_payload
from tests.integration.bootstrap.support import (
    bootstrap_materialized_dispatch,
    require_dispatch_flow_node,
    runtime_bootstrap_context,
    seed_controller_selected_checkpoint_pair,
)


def _add_checkpoint_consumed_refs(
    *,
    root_attempt_id: str,
    current_checkpoint_path: Path,
    selected_checkpoint_path: Path,
) -> list[AttemptConsumedRefModel]:
    return [
        AttemptConsumedRefModel(
            attempt_consumed_ref_id=f"{root_attempt_id}.checkpoint.current",
            attempt_id=root_attempt_id,
            ref_kind=NodeRuntimeFileKind.CHECKPOINT.value,
            slot=None,
            version=None,
            path=str(current_checkpoint_path),
            description="Newer direct-child checkpoint that should stay ordinary context.",
            order_index=0,
        ),
        AttemptConsumedRefModel(
            attempt_consumed_ref_id=f"{root_attempt_id}.checkpoint.selected",
            attempt_id=root_attempt_id,
            ref_kind=NodeRuntimeFileKind.CHECKPOINT.value,
            slot=None,
            version=None,
            path=str(selected_checkpoint_path),
            description="Controller-selected child checkpoint for the paused root reread.",
            order_index=1,
        ),
    ]


async def test_materialize_manifest_matches_open_dispatch_checkpoint_truth(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_stable_manifest_checkpoint_parity"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    selected_child_attempt_id = f"attempt.{task_id}.implementation_subtree.00"
    current_child_attempt_id = f"attempt.{task_id}.implementation_subtree.01"

    async with runtime_bootstrap_context(tmp_path) as runtime:
        task_root = runtime.paths.task_root
        async with runtime.session_factory() as session:
            rendered_at = datetime.now(tz=UTC)
            case = await bootstrap_materialized_dispatch(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version="phase-2-stable-manifest-checkpoint-parity",
                task_compose=task_compose_payload("normal-parent-first-release"),
                latest_checkpoint=CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Root is rereading child checkpoint truth.",
                        next_step="Keep the stable manifest aligned with the open dispatch.",
                    ),
                ),
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
                rendered_at=rendered_at,
            )
            state = await current_runtime_state(session, task_id)
            state.flow.current_open_dispatch_id = case.dispatch.dispatch_id
            await session.flush()
            child_node = await require_dispatch_flow_node(
                session,
                dispatch=case.dispatch,
                node_key="implementation_subtree",
            )
            selected_checkpoint_path, _ = await seed_controller_selected_checkpoint_pair(
                session,
                task_id=task_id,
                task_root=task_root,
                dispatch=case.dispatch,
                child_node=child_node,
                rendered_at=rendered_at,
                selected_attempt_id=selected_child_attempt_id,
                current_attempt_id=current_child_attempt_id,
            )
            dispatch_manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=case.dispatch,
            )
            stable_manifest = await materialize_manifest(session, task_id)

    stable_manifest_payload = json.loads(
        (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
    )

    assert selected_checkpoint_path.is_file()
    assert stable_manifest.current_context.model_dump(mode="json") == (
        dispatch_manifest.current_context.model_dump(mode="json")
    )
    assert stable_manifest.current_context.latest_relevant_checkpoint_path == (
        selected_checkpoint_path
    )
    assert stable_manifest_payload["current_context"] == (
        dispatch_manifest.current_context.model_dump(mode="json")
    )


async def test_materialize_manifest_uses_controller_selected_checkpoint_without_open_dispatch(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_stable_manifest_selected_without_open_dispatch"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    selected_child_attempt_id = f"attempt.{task_id}.implementation_subtree.selected"
    current_child_attempt_id = f"attempt.{task_id}.implementation_subtree.current"

    async with runtime_bootstrap_context(tmp_path) as runtime:
        task_root = runtime.paths.task_root
        async with runtime.session_factory() as session:
            rendered_at = datetime.now(tz=UTC)
            case = await bootstrap_materialized_dispatch(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version="phase-2-stable-manifest-selected-without-open-dispatch",
                task_compose=task_compose_payload("normal-parent-first-release"),
                latest_checkpoint=CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Root is paused between review turns.",
                        next_step="Keep the controller-selected child checkpoint stable.",
                    ),
                ),
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
                rendered_at=rendered_at,
            )
            child_node = await require_dispatch_flow_node(
                session,
                dispatch=case.dispatch,
                node_key="implementation_subtree",
            )
            (
                selected_checkpoint_path,
                current_checkpoint_path,
            ) = await seed_controller_selected_checkpoint_pair(
                session,
                task_id=task_id,
                task_root=task_root,
                dispatch=case.dispatch,
                child_node=child_node,
                rendered_at=rendered_at,
                selected_attempt_id=selected_child_attempt_id,
                current_attempt_id=current_child_attempt_id,
            )
            root_attempt_id = case.result.manifest.current_context.active_attempt_id
            session.add_all(
                _add_checkpoint_consumed_refs(
                    root_attempt_id=root_attempt_id,
                    current_checkpoint_path=current_checkpoint_path,
                    selected_checkpoint_path=selected_checkpoint_path,
                )
            )
            case.dispatch.closed_at = rendered_at + timedelta(seconds=1)
            case.dispatch.relevant_checkpoint_attempt_id = selected_child_attempt_id
            await session.flush()
            stable_manifest = await materialize_manifest(session, task_id)

    checkpoint_paths = [
        ref.path
        for ref in stable_manifest.current_context.current_relevant_paths
        if getattr(ref, "kind", None) == NodeRuntimeFileKind.CHECKPOINT
    ]

    assert checkpoint_paths.index(current_checkpoint_path) < checkpoint_paths.index(
        selected_checkpoint_path
    )
    assert stable_manifest.current_context.latest_relevant_checkpoint_path == (
        selected_checkpoint_path
    )


__all__ = [
    "test_materialize_manifest_matches_open_dispatch_checkpoint_truth",
    "test_materialize_manifest_uses_controller_selected_checkpoint_without_open_dispatch",
]
