from __future__ import annotations

from pathlib import Path

from app.main import create_app
from httpx import ASGITransport, AsyncClient
from tests.e2e.phase3.normal_lane.readback import assert_final_readback
from tests.e2e.phase3.normal_lane.support import (
    NormalLaneArtifacts,
    materialize_artifacts,
)
from tests.helpers.parent_first_lane import (
    OPERATOR_HEADERS,
    ParentFirstLaneDriver,
    JsonMap,
    continue_flow,
    json_map,
    parent_first_lane_runtime_context,
    release_current_parent,
    run_child_cycle,
    start_child_from_parent,
)
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload


async def run_phase3_normal_lane(tmp_path: Path) -> None:
    task_id = "task_phase3_normal_e2e"

    async with parent_first_lane_runtime_context(tmp_path) as runtime:
        artifacts = materialize_artifacts(runtime.paths.task_root)
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("normal-parent-first-release"),
                compiler_version="phase-3-normal-e2e",
            )

        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            driver = ParentFirstLaneDriver(
                client=client,
                session_factory=runtime.session_factory,
                task_id=task_id,
            )
            final_green = await _run_normal_lane(driver, artifacts)
            await assert_final_readback(driver, final_green)


async def _run_normal_lane(
    driver: ParentFirstLaneDriver,
    artifacts: NormalLaneArtifacts,
) -> JsonMap:
    runtime = json_map(
        await driver.client.get(
            f"/runtime/tasks/{driver.task_id}",
            headers=OPERATOR_HEADERS,
        )
    )
    assert runtime["status"] == "running"
    assert runtime["current_node_key"] == "root"

    subtree_flow = await start_child_from_parent(
        driver,
        parent_node_key="root",
        child_node_key="implementation_subtree",
        expected_flow_revision_id=str(runtime["active_flow_revision_id"]),
        summary="Start the implementation subtree.",
        instruction="Stage only the bounded implementation subtree.",
    )
    subtree_flow = await _run_subtree_children(driver, subtree_flow, artifacts)

    subtree_green = await release_current_parent(
        driver,
        expected_node_key="implementation_subtree",
        expected_flow_revision_id=str(subtree_flow["active_flow_revision_id"]),
        summary="Implementation subtree verified current findings, patch, and review evidence.",
        next_step="Return release-ready subtree evidence to root.",
    )
    root_flow = await continue_flow(
        driver,
        expected_active_flow_revision_id=str(subtree_green["active_flow_revision_id"]),
        expected_node_key="root",
    )
    root_flow = await run_child_cycle(
        driver,
        parent_flow=root_flow,
        parent_node_key="root",
        child_node_key="release_closure",
        summary="Run the bounded release closure step.",
        instruction="Use only the current surfaced release inputs.",
        checkpoint_summary="Release closure completed from current surfaced evidence.",
        checkpoint_next_step="Return closure evidence to root for final release.",
        produced_artifacts=[{"slot": "closure_report", "path": str(artifacts.closure_report)}],
    )

    final_green = await release_current_parent(
        driver,
        expected_node_key="root",
        expected_flow_revision_id=str(root_flow["active_flow_revision_id"]),
        summary="Root verified the current subtree, review, and closure evidence.",
        next_step="Close the workflow successfully.",
    )
    assert final_green["status"] == "succeeded"
    assert final_green["current_node_key"] == "root"
    return final_green


async def _run_subtree_children(
    driver: ParentFirstLaneDriver,
    subtree_flow: JsonMap,
    artifacts: NormalLaneArtifacts,
) -> JsonMap:
    subtree_flow = await run_child_cycle(
        driver,
        parent_flow=subtree_flow,
        parent_node_key="implementation_subtree",
        child_node_key="investigate_issue",
        summary="Investigate the current auth refresh failure.",
        instruction="Publish bounded findings for downstream implementation.",
        checkpoint_summary="Investigation completed with a bounded findings report.",
        checkpoint_next_step="Return findings to the implementation subtree parent.",
        produced_artifacts=[{"slot": "findings_report", "path": str(artifacts.findings_report)}],
    )
    subtree_flow = await run_child_cycle(
        driver,
        parent_flow=subtree_flow,
        parent_node_key="implementation_subtree",
        child_node_key="implement_change",
        summary="Implement the auth refresh fix.",
        instruction="Use the current findings report and publish patch plus verification.",
        checkpoint_summary="Implementation completed with patch and verification evidence.",
        checkpoint_next_step="Return to the implementation subtree for bounded review.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(artifacts.change_patch)},
            {"slot": "verification_report", "path": str(artifacts.verification_report)},
        ],
    )
    return await run_child_cycle(
        driver,
        parent_flow=subtree_flow,
        parent_node_key="implementation_subtree",
        child_node_key="review_change",
        summary="Review the scoped auth refresh patch.",
        instruction="Use the current patch and verification evidence only.",
        checkpoint_summary="Review completed with a bounded review report.",
        checkpoint_next_step="Return review evidence to the implementation subtree parent.",
        produced_artifacts=[{"slot": "review_report", "path": str(artifacts.review_report)}],
    )
