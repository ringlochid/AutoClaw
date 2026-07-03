from __future__ import annotations

from pathlib import Path

from autoclaw.main import create_app
from httpx import ASGITransport, AsyncClient
from tests.e2e.workflows.staged.readback import assert_final_readback
from tests.e2e.workflows.staged.support import (
    StagedLaneArtifacts,
    materialize_artifacts,
)
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload
from tests.helpers.workflow_lane_driver import (
    OPERATOR_HEADERS,
    JsonMap,
    ParentFirstLaneDriver,
    json_map,
    release_current_parent,
    run_child_cycle,
    start_child_from_parent,
    wait_for_auto_progress,
    workflow_lane_runtime_context,
)


async def run_staged_delivery_release_lane(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_staged_e2e"

    async with workflow_lane_runtime_context(tmp_path) as runtime:
        artifacts = materialize_artifacts(runtime.paths.task_root)
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("staged-delivery-release"),
                compiler_version="staged-e2e",
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
                gateway_server=openclaw_gateway_test_server,
            )
            final_green = await _run_staged_lane(driver, artifacts)
            await assert_final_readback(driver, final_green)


async def _run_staged_lane(
    driver: ParentFirstLaneDriver,
    artifacts: StagedLaneArtifacts,
) -> JsonMap:
    runtime = await _read_current_runtime(driver)
    root_after_discovery = await _run_discovery_subtree(
        driver,
        runtime=runtime,
        artifacts=artifacts,
    )
    root_after_delivery = await _run_delivery_subtree(
        driver,
        root_flow=root_after_discovery,
        artifacts=artifacts,
    )
    final_green = await _run_release_subtree(
        driver,
        root_flow=root_after_delivery,
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
    artifacts: StagedLaneArtifacts,
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
        summary="Gather discovery evidence for the settings-loader cleanup.",
        instruction="Publish the current discovery brief and supporting notes only.",
        checkpoint_summary="Discovery evidence is complete and internally consistent.",
        checkpoint_next_step="Return the surfaced discovery evidence to the discovery parent.",
        produced_artifacts=[
            {"slot": "discovery_brief", "path": str(artifacts.discovery_brief)},
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


async def _run_delivery_subtree(
    driver: ParentFirstLaneDriver,
    *,
    root_flow: JsonMap,
    artifacts: StagedLaneArtifacts,
) -> JsonMap:
    delivery_flow = await start_child_from_parent(
        driver,
        parent_node_key="root",
        child_node_key="delivery_loop",
        expected_flow_revision_id=str(root_flow["active_flow_revision_id"]),
        summary="Start the delivery subtree from current discovery evidence.",
        instruction="Coordinate planning, implementation, review, and QA only.",
    )
    delivery_flow = await _run_delivery_loop(
        driver,
        delivery_flow=delivery_flow,
        artifacts=artifacts,
    )
    await release_current_parent(
        driver,
        expected_node_key="delivery_loop",
        expected_flow_revision_id=str(delivery_flow["active_flow_revision_id"]),
        summary="Delivery subtree verified current plan, patch, review, and QA evidence.",
        next_step="Return surfaced delivery evidence to root for final release.",
    )
    return await wait_for_auto_progress(
        driver,
        expected_node_key="root",
    )


async def _run_release_subtree(
    driver: ParentFirstLaneDriver,
    *,
    root_flow: JsonMap,
    artifacts: StagedLaneArtifacts,
) -> JsonMap:
    root_flow = await run_child_cycle(
        driver,
        parent_flow=root_flow,
        parent_node_key="root",
        child_node_key="release_closure",
        summary="Run the bounded release closure step.",
        instruction="Use only the current surfaced discovery and delivery evidence.",
        checkpoint_summary="Release closure completed from surfaced subtree evidence.",
        checkpoint_next_step="Return closure evidence to root for final release.",
        produced_artifacts=[{"slot": "closure_report", "path": str(artifacts.closure_report)}],
    )
    return await release_current_parent(
        driver,
        expected_node_key="root",
        expected_flow_revision_id=str(root_flow["active_flow_revision_id"]),
        summary=(
            "Root verified surfaced discovery, delivery, review, QA, and release evidence."
        ),
        next_step="Close the workflow successfully.",
    )


async def _run_delivery_loop(
    driver: ParentFirstLaneDriver,
    *,
    delivery_flow: JsonMap,
    artifacts: StagedLaneArtifacts,
) -> JsonMap:
    delivery_flow = await run_child_cycle(
        driver,
        parent_flow=delivery_flow,
        parent_node_key="delivery_loop",
        child_node_key="plan_delivery",
        summary="Publish the current delivery plan from surfaced discovery findings.",
        instruction="Use the discovery brief and publish the current delivery plan only.",
        checkpoint_summary="Planning completed with the current delivery plan.",
        checkpoint_next_step="Return the plan to the delivery parent.",
        produced_artifacts=[{"slot": "delivery_plan", "path": str(artifacts.delivery_plan)}],
    )
    delivery_flow = await run_child_cycle(
        driver,
        parent_flow=delivery_flow,
        parent_node_key="delivery_loop",
        child_node_key="implement_change",
        summary="Implement the scoped settings-loader change.",
        instruction="Use the current discovery brief and delivery plan only.",
        checkpoint_summary="Implementation completed with patch and verification evidence.",
        checkpoint_next_step="Return implementation evidence to the delivery parent.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(artifacts.change_patch)},
            {"slot": "verification_report", "path": str(artifacts.verification_report)},
        ],
    )
    delivery_flow = await run_child_cycle(
        driver,
        parent_flow=delivery_flow,
        parent_node_key="delivery_loop",
        child_node_key="review_change",
        summary="Review the scoped settings-loader patch against surfaced evidence.",
        instruction="Use only the current patch and verification evidence.",
        checkpoint_summary="Review completed with a bounded review report.",
        checkpoint_next_step="Return review evidence to the delivery parent.",
        produced_artifacts=[{"slot": "review_report", "path": str(artifacts.review_report)}],
    )
    return await run_child_cycle(
        driver,
        parent_flow=delivery_flow,
        parent_node_key="delivery_loop",
        child_node_key="qa_sweep",
        summary="Run a bounded QA sweep over surfaced implementation evidence.",
        instruction="Use the current patch, verification, and review evidence only.",
        checkpoint_summary="QA sweep completed with a bounded QA report.",
        checkpoint_next_step="Return QA evidence to the delivery parent.",
        produced_artifacts=[{"slot": "qa_report", "path": str(artifacts.qa_report)}],
    )
