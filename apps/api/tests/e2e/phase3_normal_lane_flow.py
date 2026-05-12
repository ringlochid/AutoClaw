from __future__ import annotations

from pathlib import Path

from app.db import DispatchCallbackBindingModel, DispatchTurnModel, FlowModel
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from tests.e2e.phase3_normal_lane_readback import assert_final_readback
from tests.e2e.phase3_normal_lane_support import (
    OPERATOR_HEADERS,
    ArtifactClaims,
    JsonMap,
    NormalLaneArtifacts,
    NormalLaneDriver,
    json_map,
    materialize_artifacts,
)
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2_runtime_bootstrap_support import phase2_runtime_context


async def run_phase3_normal_lane(tmp_path: Path) -> None:
    task_id = "task_phase3_normal_e2e"

    async with phase2_runtime_context(tmp_path) as runtime:
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
            driver = NormalLaneDriver(
                client=client,
                session_factory=runtime.session_factory,
                task_id=task_id,
            )
            final_green = await _run_normal_lane(driver, artifacts)
            await assert_final_readback(driver, final_green)
async def _run_normal_lane(
    driver: NormalLaneDriver,
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

    subtree_flow = await _start_child_from_parent(
        driver,
        parent_node_key="root",
        child_node_key="implementation_subtree",
        expected_flow_revision_id=str(runtime["active_flow_revision_id"]),
        summary="Start the implementation subtree.",
        instruction="Stage only the bounded implementation subtree.",
    )
    subtree_flow = await _run_subtree_children(driver, subtree_flow, artifacts)

    subtree_green = await _release_current_parent(
        driver,
        expected_node_key="implementation_subtree",
        expected_flow_revision_id=str(subtree_flow["active_flow_revision_id"]),
        summary="Implementation subtree verified current findings, patch, and review evidence.",
        next_step="Return release-ready subtree evidence to root.",
    )
    root_flow = await _continue_flow(
        driver,
        expected_active_flow_revision_id=str(subtree_green["active_flow_revision_id"]),
        expected_node_key="root",
    )
    root_flow = await _run_child_cycle(
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

    final_green = await _release_current_parent(
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
    driver: NormalLaneDriver,
    subtree_flow: JsonMap,
    artifacts: NormalLaneArtifacts,
) -> JsonMap:
    subtree_flow = await _run_child_cycle(
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
    subtree_flow = await _run_child_cycle(
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
    return await _run_child_cycle(
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


async def _run_child_cycle(
    driver: NormalLaneDriver,
    *,
    parent_flow: JsonMap,
    parent_node_key: str,
    child_node_key: str,
    summary: str,
    instruction: str,
    checkpoint_summary: str,
    checkpoint_next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> JsonMap:
    await _start_child_from_parent(
        driver,
        parent_node_key=parent_node_key,
        child_node_key=child_node_key,
        expected_flow_revision_id=str(parent_flow["active_flow_revision_id"]),
        summary=summary,
        instruction=instruction,
    )
    green = await _checkpoint_and_close_child(
        driver,
        child_node_key=child_node_key,
        summary=checkpoint_summary,
        next_step=checkpoint_next_step,
        produced_artifacts=produced_artifacts,
    )
    return await _continue_flow(
        driver,
        expected_active_flow_revision_id=str(green["active_flow_revision_id"]),
        expected_node_key=parent_node_key,
    )


async def _start_child_from_parent(
    driver: NormalLaneDriver,
    *,
    parent_node_key: str,
    child_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    instruction: str,
) -> JsonMap:
    session_key = await _current_session_key(driver)
    await _assign_child(
        driver,
        session_key=session_key,
        expected_structural_revision_id=expected_flow_revision_id,
        child_node_key=child_node_key,
        summary=summary,
        instruction=instruction,
    )
    yielded = await _close_boundary(driver, session_key=session_key, boundary="yield")
    assert yielded["current_node_key"] == parent_node_key
    return await _continue_flow(
        driver,
        expected_active_flow_revision_id=str(yielded["active_flow_revision_id"]),
        expected_node_key=child_node_key,
    )


async def _checkpoint_and_close_child(
    driver: NormalLaneDriver,
    *,
    child_node_key: str,
    summary: str,
    next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> JsonMap:
    session_key = await _current_session_key(driver)
    await _record_terminal_green_checkpoint(
        driver,
        session_key=session_key,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    green = await _close_boundary(driver, session_key=session_key, boundary="green")
    assert green["current_node_key"] == child_node_key
    return green


async def _release_current_parent(
    driver: NormalLaneDriver,
    *,
    expected_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    next_step: str,
) -> JsonMap:
    session_key = await _current_session_key(driver)
    await _release_green(
        driver,
        session_key=session_key,
        expected_structural_revision_id=expected_flow_revision_id,
    )
    await _record_terminal_green_checkpoint(
        driver,
        session_key=session_key,
        summary=summary,
        next_step=next_step,
    )
    green = await _close_boundary(driver, session_key=session_key, boundary="green")
    assert green["current_node_key"] == expected_node_key
    return green
async def _current_session_key(driver: NormalLaneDriver) -> str:
    async with driver.session_factory() as session:
        flow = await session.scalar(
            select(FlowModel).where(FlowModel.task_id == driver.task_id)
        )
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        binding = await session.get(
            DispatchCallbackBindingModel,
            f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
        )
        assert binding is not None
        assert binding.binding_status == "live"
        assert isinstance(binding.session_key, str)
        return binding.session_key


async def _continue_flow(
    driver: NormalLaneDriver,
    *,
    expected_active_flow_revision_id: str,
    expected_node_key: str,
) -> JsonMap:
    await _mark_open_dispatch_inactive(driver)
    flow = json_map(
        await driver.client.post(
            f"/runtime/tasks/{driver.task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
    )
    assert flow["current_node_key"] == expected_node_key
    return flow


async def _mark_open_dispatch_inactive(driver: NormalLaneDriver) -> None:
    async with driver.session_factory() as session:
        flow = await session.scalar(
            select(FlowModel).where(FlowModel.task_id == driver.task_id)
        )
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        dispatch.delivery_status = "provider_completed"
        await session.commit()


async def _assign_child(
    driver: NormalLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> None:
    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/tools/assign_child",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": "assign_child",
            "payload": {
                "child_node_key": child_node_key,
                "assignment_intent": {
                    "summary": summary,
                    "instruction": instruction,
                },
            },
            "expected_structural_revision_id": expected_structural_revision_id,
        },
    )
    assert response.status_code == 200


async def _release_green(
    driver: NormalLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
) -> None:
    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/tools/release_green",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": "release_green",
            "payload": {},
            "expected_structural_revision_id": expected_structural_revision_id,
        },
    )
    assert response.status_code == 200


async def _close_boundary(
    driver: NormalLaneDriver,
    *,
    session_key: str,
    boundary: str,
) -> JsonMap:
    payload = json_map(
        await driver.client.post(
            f"/callback/tasks/{driver.task_id}/boundary",
            headers={"X-Autoclaw-Session-Key": session_key},
            json={"boundary": boundary},
        )
    )
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return flow


async def _record_terminal_green_checkpoint(
    driver: NormalLaneDriver,
    *,
    session_key: str,
    summary: str,
    next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> None:
    checkpoint: JsonMap = {
        "checkpoint_kind": "terminal",
        "outcome": "green",
        "handoff": {
            "summary": summary,
            "next_step": next_step,
        },
    }
    if produced_artifacts is not None:
        checkpoint["produced_artifacts"] = produced_artifacts

    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/checkpoint",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"checkpoint": checkpoint},
    )
    assert response.status_code == 200
