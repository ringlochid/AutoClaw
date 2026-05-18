from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import httpx
from app.config import get_settings
from app.db.session import dispose_db_engine
from app.runtime.effects import wait_for_runtime_effects
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from autoclaw.openclaw.bindings import NodeToolContext, load_current_node_tool_context
from autoclaw.openclaw.common import default_transport_security as shared_transport_security
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.applications import Starlette
from tests.integration.phase3 import runtime_support as phase3_runtime_support
from tests.integration.phase3.runtime_support import (
    Phase3RuntimeApi,
    bootstrap_parent_runtime,
    continue_flow,
    persist_bootstrap,
    prepare_runtime_db,
    runtime_read_json,
)

_PHASE3_RUNTIME_API_DEPTH = 0
_NODE_MCP_MOUNT_PATH, default_transport_security = "/node/mcp/", shared_transport_security
base_phase3_runtime_api = phase3_runtime_support.phase3_runtime_api


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
    headers: dict[str, str] | None = None,
    include_operator_auth: bool = True,
) -> AsyncIterator[ClientSession]:
    request_headers = dict(headers or {})
    if include_operator_auth:
        request_headers.setdefault("Authorization", f"Bearer {get_settings().api_key}")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1",
            headers=request_headers,
        ) as client:
            async with streamable_http_client(url, http_client=client) as streams:
                async with ClientSession(*streams[:2]) as session:
                    await session.initialize()
                    try:
                        yield session
                    finally:
                        await asyncio.sleep(0.01)


def node_mcp_mount_path() -> str:
    return _NODE_MCP_MOUNT_PATH


@asynccontextmanager
async def node_mcp_client_session(app: Starlette) -> AsyncIterator[ClientSession]:
    async with mcp_client_session(
        app,
        url=f"http://127.0.0.1{node_mcp_mount_path()}",
        include_operator_auth=False,
    ) as session:
        yield session


async def load_current_node_mcp_session_key(task_id: str) -> str:
    return (await load_current_node_tool_context(task_id)).session_key


def node_tool_arguments(context: NodeToolContext, **arguments: Any) -> dict[str, Any]:
    return {
        "session_key": context.session_key,
        "task_id": context.task_id,
        **arguments,
    }


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


def tool_description(result: Any, tool_name: str) -> str:
    for tool in result.tools:
        if tool.name == tool_name:
            return cast(str, tool.description or "")
    raise AssertionError(f"missing tool '{tool_name}'")


def tool_read_only_hint(result: Any, tool_name: str) -> bool | None:
    for tool in result.tools:
        if tool.name != tool_name:
            continue
        annotations = getattr(tool, "annotations", None)
        if annotations is None:
            return None
        if isinstance(annotations, dict):
            return cast(bool | None, annotations.get("readOnlyHint"))
        return cast(bool | None, getattr(annotations, "readOnlyHint", None))
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


def tool_failure(result: Any) -> dict[str, Any]:
    assert result.isError is True, {
        "content": result.content,
        "structured": result.structuredContent,
    }
    assert result.structuredContent is not None
    failure = cast(dict[str, Any], result.structuredContent)
    assert failure.get("ok") is False
    return failure


async def call_node_parent_tool(
    session: ClientSession,
    *,
    context: NodeToolContext,
    tool_name: str,
    payload: dict[str, Any],
    active_flow_revision_id: str | None = None,
) -> dict[str, Any]:
    arguments = node_tool_arguments(
        context,
        tool_name=tool_name,
        payload=payload,
    )
    if active_flow_revision_id is not None:
        arguments["expected_structural_revision_id"] = active_flow_revision_id
    return await call_tool_structured(session, "call_parent_tool", arguments)


async def call_node_assign_child(
    session: ClientSession,
    *,
    context: NodeToolContext,
    child_node_key: str,
    summary: str,
    instruction: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    return await call_node_parent_tool(
        session,
        context=context,
        tool_name="assign_child",
        payload={
            "child_node_key": child_node_key,
            "assignment_intent": {"summary": summary, "instruction": instruction},
        },
        active_flow_revision_id=active_flow_revision_id,
    )


async def call_node_boundary(
    session: ClientSession,
    *,
    context: NodeToolContext,
    boundary: str,
) -> dict[str, Any]:
    return await call_tool_structured(
        session,
        "return_boundary",
        node_tool_arguments(context, boundary=boundary),
    )


async def bootstrap_runtime_task(
    tmp_path: Path,
    *,
    task_id: str,
    openclaw_gateway_test_server: Any,
    workflow_key: str = "normal-parent-first-release",
    workflow_definition: WorkflowDefinitionFile | None = None,
) -> tuple[Path, Path]:
    config_path = await prepare_runtime_db(tmp_path)
    _disable_watchdog_in_test_config(config_path)
    task_root = tmp_path / "task-root"
    previous_watchdog = os.environ.get("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED")
    os.environ["AUTOCLAW_RUNTIME__WATCHDOG_ENABLED"] = "false"
    try:
        with openclaw_gateway_test_server.configured_env():
            if workflow_definition is None:
                await bootstrap_parent_runtime(
                    config_path=config_path,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version=f"phase-4b-mcp-{task_id}",
                    workflow_key=workflow_key,
                )
            else:
                await persist_bootstrap(
                    config_path=config_path,
                    task_id=task_id,
                    task_root=task_root,
                    workflow_definition=workflow_definition,
                    revision_no=1,
                )
    finally:
        if previous_watchdog is None:
            os.environ.pop("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED", None)
        else:
            os.environ["AUTOCLAW_RUNTIME__WATCHDOG_ENABLED"] = previous_watchdog
    return config_path, task_root


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
