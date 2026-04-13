from collections.abc import Sequence
from typing import Any, cast

from httpx import ASGITransport, AsyncClient

from app.main import app


def _find_node_state(flows: Sequence[dict[str, Any]], flow_node_id: str) -> str | None:
    for flow in flows:
        for node in flow["nodes"]:
            if node["id"] == flow_node_id:
                return cast(str, node["state"])
    return None


async def _bootstrap_compile_start(client: AsyncClient) -> tuple[str, str, str, str]:
    bootstrap_response = await client.post("/registry/bootstrap")
    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["workflows"] == 3

    compile_response = await client.post("/workflows/default-bugfix/compile")
    assert compile_response.status_code == 201

    compile_payload = compile_response.json()
    compiled_plan_id = compile_payload["id"]
    assert len(compile_payload["nodes"]) == 4

    compiled_plan_read_response = await client.get(f"/workflows/compiled-plans/{compiled_plan_id}")
    assert compiled_plan_read_response.status_code == 200
    compiled_plan_read_payload = compiled_plan_read_response.json()
    assert compiled_plan_read_payload["id"] == compiled_plan_id
    assert len(compiled_plan_read_payload["edges"]) == 4

    start_response = await client.post(
        "/runs/from-workflow/default-bugfix",
        json={
            "task": {
                "title": "kernel api run",
                "description": "phase three api run",
                "input_payload": {"source": "test"},
            },
            "attempt_number": 1,
        },
    )
    assert start_response.status_code == 201
    start_payload = start_response.json()
    return (
        start_payload["run_id"],
        start_payload["flow_id"],
        start_payload["first_flow_node_id"],
        compiled_plan_id,
    )


async def test_runtime_control_flow_via_api() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id, flow_id, first_flow_node_id, compiled_plan_id = await _bootstrap_compile_start(
            client
        )

        continue_response = await client.post(f"/runs/{run_id}/continue")
        assert continue_response.status_code == 200
        continue_payload = continue_response.json()
        assert continue_payload["status"] == "running"
        assert _find_node_state(continue_payload["flows"], first_flow_node_id) == "running"

        approval_response = await client.post(
            "/approvals",
            json={
                "run_id": run_id,
                "flow_node_id": first_flow_node_id,
                "reason": "need human confirmation",
                "request_payload": {"action": "sync"},
            },
        )
        assert approval_response.status_code == 201
        approval_payload = approval_response.json()
        assert approval_payload["status"] == "pending"

        inspect_response = await client.get(f"/runs/{run_id}")
        assert inspect_response.status_code == 200
        inspect_payload = inspect_response.json()
        assert inspect_payload["status"] == "blocked"
        assert inspect_payload["compiled_plan_id"] == compiled_plan_id
        assert _find_node_state(inspect_payload["flows"], first_flow_node_id) == "waiting"

        blocked_continue_response = await client.post(f"/runs/{run_id}/continue")
        assert blocked_continue_response.status_code == 409

        approval_id = approval_payload["id"]
        resolve_response = await client.post(
            f"/approvals/{approval_id}/resolve",
            json={
                "status": "approved",
                "resolution_payload": {"by": "tester"},
            },
        )
        assert resolve_response.status_code == 200

        resumed_response = await client.post(f"/runs/{run_id}/continue")
        assert resumed_response.status_code == 200
        resumed_payload = resumed_response.json()
        assert resumed_payload["status"] == "running"
        assert _find_node_state(resumed_payload["flows"], first_flow_node_id) == "running"

        checkpoint_response = await client.post(
            "/runs/checkpoints",
            json={
                "flow_id": flow_id,
                "flow_node_id": first_flow_node_id,
                "sequence_no": 1,
                "status": "green",
                "summary": "first node executed",
                "payload": {"result": "ok"},
            },
        )
        assert checkpoint_response.status_code == 201
        checkpoint_payload = checkpoint_response.json()
        assert checkpoint_payload["status"] == "green"

        post_checkpoint_response = await client.get(f"/runs/{run_id}")
        assert post_checkpoint_response.status_code == 200
        post_checkpoint_payload = post_checkpoint_response.json()
        assert post_checkpoint_payload["status"] == "running"
        assert _find_node_state(post_checkpoint_payload["flows"], first_flow_node_id) == "done"

        next_continue_response = await client.post(f"/runs/{run_id}/continue")
        assert next_continue_response.status_code == 200
        next_continue_payload = next_continue_response.json()
        running_nodes = [
            node
            for flow in next_continue_payload["flows"]
            for node in flow["nodes"]
            if node["state"] == "running"
        ]
        assert len(running_nodes) == 1
        assert running_nodes[0]["id"] != first_flow_node_id

        cancel_response = await client.post(f"/runs/{run_id}/cancel")
        assert cancel_response.status_code == 200
        cancel_payload = cancel_response.json()
        assert cancel_payload["status"] == "cancelled"
        paused_nodes = [
            node
            for flow in cancel_payload["flows"]
            for node in flow["nodes"]
            if node["state"] == "paused"
        ]
        assert paused_nodes

        checkpoints_response = await client.get(f"/runs/{run_id}/checkpoints")
        assert checkpoints_response.status_code == 200
        checkpoints_payload = checkpoints_response.json()
        assert len(checkpoints_payload) == 1
        assert checkpoints_payload[0]["summary"] == "first node executed"


async def test_rejected_approval_fails_run_via_api() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id, _flow_id, first_flow_node_id, _compiled_plan_id = await _bootstrap_compile_start(
            client
        )

        continue_response = await client.post(f"/runs/{run_id}/continue")
        assert continue_response.status_code == 200

        approval_response = await client.post(
            "/approvals",
            json={
                "run_id": run_id,
                "flow_node_id": first_flow_node_id,
                "reason": "operator rejection path",
                "request_payload": {"action": "review"},
            },
        )
        assert approval_response.status_code == 201
        approval_id = approval_response.json()["id"]

        reject_response = await client.post(
            f"/approvals/{approval_id}/resolve",
            json={
                "status": "rejected",
                "resolution_payload": {"by": "tester"},
            },
        )
        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "rejected"

        inspect_response = await client.get(f"/runs/{run_id}")
        assert inspect_response.status_code == 200
        inspect_payload = inspect_response.json()
        assert inspect_payload["status"] == "failed"
        assert _find_node_state(inspect_payload["flows"], first_flow_node_id) == "failed"

        continue_after_reject = await client.post(f"/runs/{run_id}/continue")
        assert continue_after_reject.status_code == 409
