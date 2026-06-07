from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from autoclaw.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    PromptSendMode,
)
from autoclaw.runtime.ids import dispatch_id_for_task
from autoclaw.runtime.projection import materialize_attempt_files, render_dispatch_prompt
from autoclaw.runtime.projection.manifest import build_dispatch_manifest_projection
from tests.integration.bootstrap.fixtures import (
    seed_child_terminal_retry_checkpoint,
    task_compose_payload,
)
from tests.integration.bootstrap.support import (
    bootstrap_materialized_dispatch,
    consumed_durable_refs_section,
    require_dispatch_flow_node,
    runtime_bootstrap_context,
    seed_controller_selected_checkpoint_pair,
    stage_release_descendant_refs,
)


async def test_render_dispatch_prompt_uses_controller_selected_checkpoint_truth(
    tmp_path: Path,
) -> None:
    task_id = "task_bootstrap_controller_selected_checkpoint"
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
                compiler_version="bootstrap-controller-selected-checkpoint",
                task_compose=task_compose_payload("normal-parent-first-release"),
                latest_checkpoint=CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Current root checkpoint for the active attempt.",
                        next_step="Use only the controller-selected checkpoint for redispatch.",
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
                current_child_checkpoint_path,
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
            manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=case.dispatch,
            )
            bundle, _ = await render_dispatch_prompt(session, task_id, case.dispatch)

    assert selected_checkpoint_path.is_file() and current_child_checkpoint_path.is_file()
    assert manifest.current_context.latest_relevant_checkpoint_path == selected_checkpoint_path
    assert f"- path: {selected_checkpoint_path}" in bundle.full_markdown
    assert "Controller-selected child checkpoint for the next root review." in bundle.full_markdown
    assert "Re-read this explicit checkpoint before deciding the next turn." in bundle.full_markdown
    assert "Newer direct-child checkpoint that should stay ordinary context." not in (
        bundle.full_markdown
    )


async def test_dispatch_manifest_ignores_selected_checkpoint_without_cutoff_valid_row(
    tmp_path: Path,
) -> None:
    task_id = "task_bootstrap_selected_checkpoint_cutoff_miss"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    async with runtime_bootstrap_context(tmp_path) as runtime:
        task_root = runtime.paths.task_root
        async with runtime.session_factory() as session:
            rendered_at = datetime.now(tz=UTC)
            case = await bootstrap_materialized_dispatch(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version="bootstrap-selected-checkpoint-cutoff-miss",
                task_compose=task_compose_payload("normal-parent-first-release"),
                latest_checkpoint=CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Root is rereading child progress.",
                        next_step="Use only cutoff-valid checkpoints.",
                    ),
                ),
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
                rendered_at=rendered_at,
            )
            child_node = await require_dispatch_flow_node(
                session,
                dispatch=case.dispatch,
                node_key="review_change",
            )
            current_child_attempt_id = f"attempt.{task_id}.review_change.current"
            current_child_checkpoint_path = await seed_child_terminal_retry_checkpoint(
                session,
                task_id=task_id,
                task_root=task_root,
                dispatch=case.dispatch,
                child_node=child_node,
                attempt_id=current_child_attempt_id,
                assignment_suffix="current",
                assignment_summary="Current child attempt with the cutoff-valid checkpoint.",
                checkpoint_summary="Cutoff-valid child checkpoint that should remain visible.",
                checkpoint_next_step="Keep this as ordinary current child context.",
                checkpoint_risk="The selected child checkpoint row is still in the future.",
                recorded_at=rendered_at - timedelta(seconds=1),
                make_current=True,
            )
            selected_child_attempt_id = f"attempt.{task_id}.review_change.selected"
            selected_checkpoint_path = await seed_child_terminal_retry_checkpoint(
                session,
                task_id=task_id,
                task_root=task_root,
                dispatch=case.dispatch,
                child_node=child_node,
                attempt_id=selected_child_attempt_id,
                assignment_suffix="selected",
                assignment_summary="Selected child attempt whose checkpoint should miss cutoff.",
                checkpoint_summary="Future selected child checkpoint that must not surface.",
                checkpoint_next_step="Do not surface this checkpoint before its recorded_at.",
                checkpoint_risk="This selected checkpoint is not cutoff-valid yet.",
                recorded_at=rendered_at + timedelta(seconds=30),
                make_current=False,
            )
            case.dispatch.relevant_checkpoint_attempt_id = selected_child_attempt_id
            await materialize_attempt_files(session, task_id, current_child_attempt_id)
            await materialize_attempt_files(session, task_id, selected_child_attempt_id)
            manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=case.dispatch,
            )
            bundle, _ = await render_dispatch_prompt(session, task_id, case.dispatch)

    assert selected_checkpoint_path.is_file()
    assert current_child_checkpoint_path.is_file()
    assert manifest.current_context.latest_relevant_checkpoint_path is None
    assert str(selected_checkpoint_path) not in bundle.full_markdown


async def test_dispatch_manifest_surfaces_release_descendant_refs_from_controller_staging(
    tmp_path: Path,
) -> None:
    task_id = "task_bootstrap_release_descendant_surface"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    async with runtime_bootstrap_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            case = await bootstrap_materialized_dispatch(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                compiler_version="bootstrap-release-descendant-surface",
                task_compose=task_compose_payload("normal-parent-first-release"),
                latest_checkpoint=CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Root is preparing a release reread turn.",
                        next_step="Use controller-staged descendant evidence for release.",
                    ),
                ),
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
                rendered_at=datetime.now(tz=UTC),
            )
            descendant_checkpoint_path, descendant_artifact_path = stage_release_descendant_refs(
                case.dispatch,
                task_root=runtime.paths.task_root,
                task_id=task_id,
            )
            await session.flush()
            manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=case.dispatch,
            )
            bundle, _ = await render_dispatch_prompt(session, task_id, case.dispatch)

    assert manifest.current_context.latest_relevant_checkpoint_path is None
    assert any(
        ref.path == descendant_checkpoint_path
        for ref in manifest.current_context.current_relevant_paths
    )
    assert any(
        isinstance(ref, EvidenceRef)
        and ref.kind == EvidenceKind.ARTIFACT
        and ref.path == descendant_artifact_path
        for ref in manifest.current_context.current_relevant_paths
    )
    consumed_refs = consumed_durable_refs_section(bundle.full_markdown)
    assert "attempt.task_bootstrap_release_descendant_surface.review_change.01" in consumed_refs
    assert "review_report.v02.md" in consumed_refs
    assert "Controller-staged descendant checkpoint for the release reread." in consumed_refs
    assert "Controller-staged descendant review artifact for the release reread." in (consumed_refs)
