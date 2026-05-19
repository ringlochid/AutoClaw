from __future__ import annotations

from app.db import FlowModel, NodeSessionModel
from app.runtime.effects import wait_for_runtime_effects
from sqlalchemy import select

from tests.helpers.parent_first_lane_readback import assert_parent_first_final_readback
from tests.helpers.parent_first_lane_runtime import (
    OPERATOR_HEADERS,
    ArtifactClaims,
    JsonMap,
    ParentFirstLaneDriver,
    json_map,
    parent_first_lane_runtime_context,
    prove_open_dispatch_inactive,
    write_lane_artifact,
)


async def current_session_key(driver: ParentFirstLaneDriver) -> str:
    async with driver.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == driver.task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        session_key = await session.scalar(
            select(NodeSessionModel.session_key)
            .where(
                NodeSessionModel.dispatch_id == flow.current_open_dispatch_id,
                NodeSessionModel.session_status == "live",
                NodeSessionModel.closed_at.is_(None),
            )
            .order_by(NodeSessionModel.opened_at.desc())
            .limit(1)
        )
        assert isinstance(session_key, str)
        return session_key


async def run_child_cycle(
    driver: ParentFirstLaneDriver,
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
    await start_child_from_parent(
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
    return await continue_flow(
        driver,
        expected_active_flow_revision_id=str(green["active_flow_revision_id"]),
        expected_node_key=parent_node_key,
    )


async def start_child_from_parent(
    driver: ParentFirstLaneDriver,
    *,
    parent_node_key: str,
    child_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    instruction: str,
) -> JsonMap:
    session_key = await current_session_key(driver)
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
    return await continue_flow(
        driver,
        expected_active_flow_revision_id=str(yielded["active_flow_revision_id"]),
        expected_node_key=child_node_key,
    )


async def release_current_parent(
    driver: ParentFirstLaneDriver,
    *,
    expected_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    next_step: str,
) -> JsonMap:
    session_key = await current_session_key(driver)
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


async def continue_flow(
    driver: ParentFirstLaneDriver,
    *,
    expected_active_flow_revision_id: str,
    expected_node_key: str,
) -> JsonMap:
    await prove_open_dispatch_inactive(driver)
    flow = json_map(
        await driver.client.post(
            f"/runtime/tasks/{driver.task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
    )
    await wait_for_runtime_effects(task_id=driver.task_id)
    assert flow["current_node_key"] == expected_node_key
    return flow


async def _checkpoint_and_close_child(
    driver: ParentFirstLaneDriver,
    *,
    child_node_key: str,
    summary: str,
    next_step: str,
    produced_artifacts: ArtifactClaims | None = None,
) -> JsonMap:
    session_key = await current_session_key(driver)
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


async def _record_terminal_green_checkpoint(
    driver: ParentFirstLaneDriver,
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
        params={"session_key": session_key},
        json={"checkpoint": checkpoint},
    )
    assert response.status_code == 200, response.text
    await wait_for_runtime_effects(task_id=driver.task_id)


async def _assign_child(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> None:
    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/tools/assign_child",
        params={"session_key": session_key},
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
    assert response.status_code == 200, response.text


async def _release_green(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
) -> None:
    response = await driver.client.post(
        f"/callback/tasks/{driver.task_id}/tools/release_green",
        params={"session_key": session_key},
        json={
            "tool_name": "release_green",
            "payload": {},
            "expected_structural_revision_id": expected_structural_revision_id,
        },
    )
    assert response.status_code == 200, response.text


async def _close_boundary(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    boundary: str,
) -> JsonMap:
    payload = json_map(
        await driver.client.post(
            f"/callback/tasks/{driver.task_id}/boundary",
            params={"session_key": session_key},
            json={"boundary": boundary},
        )
    )
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return flow


__all__ = [
    "OPERATOR_HEADERS",
    "ArtifactClaims",
    "JsonMap",
    "ParentFirstLaneDriver",
    "assert_parent_first_final_readback",
    "continue_flow",
    "current_session_key",
    "json_map",
    "parent_first_lane_runtime_context",
    "release_current_parent",
    "run_child_cycle",
    "start_child_from_parent",
    "write_lane_artifact",
]
