from __future__ import annotations

from pathlib import Path

from app.main import create_app
from httpx import ASGITransport, AsyncClient
from tests.e2e.phase4.maximal_lane.readback import assert_final_readback
from tests.e2e.phase4.maximal_lane.support import (
    MaximalLaneArtifacts,
    materialize_artifacts,
)
from tests.helpers.parent_first_lane import (
    OPERATOR_HEADERS,
    JsonMap,
    ParentFirstLaneDriver,
    json_map,
    parent_first_lane_runtime_context,
    release_current_parent,
    run_child_cycle,
    start_child_from_parent,
    wait_for_auto_progress,
)
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload


async def run_phase4_maximal_lane(tmp_path: Path) -> None:
    task_id = "task_phase4_maximal_e2e"

    async with parent_first_lane_runtime_context(tmp_path) as runtime:
        artifacts = materialize_artifacts(runtime.paths.task_root)
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("maximal-parent-first-release"),
                compiler_version="phase-4-maximal-e2e",
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
            final_green = await _run_maximal_lane(driver, artifacts)
            await assert_final_readback(driver, final_green)


async def _run_maximal_lane(
    driver: ParentFirstLaneDriver,
    artifacts: MaximalLaneArtifacts,
) -> JsonMap:
    runtime = await _read_current_runtime(driver)
    root_after_discovery = await _run_discovery_subtree(
        driver,
        runtime=runtime,
        artifacts=artifacts,
    )
    root_after_implementation = await _run_implementation_subtree(
        driver,
        root_flow=root_after_discovery,
        artifacts=artifacts,
    )
    final_green = await _run_release_subtree(
        driver,
        root_flow=root_after_implementation,
        artifacts=artifacts,
    )
    assert final_green["status"] == "succeeded"
    assert final_green["current_node_key"] == "root"
    return final_green


async def _read_current_runtime(driver: ParentFirstLaneDriver) -> JsonMap:
    runtime = json_map(
        await driver.client.get(
            f"/runtime/tasks/{driver.task_id}",
            headers=OPERATOR_HEADERS,
        )
    )
    assert runtime["status"] == "running"
    assert runtime["current_node_key"] == "root"
    return runtime


async def _run_discovery_subtree(
    driver: ParentFirstLaneDriver,
    *,
    runtime: JsonMap,
    artifacts: MaximalLaneArtifacts,
) -> JsonMap:
    discovery_flow = await start_child_from_parent(
        driver,
        parent_node_key="root",
        child_node_key="discovery",
        expected_flow_revision_id=str(runtime["active_flow_revision_id"]),
        summary="Start the bounded discovery subtree.",
        instruction="Coordinate discovery findings before downstream planning.",
    )
    discovery_flow = await run_child_cycle(
        driver,
        parent_flow=discovery_flow,
        parent_node_key="discovery",
        child_node_key="gather_evidence",
        summary="Gather discovery evidence for the auth refresh failure.",
        instruction="Publish the current findings report and supporting notes only.",
        checkpoint_summary="Discovery evidence is complete and internally consistent.",
        checkpoint_next_step="Return the surfaced findings to the discovery parent.",
        produced_artifacts=[
            {"slot": "findings_report", "path": str(artifacts.findings_report)},
            {"slot": "discovery_notes", "path": str(artifacts.discovery_notes)},
        ],
    )
    await release_current_parent(
        driver,
        expected_node_key="discovery",
        expected_flow_revision_id=str(discovery_flow["active_flow_revision_id"]),
        summary="Discovery subtree verified the current surfaced findings outputs.",
        next_step="Return surfaced discovery evidence to root for downstream planning.",
    )
    return await wait_for_auto_progress(
        driver,
        expected_node_key="root",
    )


