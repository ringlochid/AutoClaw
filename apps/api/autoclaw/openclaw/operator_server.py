from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, cast

from app.config import get_settings
from app.runtime.control.flow.service import (
    cancel_runtime_flow,
    continue_runtime_flow,
    list_runtime_flows,
    pause_runtime_flow,
    runtime_flow_read,
)
from app.runtime.control.observability import (
    OBSERVABILITY_FILE_SPECS,
    observability_ref,
    operator_snapshot,
    operator_trace,
)
from app.schemas.runtime import (
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceQuery,
    OperatorFlowTraceResponse,
    RuntimeFlowControlQuery,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
    RuntimeTaskListQuery,
)
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from autoclaw.openclaw.common import (
    default_transport_security,
    run_read_operation,
    run_runtime_write_operation,
)

OPERATOR_TOOL_NAMES: tuple[str, ...] = (
    "list_runtime_tasks",
    "get_runtime_task",
    "get_operator_snapshot",
    "get_operator_trace",
    "pause_task",
    "continue_task",
    "cancel_task",
    "get_delivery_state_ref",
    "get_continuity_state_ref",
    "get_watchdog_state_ref",
    "get_provider_events_ref",
)


def create_operator_mcp_server(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = _build_operator_mcp_server(
        host=host,
        transport_security=transport_security,
    )
    _register_runtime_task_tools(server)
    _register_operator_read_tools(server)
    _register_runtime_control_tools(server)
    _register_observability_ref_tools(server)
    return server


def _build_operator_mcp_server(
    *,
    host: str,
    transport_security: TransportSecuritySettings | None,
) -> FastMCP:
    return FastMCP(
        "autoclaw-operator",
        instructions=(
            "Operator-safe AutoClaw runtime surface. This server only exposes task-scoped "
            "runtime, operator, and support reads plus pause/continue/cancel controls."
        ),
        json_response=True,
        stateless_http=True,
        transport_security=transport_security or default_transport_security(host=host),
    )


def _register_runtime_task_tools(server: FastMCP) -> None:
    @server.tool(name="list_runtime_tasks")
    async def list_runtime_tasks(
        query: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        sort: Literal[
            "updated_at_desc",
            "updated_at_asc",
            "task_title_asc",
            "task_title_desc",
        ] = "updated_at_desc",
        status: Literal[
            "any",
            "pending",
            "running",
            "blocked",
            "paused",
            "succeeded",
            "failed",
            "cancelled",
        ] = "any",
    ) -> RuntimeFlowSummaryListResponse:
        filters = RuntimeTaskListQuery(
            q=query,
            limit=limit,
            cursor=cursor,
            sort=sort,
            status=status,
        )
        return await run_read_operation(
            lambda session: list_runtime_flows(
                session,
                q=filters.q,
                limit=filters.limit,
                cursor=filters.cursor,
                sort=filters.sort,
                status=filters.status,
            )
        )

    @server.tool(name="get_runtime_task")
    async def get_runtime_task(task_id: str) -> RuntimeFlowRead:
        return await run_read_operation(lambda session: runtime_flow_read(session, task_id))


def _register_operator_read_tools(server: FastMCP) -> None:
    @server.tool(name="get_operator_snapshot")
    async def get_operator_snapshot(task_id: str) -> OperatorFlowSnapshotResponse:
        return await run_read_operation(lambda session: operator_snapshot(session, task_id))

    @server.tool(name="get_operator_trace")
    async def get_operator_trace(
        task_id: str,
        scope: Literal["current", "whole"] = "current",
        query: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        sort: Literal["occurred_at_desc", "occurred_at_asc"] = "occurred_at_desc",
    ) -> OperatorFlowTraceResponse:
        trace_query = OperatorFlowTraceQuery(
            scope=scope,
            q=query,
            limit=limit,
            cursor=cursor,
            sort=sort,
        )
        return await run_read_operation(
            lambda session: operator_trace(
                session,
                task_id,
                scope=trace_query.scope,
                q=trace_query.q,
                limit=trace_query.limit,
                cursor=trace_query.cursor,
                sort=trace_query.sort,
            )
        )


def _register_runtime_control_tools(server: FastMCP) -> None:
    @server.tool(name="pause_task")
    async def pause_task(
        task_id: str,
        expected_active_flow_revision_id: str,
    ) -> RuntimeFlowPauseResponse:
        query = RuntimeFlowControlQuery(
            expected_active_flow_revision_id=expected_active_flow_revision_id
        )
        return await run_runtime_write_operation(
            lambda session: pause_runtime_flow(
                session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
            )
        )

    @server.tool(name="continue_task")
    async def continue_task(
        task_id: str,
        expected_active_flow_revision_id: str,
    ) -> RuntimeFlowRead:
        query = RuntimeFlowControlQuery(
            expected_active_flow_revision_id=expected_active_flow_revision_id
        )
        return await run_runtime_write_operation(
            lambda session: continue_runtime_flow(
                session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
            )
        )

    @server.tool(name="cancel_task")
    async def cancel_task(
        task_id: str,
        expected_active_flow_revision_id: str,
    ) -> RuntimeFlowRead:
        query = RuntimeFlowControlQuery(
            expected_active_flow_revision_id=expected_active_flow_revision_id
        )
        return await run_runtime_write_operation(
            lambda session: cancel_runtime_flow(
                session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
            )
        )


def _register_observability_ref_tools(server: FastMCP) -> None:
    for tool_name, (filename, description) in zip(
        (
            "get_delivery_state_ref",
            "get_continuity_state_ref",
            "get_watchdog_state_ref",
            "get_provider_events_ref",
        ),
        OBSERVABILITY_FILE_SPECS,
        strict=True,
    ):
        register_observability_ref_tool(
            server,
            tool_name=tool_name,
            filename=filename,
            description=description,
        )


def register_observability_ref_tool(
    server: FastMCP,
    *,
    tool_name: str,
    filename: str,
    description: str,
) -> None:
    @server.tool(name=tool_name)
    async def _tool(task_id: str) -> ObservabilityFileRef:
        return await _observability_file_ref(
            task_id=task_id,
            filename=filename,
            description=description,
        )


def create_operator_mcp_app(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> Starlette:
    app = create_operator_mcp_server(
        host=host,
        transport_security=transport_security,
    ).streamable_http_app()
    app.add_middleware(
        cast(Any, _OperatorAuthMiddleware),
        expected_token=get_settings().api_key,
    )
    return app


async def _observability_file_ref(
    *,
    task_id: str,
    filename: str,
    description: str,
) -> ObservabilityFileRef:
    return await run_read_operation(
        lambda session: observability_ref(
            session,
            task_id,
            filename,
            description,
        )
    )


class _OperatorAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Starlette, *, expected_token: str) -> None:
        super().__init__(app)
        self._expected_token = expected_token

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        expected = f"Bearer {self._expected_token}"
        if request.headers.get("authorization", "") != expected:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized operator MCP request"},
            )
        return await call_next(request)


__all__ = [
    "OPERATOR_TOOL_NAMES",
    "create_operator_mcp_app",
    "create_operator_mcp_server",
]
