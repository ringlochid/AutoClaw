from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.interfaces.mcp.bindings import load_current_node_tool_context
from autoclaw.persistence import FlowModel
from autoclaw.runtime.post_commit import wait_for_runtime_effects
from autoclaw.runtime.post_commit import worker as post_commit_worker
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_read_json,
)
from tests.integration.mcp.node_dispatch_support import (
    seed_node_mcp_session_pair,
)
from tests.integration.mcp.support import bootstrap_runtime_task, runtime_api_context


async def test_callback_http_accepts_explicit_session_key_query(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.callback-explicit-session-key"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            context = await load_current_node_tool_context(task_id)
            runtime = await runtime_read_json(api.client, task_id)
            response = await api.client.post(
                f"/callback/tasks/{task_id}/tools/assign_child",
                params={"session_key": context.session_key},
                json={
                    "tool_name": "assign_child",
                    "payload": {
                        "child_node_key": "change_subtree",
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


async def test_callback_http_rejects_mismatched_task_and_session_authority(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_a_id = "task.callback-mismatch-a"
    task_b_id = "task.callback-mismatch-b"

    with openclaw_gateway_test_server.configured_env():
        async with runtime_api_context(config_path) as api:
            context_a, _context_b = await seed_node_mcp_session_pair(
                api.session_factory,
                tmp_path,
                task_a_id=task_a_id,
                task_b_id=task_b_id,
                compiler_stem="callback-mismatch",
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


async def test_wait_for_runtime_effects_stays_task_scoped_while_other_tasks_pending(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
    monkeypatch: Any,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_id = "task.wait-for-runtime-effects.unrelated"
    target_task_id = "task.wait-for-runtime-effects.target"

    with openclaw_gateway_test_server.configured_env():
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=tmp_path / "task-root",
            compiler_version="wait-for-runtime-effects-unrelated",
        )

        async with runtime_api_context(config_path) as api:
            pending_checks = 0
            real_task_pending_reconcile = post_commit_worker.task_pending_reconcile

            async def task_pending_reconcile_for_test(
                session_factory: Any,
                task_id_arg: str,
            ) -> bool:
                nonlocal pending_checks
                if task_id_arg == target_task_id:
                    pending_checks += 1
                    return pending_checks == 1
                return await real_task_pending_reconcile(session_factory, task_id_arg)

            monkeypatch.setattr(
                post_commit_worker,
                "task_pending_reconcile",
                task_pending_reconcile_for_test,
            )

            await asyncio.wait_for(
                wait_for_runtime_effects(task_id=target_task_id, max_wait_seconds=5.0),
                timeout=2.0,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                assert flow.status == "running"
            assert pending_checks >= 2
