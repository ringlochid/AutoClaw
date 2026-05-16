from __future__ import annotations

from typing import Literal

from app.runtime.control.flow.service import (
    cancel_runtime_flow,
    continue_runtime_flow,
    list_runtime_flows,
    pause_runtime_flow,
    runtime_flow_read,
)
from app.runtime.control.observability import operator_snapshot, operator_trace
from app.schemas.runtime import (
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

from autoclaw.openclaw.common import run_read_operation, run_runtime_write_operation


def register_runtime_task_tools(server: FastMCP) -> None:
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


def register_operator_read_tools(server: FastMCP) -> None:
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


def register_runtime_control_tools(server: FastMCP) -> None:
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
