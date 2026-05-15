from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from app.config import get_settings
from app.db import (
    DispatchCallbackBindingModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
)
from app.db.session import dispose_db_engine
from app.runtime import PromptSendMode
from app.runtime.control.dispatch.callbacks import create_callback_binding
from app.runtime.effects import wait_for_runtime_effects
from autoclaw.openclaw.bindings import NodeMcpBinding, load_current_node_mcp_binding
from autoclaw.openclaw.common import default_transport_security
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.applications import Starlette
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_dispatch,
)
from tests.integration.phase3.runtime_support import (
    OPERATOR_HEADERS,
    Phase3RuntimeApi,
    bootstrap_parent_runtime,
    continue_flow,
    prepare_runtime_db,
    runtime_read_json,
)
from tests.integration.phase3.runtime_support import (
    phase3_runtime_api as base_phase3_runtime_api,
)

_PHASE3_RUNTIME_API_DEPTH = 0


def _disable_watchdog_in_test_config(config_path: Path) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    if "[runtime]" in config_text:
        if "watchdog_enabled" not in config_text:
            config_text = f"{config_text.rstrip()}\nwatchdog_enabled = false\n"
    else:
        config_text = f"{config_text.rstrip()}\n\n[runtime]\nwatchdog_enabled = false\n"
    config_path.write_text(config_text, encoding="utf-8")


@asynccontextmanager
async def mcp_client_session(
    app: Starlette,
    *,
    url: str = "http://127.0.0.1/mcp",
) -> AsyncIterator[ClientSession]:
    headers = {"Authorization": f"Bearer {get_settings().api_key}"}
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1",
            headers=headers,
        ) as client:
            async with streamable_http_client(
                url,
                http_client=client,
            ) as streams:
                async with ClientSession(*streams[:2]) as session:
                    await session.initialize()
                    yield session


@asynccontextmanager
async def phase3_runtime_api(config_path: Path) -> AsyncIterator[Phase3RuntimeApi]:
    global _PHASE3_RUNTIME_API_DEPTH
    _PHASE3_RUNTIME_API_DEPTH += 1
    try:
        async with base_phase3_runtime_api(config_path) as api:
            yield api
    finally:
        _PHASE3_RUNTIME_API_DEPTH -= 1
        if _PHASE3_RUNTIME_API_DEPTH == 0:
            await dispose_db_engine()


def tool_names(result: Any) -> tuple[str, ...]:
    return tuple(tool.name for tool in result.tools)


def tool_input_schema(result: Any, tool_name: str) -> dict[str, Any]:
    for tool in result.tools:
        if tool.name == tool_name:
            return cast(dict[str, Any], tool.inputSchema)
    raise AssertionError(f"missing tool '{tool_name}'")


