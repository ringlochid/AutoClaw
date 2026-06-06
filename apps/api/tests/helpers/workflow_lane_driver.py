from __future__ import annotations

from autoclaw.persistence import DispatchTurnModel, FlowModel, NodeSessionModel
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from httpx import Response
from sqlalchemy import select

from tests.helpers.runtime_support import (
    current_session_key_after_dispatch_progress_for_node,
)
from tests.helpers.workflow_lane import (
    OPERATOR_HEADERS,
    ArtifactClaims,
    JsonMap,
    ParentFirstLaneDriver,
    assert_parent_first_final_readback,
    json_map,
    wait_for_current_dispatch_progression,
    workflow_lane_runtime_context,
    write_lane_artifact,
)


async def current_session_key(driver: ParentFirstLaneDriver) -> str:
    return await current_session_key_for_node(driver)


async def current_session_key_for_node(
    driver: ParentFirstLaneDriver,
    *,
    expected_node_key: str | None = None,
) -> str:
    current_live_session_key: str | None = None

    async def live_session_ready() -> bool:
        nonlocal current_live_session_key
        async with driver.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == driver.task_id)
            )
            assert flow is not None
            if expected_node_key is not None:
                session_key = await session.scalar(
                    select(NodeSessionModel.session_key)
                    .join(
                        DispatchTurnModel,
                        DispatchTurnModel.dispatch_id == NodeSessionModel.dispatch_id,
                    )
                    .where(
                        DispatchTurnModel.task_id == driver.task_id,
                        DispatchTurnModel.node_key == expected_node_key,
                        NodeSessionModel.session_status == "live",
                        NodeSessionModel.closed_at.is_(None),
                    )
                    .order_by(NodeSessionModel.opened_at.desc())
                    .limit(1)
                )
                if isinstance(session_key, str):
                    current_live_session_key = session_key
                    return True
            if flow.current_open_dispatch_id is None:
                return False
            if expected_node_key is not None and flow.current_node_key != expected_node_key:
                return False
            dispatch_id = flow.current_open_dispatch_id
            if expected_node_key is not None:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                if dispatch is None or dispatch.node_key != expected_node_key:
                    return False
            session_key = await session.scalar(
                select(NodeSessionModel.session_key)
                .where(
                    NodeSessionModel.dispatch_id == dispatch_id,
                    NodeSessionModel.session_status == "live",
                    NodeSessionModel.closed_at.is_(None),
                )
                .order_by(NodeSessionModel.opened_at.desc())
                .limit(1)
            )
            if isinstance(session_key, str):
                current_live_session_key = session_key
                return True
        return False

    await drive_runtime_until(
        live_session_ready,
        task_id=driver.task_id,
        max_cycles=40,
    )
    assert current_live_session_key is not None
    return current_live_session_key


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
    await _checkpoint_and_close_child(
        driver,
        child_node_key=child_node_key,
        summary=checkpoint_summary,
        next_step=checkpoint_next_step,
        produced_artifacts=produced_artifacts,
    )
    return await wait_for_auto_progress(
        driver,
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
    session_key = await current_session_key_for_node(
        driver,
        expected_node_key=parent_node_key,
    )
    await _assign_child(
        driver,
        session_key=session_key,
        expected_structural_revision_id=expected_flow_revision_id,
        child_node_key=child_node_key,
        summary=summary,
        instruction=instruction,
    )
    yielded_flow = await _close_boundary(driver, session_key=session_key, boundary="yield")
    await current_session_key_after_dispatch_progress_for_node(
        session_factory=driver.session_factory,
        task_id=driver.task_id,
        client=driver.client,
        expected_active_flow_revision_id=str(yielded_flow["active_flow_revision_id"]),
        expected_node_key=child_node_key,
    )
    flow = json_map(
        await driver.client.get(
            f"/runtime/tasks/{driver.task_id}",
            headers=OPERATOR_HEADERS,
        )
    )
    assert flow["current_node_key"] == child_node_key
    return flow


async def release_current_parent(
    driver: ParentFirstLaneDriver,
    *,
    expected_node_key: str,
    expected_flow_revision_id: str,
    summary: str,
    next_step: str,
) -> JsonMap:
    session_key = await current_session_key_for_node(
        driver,
        expected_node_key=expected_node_key,
    )
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
    return await _close_boundary(driver, session_key=session_key, boundary="green")


async def continue_flow(
    driver: ParentFirstLaneDriver,
    *,
    expected_active_flow_revision_id: str,
    expected_node_key: str,
) -> JsonMap:
    await wait_for_current_dispatch_progression(driver)
    flow = json_map(
        await driver.client.post(
            f"/runtime/tasks/{driver.task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
    )
    await drive_runtime_once(task_id=driver.task_id)
    assert flow["current_node_key"] == expected_node_key
    return flow


async def wait_for_auto_progress(
    driver: ParentFirstLaneDriver,
    *,
    expected_node_key: str,
) -> JsonMap:
    flow = json_map(
        await driver.client.get(
            f"/runtime/tasks/{driver.task_id}",
            headers=OPERATOR_HEADERS,
        )
    )
    await current_session_key_after_dispatch_progress_for_node(
        session_factory=driver.session_factory,
        task_id=driver.task_id,
        client=driver.client,
        expected_active_flow_revision_id=str(flow["active_flow_revision_id"]),
        expected_node_key=expected_node_key,
    )
    flow = json_map(
        await driver.client.get(
            f"/runtime/tasks/{driver.task_id}",
            headers=OPERATOR_HEADERS,
        )
    )
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
    session_key = await current_session_key_for_node(
        driver,
        expected_node_key=child_node_key,
    )
    await _record_terminal_green_checkpoint(
        driver,
        session_key=session_key,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    return await _close_boundary(driver, session_key=session_key, boundary="green")


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

    response = await _post_callback_with_session_retry(
        driver,
        session_key=session_key,
        path=f"/callback/tasks/{driver.task_id}/checkpoint",
        json_body={"checkpoint": checkpoint},
    )
    assert response.status_code == 200, response.text
    await drive_runtime_once(task_id=driver.task_id)


async def _assign_child(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    expected_structural_revision_id: str,
    child_node_key: str,
    summary: str,
    instruction: str,
) -> None:
    response = await _post_callback_with_session_retry(
        driver,
        session_key=session_key,
        path=f"/callback/tasks/{driver.task_id}/tools/assign_child",
        json_body={
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
    response = await _post_callback_with_session_retry(
        driver,
        session_key=session_key,
        path=f"/callback/tasks/{driver.task_id}/tools/release_green",
        json_body={
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
        await _post_callback_with_session_retry(
            driver,
            session_key=session_key,
            path=f"/callback/tasks/{driver.task_id}/boundary",
            json_body={"boundary": boundary},
        )
    )
    flow = payload["flow"]
    assert isinstance(flow, dict)
    return flow


async def _post_callback_with_session_retry(
    driver: ParentFirstLaneDriver,
    *,
    session_key: str,
    path: str,
    json_body: JsonMap,
) -> Response:
    current_key = session_key
    response: Response | None = None
    for _ in range(4):
        response = await driver.client.post(
            path,
            params={"session_key": current_key},
            json=json_body,
        )
        if not _stale_dispatch_response(response):
            return response
        await drive_runtime_once(task_id=driver.task_id)
        current_key = await current_session_key(driver)
    assert response is not None
    return response


def _stale_dispatch_response(response: Response) -> bool:
    if response.status_code != 409:
        return False
    payload = response.json()
    detail = payload.get("detail") if isinstance(payload, dict) else None
    return isinstance(detail, dict) and detail.get("code") == "stale_dispatch"


__all__ = [
    "OPERATOR_HEADERS",
    "ArtifactClaims",
    "JsonMap",
    "ParentFirstLaneDriver",
    "assert_parent_first_final_readback",
    "continue_flow",
    "current_session_key",
    "json_map",
    "release_current_parent",
    "run_child_cycle",
    "start_child_from_parent",
    "wait_for_auto_progress",
    "workflow_lane_runtime_context",
    "write_lane_artifact",
]
