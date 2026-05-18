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
from autoclaw.openclaw.tool_teaching import (
    OPERATOR_OBSERVE_ORDER_NOTE,
    RUNTIME_STATE_WARNING,
    STATUS_CHECK_WARNING,
    mutating_tool_teaching,
    read_only_tool_teaching,
)

LIST_RUNTIME_TASKS_TEACHING = read_only_tool_teaching(
    name="list_runtime_tasks",
    summary="List task runtime summaries so you can find a task before deeper inspection.",
    details=(OPERATOR_OBSERVE_ORDER_NOTE,),
)
GET_RUNTIME_TASK_TEACHING = read_only_tool_teaching(
    name="get_runtime_task",
    summary=(
        "Inspect the current runtime status for one task. Use this first for task status checks."
    ),
    details=(OPERATOR_OBSERVE_ORDER_NOTE,),
)
GET_OPERATOR_SNAPSHOT_TEACHING = read_only_tool_teaching(
    name="get_operator_snapshot",
    summary="Inspect the current operator summary and current paths for one task.",
    details=("Use this after get_runtime_task when you need the current operator-facing state.",),
)
GET_OPERATOR_TRACE_TEACHING = read_only_tool_teaching(
    name="get_operator_trace",
    summary="Inspect dispatch and checkpoint history for one task.",
    details=(
        "Use this after get_runtime_task or get_operator_snapshot when you need timeline detail.",
    ),
)
PAUSE_TASK_TEACHING = mutating_tool_teaching(
    name="pause_task",
    summary="Pause a task when you intentionally want to stop forward progress.",
    details=(RUNTIME_STATE_WARNING,),
)
CONTINUE_TASK_TEACHING = mutating_tool_teaching(
    name="continue_task",
    summary=(
        "Resume or reopen the current task runtime after inspection confirms it is appropriate."
    ),
    details=(RUNTIME_STATE_WARNING, STATUS_CHECK_WARNING),
)
CANCEL_TASK_TEACHING = mutating_tool_teaching(
    name="cancel_task",
    summary="Cancel a task when you intentionally want to stop it.",
    details=(RUNTIME_STATE_WARNING,),
)


def register_runtime_task_tools(server: FastMCP) -> None:
    @server.tool(
        name="list_runtime_tasks",
        title=LIST_RUNTIME_TASKS_TEACHING.title,
        description=LIST_RUNTIME_TASKS_TEACHING.description,
        annotations=LIST_RUNTIME_TASKS_TEACHING.annotations,
    )
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

    @server.tool(
        name="get_runtime_task",
        title=GET_RUNTIME_TASK_TEACHING.title,
        description=GET_RUNTIME_TASK_TEACHING.description,
        annotations=GET_RUNTIME_TASK_TEACHING.annotations,
    )
    async def get_runtime_task(task_id: str) -> RuntimeFlowRead:
        return await run_read_operation(lambda session: runtime_flow_read(session, task_id))


def register_operator_read_tools(server: FastMCP) -> None:
    @server.tool(
        name="get_operator_snapshot",
        title=GET_OPERATOR_SNAPSHOT_TEACHING.title,
        description=GET_OPERATOR_SNAPSHOT_TEACHING.description,
        annotations=GET_OPERATOR_SNAPSHOT_TEACHING.annotations,
    )
    async def get_operator_snapshot(task_id: str) -> OperatorFlowSnapshotResponse:
        return await run_read_operation(lambda session: operator_snapshot(session, task_id))

    @server.tool(
        name="get_operator_trace",
        title=GET_OPERATOR_TRACE_TEACHING.title,
        description=GET_OPERATOR_TRACE_TEACHING.description,
        annotations=GET_OPERATOR_TRACE_TEACHING.annotations,
    )
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
    @server.tool(
        name="pause_task",
        title=PAUSE_TASK_TEACHING.title,
        description=PAUSE_TASK_TEACHING.description,
        annotations=PAUSE_TASK_TEACHING.annotations,
    )
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

    @server.tool(
        name="continue_task",
        title=CONTINUE_TASK_TEACHING.title,
        description=CONTINUE_TASK_TEACHING.description,
        annotations=CONTINUE_TASK_TEACHING.annotations,
    )
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

    @server.tool(
        name="cancel_task",
        title=CANCEL_TASK_TEACHING.title,
        description=CANCEL_TASK_TEACHING.description,
        annotations=CANCEL_TASK_TEACHING.annotations,
    )
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
