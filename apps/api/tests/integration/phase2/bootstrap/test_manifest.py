from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.runtime import EvidenceKind, EvidenceRef, PromptSendMode
from app.runtime.ids import dispatch_id_for_task
from app.runtime.projection.attempt_materialization import materialize_attempt_files
from app.runtime.projection.dispatch.prompt import render_dispatch_prompt
from app.runtime.projection.manifest.materialization import materialize_manifest
from app.runtime.projection.manifest.projection import build_dispatch_manifest_projection
from app.runtime.projection.runtime_state import current_runtime_state
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_dispatch,
    task_compose_payload,
)
from tests.integration.phase2.bootstrap.support import (
    consumed_durable_refs_section,
    phase2_runtime_context,
    require_flow_node_by_key,
    seed_child_artifact_publication,
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