async def call_tool_result(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> Any:
    return await session.call_tool(name, arguments or {})


async def call_tool_structured(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = await call_tool_result(session, name, arguments)
    assert result.isError is False, {
        "content": result.content,
        "structured": result.structuredContent,
    }
    assert result.structuredContent is not None
    return cast(dict[str, Any], result.structuredContent)


async def call_node_assign_child(
    session: ClientSession,
    *,
    child_node_key: str,
    summary: str,
    instruction: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    return await call_tool_structured(
        session,
        "call_parent_tool",
        {
            "tool_name": "assign_child",
            "payload": {
                "child_node_key": child_node_key,
                "assignment_intent": {
                    "summary": summary,
                    "instruction": instruction,
                },
            },
            "expected_structural_revision_id": active_flow_revision_id,
        },
    )


async def call_node_boundary(
    session: ClientSession,
    boundary: str,
) -> dict[str, Any]:
    return await call_tool_structured(session, "return_boundary", {"boundary": boundary})


async def bootstrap_runtime_task(
    tmp_path: Path,
    *,
    task_id: str,
    openclaw_gateway_test_server: Any,
) -> tuple[Path, Path]:
    config_path = await prepare_runtime_db(tmp_path)
    _disable_watchdog_in_test_config(config_path)
    task_root = tmp_path / "task-root"
    previous_watchdog = os.environ.get("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED")
    os.environ["AUTOCLAW_RUNTIME__WATCHDOG_ENABLED"] = "false"
    try:
        with openclaw_gateway_test_server.configured_env():
            await bootstrap_parent_runtime(
                config_path=config_path,
                task_id=task_id,
                task_root=task_root,
                compiler_version=f"phase-4b-mcp-{task_id}",
            )
    finally:
        if previous_watchdog is None:
            os.environ.pop("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED", None)
        else:
            os.environ["AUTOCLAW_RUNTIME__WATCHDOG_ENABLED"] = previous_watchdog
    return config_path, task_root


def dispatch_support_path(task_root: Path, dispatch_id: str, filename: str) -> Path:
    return task_root / "_runtime" / "dispatch" / dispatch_id / filename


async def wait_for_support_state_json(
    path: Path,
    *,
    task_id: str,
    predicate: Callable[[dict[str, Any]], bool],
    max_wait_seconds: float = 5.0,
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(path.is_file):
            payload = cast(
                dict[str, Any],
                json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8")),
            )
            if predicate(payload):
                return payload
        await wait_for_runtime_effects(task_id=task_id)
        await asyncio.sleep(0.05)
    raise AssertionError(f"support-state predicate did not pass for '{path}'")


async def continue_to_current_dispatch(config_path: Path, task_id: str) -> dict[str, Any]:
    async with phase3_runtime_api(config_path) as api:
        for _ in range(20):
            await wait_for_runtime_effects(task_id=task_id)
            flow = await runtime_read_json(api.client, task_id)
            response = await continue_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=cast(str, flow["active_flow_revision_id"]),
            )
            if response.status_code == 200:
                await wait_for_runtime_effects(task_id=task_id)
                return cast(dict[str, Any], response.json())
            detail = response.json().get("detail", {})
            if detail.get("summary") != "current dispatch is still awaiting inactivity proof":
                assert response.status_code == 200, response.json()
            await wait_for_runtime_effects(task_id=task_id)
        raise AssertionError("continue_to_current_dispatch did not become runnable in time")


async def seed_live_node_mcp_dispatch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    task_root: Path,
    compiler_version: str = "phase-4b-node-mcp-stale-authority",
) -> NodeMcpBinding:
    async with session_factory() as session:
        await persist_bootstrap_runtime(
            session,
            task_id=task_id,
            task_root=task_root,
            compiler_version=compiler_version,
        )
        dispatch = await seed_dispatch(
            session,
            task_id=task_id,
            dispatch_id=f"dispatch.{task_id}.root.01",
            send_mode=PromptSendMode.FULL_PROMPT,
        )
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
        assert flow is not None
        assert delivery_state is not None
        flow.status = "running"
        flow.current_open_dispatch_id = dispatch.dispatch_id
        dispatch.gateway_session_key = f"gateway-session.{dispatch.dispatch_id}"
        delivery_state.accepted_at = dispatch.rendered_at
        delivery_state.controller_observation_state = "live"
        session.add(
            NodeSessionModel(
                node_session_id=f"node-session.{dispatch.dispatch_id}",
                flow_node_id=dispatch.flow_node_id,
                assignment_id=dispatch.assignment_id,
                attempt_id=dispatch.attempt_id,
                dispatch_id=dispatch.dispatch_id,
                session_key=dispatch.gateway_session_key,
                session_status="live",
                opened_at=dispatch.rendered_at,
            )
        )
        await create_callback_binding(
            session,
            task_id=task_id,
            dispatch_id=dispatch.dispatch_id,
            attempt_id=cast(str, dispatch.attempt_id),
            assignment_id=cast(str, dispatch.assignment_id),
        )
        await session.commit()
    return await load_current_node_mcp_binding(task_id)


async def revoke_same_dispatch_node_mcp_binding(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    binding: NodeMcpBinding,
    flow_status: str,
    control_state: str,
    control_state_reason: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        current_dispatch = await session.get(DispatchTurnModel, binding.dispatch_id)
        callback_binding = await session.scalar(
            select(DispatchCallbackBindingModel).where(
                DispatchCallbackBindingModel.task_id == task_id,
                DispatchCallbackBindingModel.dispatch_id == binding.dispatch_id,
            )
        )
        assert flow is not None
        assert current_dispatch is not None
        assert callback_binding is not None
        flow.status = flow_status
        flow.current_open_dispatch_id = binding.dispatch_id
        current_dispatch.control_state = control_state
        current_dispatch.control_state_reason = control_state_reason
        callback_binding.binding_status = "revoked"
        callback_binding.revoked_at = datetime.now(tz=UTC)
        await session.commit()


async def assert_same_dispatch_node_mcp_binding_state(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    binding: NodeMcpBinding,
    flow_status: str,
    control_state: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        current_dispatch = await session.get(DispatchTurnModel, binding.dispatch_id)
        callback_binding = await session.scalar(
            select(DispatchCallbackBindingModel).where(
                DispatchCallbackBindingModel.task_id == task_id,
                DispatchCallbackBindingModel.dispatch_id == binding.dispatch_id,
            )
        )
        assert flow is not None
        assert current_dispatch is not None
        assert callback_binding is not None
        assert flow.current_open_dispatch_id == binding.dispatch_id
        assert flow.status == flow_status
        assert current_dispatch.control_state == control_state
        assert callback_binding.binding_status == "revoked"
        assert callback_binding.revoked_at is not None


__all__ = [
    "OPERATOR_HEADERS",
    "assert_same_dispatch_node_mcp_binding_state",
    "bootstrap_runtime_task",
    "call_node_assign_child",
    "call_node_boundary",
    "call_tool_result",
    "call_tool_structured",
    "continue_to_current_dispatch",
    "default_transport_security",
    "dispatch_support_path",
    "mcp_client_session",
    "phase3_runtime_api",
    "revoke_same_dispatch_node_mcp_binding",
    "runtime_read_json",
    "seed_live_node_mcp_dispatch",
    "tool_input_schema",
    "tool_names",
    "wait_for_support_state_json",
]
