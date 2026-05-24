from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from app.db import DispatchTurnModel, FlowModel, FlowNodeModel
from autoclaw.openclaw.bindings import NodeToolContext, load_current_node_tool_context
from sqlalchemy import func, select
from tests.integration.phase3.runtime_support import prepare_runtime_db
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.mcp.node_dispatch_support import (
    assert_same_dispatch_node_session_state,
    load_node_tool_binding,
    revoke_same_dispatch_node_session,
    seed_live_node_mcp_dispatch,
    seed_node_mcp_session_pair,
)
from tests.integration.phase4b.mcp.node_server.inventory_support import (
    node_mcp_app,
    read_current_role_from_bound_node,
)
from tests.integration.phase4b.mcp.support import (
    bootstrap_runtime_task,
    call_tool_result,
    mcp_client_session,
    phase3_runtime_api,
    tool_failure,
)


async def assert_stale_boundary_rejected(context: NodeToolContext) -> dict[str, Any]:
    async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
        result = await call_tool_result(
            session,
            "return_boundary",
            {
                "session_key": context.session_key,
                "task_id": context.task_id,
                "boundary": "yield",
            },
        )
        failure = tool_failure(result)
        assert result.content[0].text == failure["summary"]
        return failure


async def test_phase45_node_tool_context_uses_live_node_session_not_dispatch_echo(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task.phase45.node-tool-context-live-session"
    config_path, task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            original_context = await load_current_node_tool_context(task_id)
            original_binding = await load_node_tool_binding(
                api.session_factory,
                context=original_context,
            )
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch_count_before = await session.scalar(
                    select(func.count(DispatchTurnModel.dispatch_id)).where(
                        DispatchTurnModel.task_id == task_id
                    )
                )
                assert flow is not None
                assert flow.current_open_dispatch_id == original_binding.dispatch_id

            reused_context = await seed_live_node_mcp_dispatch(
                api.session_factory,
                task_id=task_id,
                task_root=task_root,
                bootstrap_runtime=False,
            )
            reused_binding = await load_node_tool_binding(
                api.session_factory,
                context=reused_context,
            )
            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, reused_binding.dispatch_id)
                dispatch_count_after = await session.scalar(
                    select(func.count(DispatchTurnModel.dispatch_id)).where(
                        DispatchTurnModel.task_id == task_id
                    )
                )
                assert dispatch is not None
                dispatch.gateway_session_key = "dispatch.echo.should.not.authorize"
                await session.commit()

            reread_context = await load_current_node_tool_context(task_id)

    assert reused_context == original_context
    assert dispatch_count_after == dispatch_count_before
    assert reread_context.session_key == original_context.session_key


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flow_status", "control_state", "control_state_reason"),
    (
        ("running", "live", "manual_revoke"),
        ("paused", "abort_requested", "pause_requested"),
        ("cancelled", "abort_requested", "cancel_requested"),
    ),
    ids=("revoked-session", "paused-same-dispatch", "cancelled-same-dispatch"),
)
async def test_phase4b_node_mcp_rejects_same_dispatch_stale_authority(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
    flow_status: str,
    control_state: str,
    control_state_reason: str,
) -> None:
    task_id = f"task.phase4b.node-mcp-stale-{flow_status}"
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context = await seed_live_node_mcp_dispatch(
                api.session_factory, task_id=task_id, task_root=task_root
            )
            await revoke_same_dispatch_node_session(
                api.session_factory,
                task_id=task_id,
                context=context,
                flow_status=flow_status,
                control_state=control_state,
                control_state_reason=control_state_reason,
            )
            await assert_same_dispatch_node_session_state(
                api.session_factory,
                task_id=task_id,
                context=context,
                flow_status=flow_status,
                control_state=control_state,
            )
            failure = await assert_stale_boundary_rejected(context)
            if flow_status == "running":
                assert failure == {
                    "ok": False,
                    "code": "stale_dispatch",
                    "summary": "stale node session key",
                    "retryable": True,
                    "field_path": None,
                    "suggested_next_step": (
                        "Reread the current dispatch context and retry only if this node is still "
                        "the current caller for an open dispatch."
                    ),
                }
            else:
                assert failure == {
                    "ok": False,
                    "code": "illegal_state",
                    "summary": "inactive node session key",
                    "retryable": False,
                    "field_path": None,
                    "suggested_next_step": (
                        "Reread the current runtime status and dispatch context, then use the "
                        "operator lane to resume or inspect the task before sending more "
                        "callback writes."
                    ),
                }


async def test_phase4b_node_mcp_rejects_mismatched_task_and_session_authority(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_a_id = "task.phase4b.node-mcp-mismatch-a"
    task_b_id = "task.phase4b.node-mcp-mismatch-b"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context_a, context_b = await seed_node_mcp_session_pair(
                api.session_factory,
                tmp_path,
                task_a_id=task_a_id,
                task_b_id=task_b_id,
                compiler_stem="phase-4b-node-mcp-mismatch",
            )
            mismatched_context = NodeToolContext(
                task_id=context_b.task_id,
                session_key=context_a.session_key,
            )
            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                result = await call_tool_result(
                    session,
                    "return_boundary",
                    {
                        "session_key": mismatched_context.session_key,
                        "task_id": task_b_id,
                        "boundary": "yield",
                    },
                )
            failure = tool_failure(result)
            assert failure["code"] == "stale_dispatch"
            assert failure["summary"] == (
                f"session key '{context_a.session_key}' is not bound to task '{task_b_id}'"
            )
            assert failure["retryable"] is True


async def test_phase4b_node_mcp_isolates_concurrent_live_task_sessions(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_a_id = "task.phase4b.node-mcp-concurrent-a"
    task_b_id = "task.phase4b.node-mcp-concurrent-b"

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            context_a, context_b = await seed_node_mcp_session_pair(
                api.session_factory,
                tmp_path,
                task_a_id=task_a_id,
                task_b_id=task_b_id,
                compiler_stem="phase-4b-node-mcp-concurrent",
            )
            role_a, role_b = await asyncio.gather(
                read_current_role_from_bound_node(context_a),
                read_current_role_from_bound_node(context_b),
            )
            assert role_a["key"] == "researcher"
            assert role_b["key"] == "researcher"


async def test_phase4b_node_mcp_rejects_definition_lookup_from_worker_node(
    tmp_path: Path,
        openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4b_node_mcp_worker_lookup_illegal"
    config_path, _task_root = await bootstrap_runtime_task(
        tmp_path,
        task_id=task_id,
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    )

    with openclaw_gateway_test_server.configured_env():
        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                worker_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                        FlowNodeModel.node_key == flow.current_node_key,
                    )
                )
                assert worker_node is not None
                worker_node.structural_kind = "worker"
                await session.commit()
            context = await load_current_node_tool_context(task_id)
            async with mcp_client_session(node_mcp_app(), include_operator_auth=False) as session:
                result = await call_tool_result(
                    session,
                    "get_definition",
                    {
                        "session_key": context.session_key,
                        "task_id": task_id,
                        "kind": "role",
                        "key": "researcher",
                    },
                )
            failure = tool_failure(result)
            assert failure == {
                "ok": False,
                "code": "illegal_caller",
                "summary": (
                    "worker nodes cannot use current-only structural definition lookup tools"
                ),
                "retryable": False,
                "field_path": None,
                "suggested_next_step": (
                    "Reread the current dispatch context and use only the tools or boundaries "
                    "legal for this node and this open dispatch."
                ),
            }
