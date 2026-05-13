from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.db.models import PolicyDefinitionModel
from app.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    PromptSendMode,
)
from app.runtime.ids import dispatch_id_for_task
from app.runtime.projection.attempt_materialization import materialize_attempt_files
from app.runtime.projection.dispatch.prompt import render_dispatch_prompt
from app.runtime.projection.manifest.materialization import materialize_manifest
from app.runtime.projection.manifest.projection import build_dispatch_manifest_projection
from app.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_dispatch,
    task_compose_payload,
)
from tests.integration.phase2.bootstrap.support import (
    bootstrap_materialized_dispatch,
    consumed_durable_refs_section,
    phase2_runtime_context,
    require_dispatch_flow_node,
    require_flow_node_by_key,
    seed_child_artifact_publication,
    seed_controller_selected_checkpoint_pair,
    stage_release_descendant_refs,
)


async def test_live_materialization_localizes_external_surfaced_refs(
    tmp_path: Path,
) -> None:
    shared_context = (tmp_path / "shared-context").resolve()
    shared_context.mkdir(parents=True)
    task_id = "task_phase2_live_localization"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    async with phase2_runtime_context(tmp_path) as runtime:
        task_root = runtime.paths.task_root
        async with runtime.session_factory() as session:
            result = await persist_bootstrap_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version="phase-2-live-localization",
                task_compose=task_compose_payload(
                    "minimal-implement-change",
                    workspace={
                        "mode": "ensure_host_path",
                        "host_path": str(tmp_path / "custom-workspace"),
                    },
                    context={
                        "mode": "use_existing_host",
                        "host_path": str(shared_context),
                    },
                ),
            )
            await materialize_manifest(session, task_id)
            await materialize_attempt_files(
                session,
                task_id,
                result.manifest.current_context.active_attempt_id,
            )
            dispatch = await seed_dispatch(
                session,
                task_id=task_id,
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
            )
            manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=dispatch,
            )
            bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

    localized_criteria_path = (
        task_root / "tmp" / "transfers" / "localized" / ("implementation_rules.v01.md")
    )
    assignment_payload = json.loads(
        (
            task_root
            / "_runtime"
            / "attempts"
            / result.manifest.current_context.active_attempt_id
            / "assignment.json"
        ).read_text(encoding="utf-8")
    )
    manifest_payload = json.loads(
        (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
    )

    assert localized_criteria_path.is_file()
    assert assignment_payload["criteria"][0]["path"] == str(localized_criteria_path)
    assert any(
        ref.kind == EvidenceKind.CRITERIA and ref.path == localized_criteria_path
        for ref in manifest.current_context.current_relevant_paths
    )
    root_node = next(node for node in manifest_payload["node_tree"] if node["node_key"] == "root")
    assert root_node["criteria"][0]["path"] == str(localized_criteria_path)
    assert str(localized_criteria_path) in bundle.full_markdown
    assert str(shared_context / "criteria" / "implementation_rules.v01.md") not in (
        bundle.full_markdown
    )


async def test_materialize_manifest_preserves_declaring_owner_for_inherited_criteria(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_manifest_criteria_owner"

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await persist_bootstrap_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                compiler_version="phase-2-manifest-criteria-owner",
                task_compose=task_compose_payload("normal-parent-first-release"),
            )
            manifest = await materialize_manifest(session, task_id)

    manifest_payload = json.loads(
        (runtime.paths.task_root / "_runtime" / "workflow-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    review_change = next(node for node in manifest.node_tree if node.node_key == "review_change")
    review_change_payload = next(
        node for node in manifest_payload["node_tree"] if node["node_key"] == "review_change"
    )

    assert review_change.criteria[0].slot == "implementation_subtree_requirements"
    assert review_change.criteria[0].owner_node_key == "implementation_subtree"
    assert review_change_payload["criteria"][0]["owner_node_key"] == "implementation_subtree"


async def test_manifest_palette_skips_corrupt_unused_current_policy_rows(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_manifest_policy_palette"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await persist_bootstrap_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                compiler_version="phase-2-structural-palette",
                task_compose=task_compose_payload("minimal-implement-change"),
            )
            policy_definition = await session.scalar(
                select(PolicyDefinitionModel)
                .options(joinedload(PolicyDefinitionModel.current_revision))
                .where(PolicyDefinitionModel.policy_key == "standard-release")
            )
            assert policy_definition is not None
            assert policy_definition.current_revision is not None
            policy_definition.current_revision.content_json = {
                "id": "standard-release",
                "description": "Corrupt current policy row that should stay unused.",
            }
            await session.flush()
            await materialize_manifest(session, task_id)
            dispatch = await seed_dispatch(
                session,
                task_id=task_id,
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
            )
            manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=dispatch,
            )
            bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

    assert manifest.structural_edit_palette is not None
    assert any(role.role == "architect" for role in manifest.structural_edit_palette.roles)
    assert not any(
        policy.policy == "standard-release" for policy in manifest.structural_edit_palette.policies
    )
    assert "architect (allowed node kinds: worker)" in bundle.full_markdown
    assert "standard-release" not in bundle.full_markdown


async def test_parent_dispatch_surfaces_current_child_artifact_refs_from_current_pointers(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_child_artifact_refs"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    published_at = datetime.now(tz=UTC) - timedelta(seconds=3)

    async with phase2_runtime_context(tmp_path) as runtime:
        task_root = runtime.paths.task_root
        async with runtime.session_factory() as session:
            await persist_bootstrap_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version="phase-2-child-artifact-refs",
                task_compose=task_compose_payload("normal-parent-first-release"),
            )
            state = await current_runtime_state(session, task_id)
            child_node = await require_flow_node_by_key(
                session,
                flow_revision_id=state.flow_revision.flow_revision_id,
                node_key="implementation_subtree",
            )
            artifact_path = await seed_child_artifact_publication(
                session,
                task_id=task_id,
                task_root=task_root,
                flow_id=state.flow.flow_id,
                flow_revision_id=state.flow_revision.flow_revision_id,
                child_node=child_node,
                slot="subtree_review_report",
                assignment_summary="Summarize the current change evidence for root review.",
                artifact_body="root review summary",
                artifact_description=(
                    "Current direct-child subtree review report for the root decision."
                ),
                published_at=published_at,
            )
            manifest = await materialize_manifest(session, task_id)
            dispatch = await seed_dispatch(
                session,
                task_id=task_id,
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
                rendered_at=published_at + timedelta(seconds=1),
            )
            bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

    assert any(
        isinstance(ref, EvidenceRef)
        and ref.kind == EvidenceKind.ARTIFACT
        and ref.slot == "subtree_review_report"
        and ref.path == artifact_path
        for ref in manifest.current_context.current_relevant_paths
    )

    manifest_payload = json.loads(
        (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
    )
    assert any(
        ref["kind"] == "artifact"
        and ref["slot"] == "subtree_review_report"
        and ref["version"] == 1
        and ref["path"] == str(artifact_path)
        for ref in manifest_payload["current_context"]["current_relevant_paths"]
    )

    consumed_refs = consumed_durable_refs_section(bundle.full_markdown)
    assert "subtree_review_report.v01.md" in consumed_refs
    assert "Current direct-child subtree review report for the root decision." in consumed_refs
    assert "version: 1" in consumed_refs


async def test_materialize_manifest_matches_open_dispatch_checkpoint_truth(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_stable_manifest_checkpoint_parity"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    selected_child_attempt_id = f"attempt.{task_id}.implementation_subtree.00"
    current_child_attempt_id = f"attempt.{task_id}.implementation_subtree.01"

    async with phase2_runtime_context(tmp_path) as runtime:
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


async def test_materialize_manifest_matches_open_dispatch_release_descendant_truth(
    tmp_path: Path,
) -> None:
    task_id = "task_phase2_stable_manifest_release_parity"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    async with phase2_runtime_context(tmp_path) as runtime:
        task_root = runtime.paths.task_root
        async with runtime.session_factory() as session:
            case = await bootstrap_materialized_dispatch(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version="phase-2-stable-manifest-release-parity",
                task_compose=task_compose_payload("normal-parent-first-release"),
                latest_checkpoint=CheckpointProjection(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoff(
                        summary="Root is preparing a release reread.",
                        next_step="Keep descendant release evidence aligned across rereads.",
                    ),
                ),
                dispatch_id=dispatch_id,
                send_mode=PromptSendMode.FULL_PROMPT,
                rendered_at=datetime.now(tz=UTC),
            )
            state = await current_runtime_state(session, task_id)
            state.flow.current_open_dispatch_id = case.dispatch.dispatch_id
            await session.flush()
            descendant_checkpoint_path, descendant_artifact_path = stage_release_descendant_refs(
                case.dispatch,
                task_root=task_root,
                task_id=task_id,
            )
            await session.flush()
            dispatch_manifest = await build_dispatch_manifest_projection(
                session,
                task_id=task_id,
                dispatch=case.dispatch,
            )
            stable_manifest = await materialize_manifest(session, task_id)

    stable_manifest_payload = json.loads(
        (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
    )

    assert descendant_checkpoint_path.is_file()
    assert descendant_artifact_path.is_file()
    assert stable_manifest.current_context.model_dump(mode="json") == (
        dispatch_manifest.current_context.model_dump(mode="json")
    )
    assert stable_manifest_payload["current_context"] == (
        dispatch_manifest.current_context.model_dump(mode="json")
    )
