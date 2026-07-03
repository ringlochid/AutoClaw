from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, cast

import httpx
from autoclaw.config import get_settings
from autoclaw.definitions.contracts.workflow import WorkflowDefinitionFile
from autoclaw.interfaces.cli.support import temporary_env
from autoclaw.interfaces.mcp.bindings import NodeToolContext, load_current_node_tool_context
from autoclaw.interfaces.mcp.transport import (
    default_transport_security as shared_transport_security,
)
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.post_commit import stop_runtime_effect_runner, wait_for_runtime_effects
from autoclaw.runtime.watchdog import stop_runtime_watchdog
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.applications import Starlette
from tests.helpers import runtime_support
from tests.helpers.openclaw_gateway_support import agent_wait_fixture
from tests.helpers.runtime_support import set_runtime_watchdog_enabled

_RUNTIME_API_DEPTH = 0
_NODE_MCP_MOUNT_PATH, default_transport_security = "/node/mcp/", shared_transport_security
_MCP_COMPOSE_GATEWAY_BASE_URL = "http://127.0.0.1:19055"
_MCP_COMPOSE_GATEWAY_TOKEN = "gateway-config-token"
bootstrap_parent_runtime = runtime_support.bootstrap_parent_runtime
base_runtime_api_context = runtime_support.runtime_api_context
persist_bootstrap = runtime_support.persist_bootstrap
prepare_runtime_db = runtime_support.prepare_runtime_db


@contextmanager
def _runtime_startup_gateway_env() -> Iterator[None]:
    base_url = os.environ.get("AUTOCLAW_OPENCLAW__BASE_URL")
    gateway_token = os.environ.get("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN")
    if base_url != _MCP_COMPOSE_GATEWAY_BASE_URL or gateway_token != _MCP_COMPOSE_GATEWAY_TOKEN:
        yield
        return
    with temporary_env(
        {
            "AUTOCLAW_OPENCLAW__GATEWAY_TOKEN": None,
            "AUTOCLAW_OPENCLAW__GATEWAY_PASSWORD": None,
        }
    ):
        yield


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
                        # Let the streamable HTTP transport flush its close handshake cleanly.
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
async def runtime_api_context(
    config_path: Path,
) -> AsyncIterator[runtime_support.RuntimeApiContext]:
    global _RUNTIME_API_DEPTH
    _RUNTIME_API_DEPTH += 1
    try:
        with _runtime_startup_gateway_env():
            async with base_runtime_api_context(config_path) as api:
                await stop_runtime_effect_runner()
                await stop_runtime_watchdog()
                yield api
    finally:
        await stop_runtime_effect_runner()
        await stop_runtime_watchdog()
        _RUNTIME_API_DEPTH -= 1
        if _RUNTIME_API_DEPTH == 0:
            await dispose_db_engine()


def tool_names(result: Any) -> tuple[str, ...]:
    return tuple(tool.name for tool in result.tools)


def tool_input_schema(result: Any, tool_name: str) -> dict[str, Any]:
    for tool in result.tools:
        if tool.name == tool_name:
            return cast(dict[str, Any], tool.inputSchema)
    raise AssertionError(f"missing tool '{tool_name}'")


def tool_output_schema(result: Any, tool_name: str) -> dict[str, Any] | None:
    for tool in result.tools:
        if tool.name == tool_name:
            return cast(dict[str, Any] | None, getattr(tool, "outputSchema", None))
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


def assert_tool_result_matches_output_schema(
    tools_result: Any,
    tool_name: str,
    result: Any,
) -> None:
    schema = tool_output_schema(tools_result, tool_name)
    assert schema is not None, f"missing output schema for tool '{tool_name}'"
    assert result.structuredContent is not None, {
        "tool": tool_name,
        "content": result.content,
        "structured": result.structuredContent,
    }
    Draft202012Validator(schema).validate(result.structuredContent)


async def call_node_structural_tool(
    session: ClientSession,
    *,
    context: NodeToolContext,
    tool_name: str,
    payload: dict[str, Any],
    active_flow_revision_id: str | None = None,
) -> dict[str, Any]:
    arguments = node_tool_arguments(context, payload=payload)
    if active_flow_revision_id is not None:
        arguments["expected_structural_revision_id"] = active_flow_revision_id
    return await call_tool_structured(session, tool_name, arguments)


async def call_node_assign_child(
    session: ClientSession,
    *,
    context: NodeToolContext,
    child_node_key: str,
    summary: str,
    instruction: str,
    active_flow_revision_id: str,
) -> dict[str, Any]:
    return await call_node_structural_tool(
        session,
        context=context,
        tool_name="assign_child",
        payload={
            "child_node_key": child_node_key,
            "assignment_intent": {"summary": summary, "instruction": instruction},
        },
        active_flow_revision_id=active_flow_revision_id,
    )


async def call_node_checkpoint(
    session: ClientSession,
    *,
    context: NodeToolContext,
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    return await call_tool_structured(
        session,
        "record_checkpoint",
        node_tool_arguments(context, checkpoint=checkpoint),
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
    workflow_key: str = "reviewed-change-release",
    workflow_definition: WorkflowDefinitionFile | None = None,
) -> tuple[Path, Path]:
    config_path = await prepare_runtime_db(tmp_path)
    set_runtime_watchdog_enabled(config_path, enabled=False)
    task_root = tmp_path / "task-root"
    previous_watchdog = os.environ.get("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED")
    os.environ["AUTOCLAW_RUNTIME__WATCHDOG_ENABLED"] = "false"
    try:
        with openclaw_gateway_test_server.configured_env():
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                agent_wait_fixture(status="timeout"),
            )
            if workflow_definition is None:
                await bootstrap_parent_runtime(
                    config_path=config_path,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version=f"mcp-{task_id}",
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
        await stop_runtime_effect_runner()
        await stop_runtime_watchdog()
    finally:
        if previous_watchdog is None:
            os.environ.pop("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED", None)
        else:
            os.environ["AUTOCLAW_RUNTIME__WATCHDOG_ENABLED"] = previous_watchdog
    return config_path, task_root


__all__ = [
    "bootstrap_parent_runtime",
    "bootstrap_runtime_task",
    "call_node_assign_child",
    "call_node_boundary",
    "call_node_checkpoint",
    "call_node_structural_tool",
    "call_tool_result",
    "call_tool_structured",
    "default_transport_security",
    "load_current_node_mcp_session_key",
    "mcp_client_session",
    "node_mcp_client_session",
    "node_mcp_mount_path",
    "node_tool_arguments",
    "prepare_runtime_db",
    "runtime_api_context",
    "tool_description",
    "tool_failure",
    "tool_input_schema",
    "tool_names",
    "tool_output_schema",
    "tool_read_only_hint",
    "wait_for_runtime_effects",
]
