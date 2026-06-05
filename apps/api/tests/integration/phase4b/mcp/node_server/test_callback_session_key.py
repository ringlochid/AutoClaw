from __future__ import annotations

from pathlib import Path

from autoclaw.interfaces.mcp.bindings import load_current_node_tool_context
from tests.integration.phase3.runtime_support import prepare_runtime_db, runtime_read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_dispatch_support import (
    seed_node_mcp_session_pair,
)
from tests.integration.phase4b.mcp.support import bootstrap_runtime_task, phase3_runtime_api


async def test_phase45_callback_http_accepts_explicit_session_key_query(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase45.callback-explicit-session-key"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context = await load_current_node_tool_context(task_id)
            runtime = await runtime_read_json(api.client, task_id)
            response = await api.client.post(
                f"/callback/tasks/{task_id}/tools/assign_child",
                params={"session_key": context.session_key},
                json={
                    "tool_name": "assign_child",
                    "payload": {
                        "child_node_key": "implementation_subtree",
                        "assignment_intent": {
                            "summary": "Stage via explicit callback session_key query.",
                            "instruction": "Keep the callback lane explicit.",
                        },
                    },
                    "expected_structural_revision_id": runtime["active_flow_revision_id"],
                },
            )

    assert response.status_code == 200
    assert response.json()["tool_name"] == "assign_child"


async def test_phase45_callback_http_rejects_mismatched_task_and_session_authority(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_a_id = "task.phase45.callback-mismatch-a"
    task_b_id = "task.phase45.callback-mismatch-b"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context_a, _context_b = await seed_node_mcp_session_pair(
                api.session_factory,
                tmp_path,
                task_a_id=task_a_id,
                task_b_id=task_b_id,
                compiler_stem="phase-45-callback-mismatch",
            )
            response = await api.client.post(
                f"/callback/tasks/{task_b_id}/boundary",
                params={"session_key": context_a.session_key},
                json={"boundary": "yield"},
            )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "ok": False,
        "code": "stale_dispatch",
        "summary": f"session key '{context_a.session_key}' is not bound to task '{task_b_id}'",
        "retryable": True,
        "field_path": None,
        "suggested_next_step": (
            "Reread the current dispatch context and retry only if this node is still "
            "the current caller for an open dispatch."
        ),
    }
