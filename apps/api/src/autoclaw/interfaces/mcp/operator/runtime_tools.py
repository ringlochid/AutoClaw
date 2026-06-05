from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from autoclaw.integrations.openclaw.runtime_io import (
    read_openclaw_operation,
    write_openclaw_runtime_operation,
)
from autoclaw.runtime.contracts import (
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceQuery,
    OperatorFlowTraceResponse,
    RuntimeFlowControlQuery,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
    RuntimeTaskListQuery,
)
from autoclaw.runtime.flow import (
    cancel_runtime_flow,
    continue_runtime_flow,
    list_runtime_flows,
    pause_runtime_flow,
    runtime_flow_read,
)
from autoclaw.runtime.observability import operator_snapshot, operator_trace

from ..tool_teaching import (
    FRESH_REVISION_NOTE,
    INSPECT_FIRST_NOTE,
    RUNTIME_STATE_WARNING,
    STATUS_CHECK_WARNING,
    mutating_tool_teaching,
    read_only_tool_teaching,
)

LIST_RUNTIME_TASKS_TEACHING = read_only_tool_teaching(
    name="list_runtime_tasks",
    summary="List task runtime summaries so you can find a task before deeper inspection.",
    details=(
        "Use get_runtime_task next for one task's current status and fresh revision.",
        "Inspect before mutating runtime state.",
    ),
)
GET_RUNTIME_TASK_TEACHING = read_only_tool_teaching(
    name="get_runtime_task",
    summary=("Inspect the current task status and active flow revision for one task."),
    details=(
        "Use this first for status checks and before pause_task, continue_task, or cancel_task.",
        "Use this to get a fresh expected_active_flow_revision_id before "
        "pause_task, continue_task, or cancel_task.",
    ),
)
GET_OPERATOR_SNAPSHOT_TEACHING = read_only_tool_teaching(
    name="get_operator_snapshot",
    summary="Inspect the current operator-facing state and current_paths for one task.",
    details=(
        "Use this after get_runtime_task when you need current state, not chronology.",
        "Observe before mutating runtime state.",
    ),
)
GET_OPERATOR_TRACE_TEACHING = read_only_tool_teaching(
    name="get_operator_trace",
    summary="Inspect dispatch and checkpoint chronology for one task.",
    details=(
        "Use this after get_runtime_task or get_operator_snapshot when you "
        "need to understand how the workflow reached the current state.",
        "Observe before mutating runtime state.",
    ),
)
PAUSE_TASK_TEACHING = mutating_tool_teaching(
    name="pause_task",
    summary="Pause a task when you intentionally want to stop forward progress.",
    details=(RUNTIME_STATE_WARNING, FRESH_REVISION_NOTE),
)
CONTINUE_TASK_TEACHING = mutating_tool_teaching(
    name="continue_task",
    summary="Resume a paused task after inspection confirms it should continue.",
    details=(
        RUNTIME_STATE_WARNING,
        STATUS_CHECK_WARNING,
        INSPECT_FIRST_NOTE,
        "Pause-resume only.",
        "Not the ordinary path for yielded child handoff, parent wake, or retry advancement.",
        FRESH_REVISION_NOTE,
    ),
)
CANCEL_TASK_TEACHING = mutating_tool_teaching(
    name="cancel_task",
    summary="Cancel a task when you intentionally want to stop it.",
    details=(RUNTIME_STATE_WARNING, FRESH_REVISION_NOTE),
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
        return await read_openclaw_operation(
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
        return await read_openclaw_operation(lambda session: runtime_flow_read(session, task_id))


def register_operator_read_tools(server: FastMCP) -> None:
    @server.tool(
        name="get_operator_snapshot",
        title=GET_OPERATOR_SNAPSHOT_TEACHING.title,
        description=GET_OPERATOR_SNAPSHOT_TEACHING.description,
        annotations=GET_OPERATOR_SNAPSHOT_TEACHING.annotations,
    )
    async def get_operator_snapshot(task_id: str) -> OperatorFlowSnapshotResponse:
        return await read_openclaw_operation(lambda session: operator_snapshot(session, task_id))

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
        return await read_openclaw_operation(
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
        return await write_openclaw_runtime_operation(
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
        return await write_openclaw_runtime_operation(
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
        return await write_openclaw_runtime_operation(
            lambda session: cancel_runtime_flow(
                session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
            )
        )