async def _run_implementation_subtree(
    driver: ParentFirstLaneDriver,
    *,
    root_flow: JsonMap,
    artifacts: MaximalLaneArtifacts,
) -> JsonMap:
    implementation_flow = await start_child_from_parent(
        driver,
        parent_node_key="root",
        child_node_key="implementation_loop",
        expected_flow_revision_id=str(root_flow["active_flow_revision_id"]),
        summary="Start the implementation subtree from current discovery evidence.",
        instruction="Coordinate planning, implementation, review, and QA only.",
    )
    implementation_flow = await _run_implementation_loop(
        driver,
        implementation_flow=implementation_flow,
        artifacts=artifacts,
    )
    await release_current_parent(
        driver,
        expected_node_key="implementation_loop",
        expected_flow_revision_id=str(implementation_flow["active_flow_revision_id"]),
        summary="Implementation subtree verified current plan, patch, review, and QA evidence.",
        next_step="Return surfaced implementation evidence to root for final release.",
    )
    return await wait_for_auto_progress(
        driver,
        expected_node_key="root",
    )


async def _run_release_subtree(
    driver: ParentFirstLaneDriver,
    *,
    root_flow: JsonMap,
    artifacts: MaximalLaneArtifacts,
) -> JsonMap:
    root_flow = await run_child_cycle(
        driver,
        parent_flow=root_flow,
        parent_node_key="root",
        child_node_key="release_closure",
        summary="Run the bounded release closure step.",
        instruction="Use only the current surfaced discovery and implementation evidence.",
        checkpoint_summary="Release closure completed from surfaced subtree evidence.",
        checkpoint_next_step="Return closure evidence to root for final release.",
        produced_artifacts=[{"slot": "closure_report", "path": str(artifacts.closure_report)}],
    )
    return await release_current_parent(
        driver,
        expected_node_key="root",
        expected_flow_revision_id=str(root_flow["active_flow_revision_id"]),
        summary=(
            "Root verified surfaced discovery, implementation, review, QA, and release evidence."
        ),
        next_step="Close the workflow successfully.",
    )


async def _run_implementation_loop(
    driver: ParentFirstLaneDriver,
    *,
    implementation_flow: JsonMap,
    artifacts: MaximalLaneArtifacts,
) -> JsonMap:
    implementation_flow = await run_child_cycle(
        driver,
        parent_flow=implementation_flow,
        parent_node_key="implementation_loop",
        child_node_key="plan_iteration",
        summary="Publish the current delivery plan from surfaced discovery findings.",
        instruction="Use the findings report and publish the current delivery plan only.",
        checkpoint_summary="Planning completed with the current delivery plan.",
        checkpoint_next_step="Return the plan to the implementation parent.",
        produced_artifacts=[{"slot": "delivery_plan", "path": str(artifacts.delivery_plan)}],
    )
    implementation_flow = await run_child_cycle(
        driver,
        parent_flow=implementation_flow,
        parent_node_key="implementation_loop",
        child_node_key="implement_change",
        summary="Implement the scoped auth refresh fix.",
        instruction="Use the current findings and delivery plan only.",
        checkpoint_summary="Implementation completed with patch and verification evidence.",
        checkpoint_next_step="Return implementation evidence to the implementation parent.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(artifacts.change_patch)},
            {"slot": "verification_report", "path": str(artifacts.verification_report)},
        ],
    )
    implementation_flow = await run_child_cycle(
        driver,
        parent_flow=implementation_flow,
        parent_node_key="implementation_loop",
        child_node_key="review_change",
        summary="Review the scoped auth refresh patch against surfaced evidence.",
        instruction="Use only the current patch and verification evidence.",
        checkpoint_summary="Review completed with a bounded review report.",
        checkpoint_next_step="Return review evidence to the implementation parent.",
        produced_artifacts=[{"slot": "review_report", "path": str(artifacts.review_report)}],
    )
    return await run_child_cycle(
        driver,
        parent_flow=implementation_flow,
        parent_node_key="implementation_loop",
        child_node_key="qa_sweep",
        summary="Run a bounded QA sweep over surfaced implementation evidence.",
        instruction="Use the current patch, verification, and review evidence only.",
        checkpoint_summary="QA sweep completed with a bounded QA report.",
        checkpoint_next_step="Return QA evidence to the implementation parent.",
        produced_artifacts=[{"slot": "qa_report", "path": str(artifacts.qa_report)}],
    )
