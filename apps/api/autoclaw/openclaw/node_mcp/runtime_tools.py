from __future__ import annotations

from typing import Any, overload

from app.db.session import get_session_factory
from app.runtime.contracts import EgressBoundary, ParentRootToolName
from app.runtime.control.node_operations import (
    BoundaryNodeOperation,
    CheckpointNodeOperation,
    NodeOperation,
    ParentToolNodeOperation,
    execute_node_operation,
)
from app.schemas.runtime import (
    BoundaryRead,
    BoundaryWrite,
    CheckpointRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ParentToolSuccess,
)
from app.schemas.runtime.parent_tools import ParentToolCall
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from autoclaw.openclaw.node_mcp.contracts import (
    BOUNDARY_OUTPUT_SCHEMA,
    CALL_PARENT_TOOL_TEACHING,
    CHECKPOINT_OUTPUT_SCHEMA,
    NODE_PARENT_TOOL_INPUT_SCHEMA,
    PARENT_TOOL_OUTPUT_SCHEMA,
    RECORD_CHECKPOINT_TEACHING,
    RETURN_BOUNDARY_TEACHING,
)


def register_node_runtime_tools(server: FastMCP) -> None:
    @server.tool(
        name="record_checkpoint",
        title=RECORD_CHECKPOINT_TEACHING.title,
        description=RECORD_CHECKPOINT_TEACHING.description,
        annotations=RECORD_CHECKPOINT_TEACHING.annotations,
    )
    async def record_checkpoint_tool(
        session_key: str,
        task_id: str,
        checkpoint: CheckpointWriteBody,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_node_operation(
                task_id=task_id,
                session_key=session_key,
                operation=CheckpointNodeOperation(payload=CheckpointWrite(checkpoint=checkpoint)),
            )
        )

    @server.tool(
        name="return_boundary",
        title=RETURN_BOUNDARY_TEACHING.title,
        description=RETURN_BOUNDARY_TEACHING.description,
        annotations=RETURN_BOUNDARY_TEACHING.annotations,
    )
    async def return_boundary(
        session_key: str,
        task_id: str,
        boundary: EgressBoundary,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_node_operation(
                task_id=task_id,
                session_key=session_key,
                operation=BoundaryNodeOperation(payload=BoundaryWrite(boundary=boundary)),
            )
        )

    @server.tool(
        name="call_parent_tool",
        title=CALL_PARENT_TOOL_TEACHING.title,
        description=CALL_PARENT_TOOL_TEACHING.description,
        annotations=CALL_PARENT_TOOL_TEACHING.annotations,
    )
    async def call_parent_tool_tool(
        session_key: str,
        task_id: str,
        tool_name: ParentRootToolName,
        payload: dict[str, Any],
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        parent_tool_call = ParentToolCall(
            tool_name=tool_name,
            payload=payload,
            expected_structural_revision_id=expected_structural_revision_id,
        )
        return node_success_tool_result(
            await run_node_operation(
                task_id=task_id,
                session_key=session_key,
                operation=ParentToolNodeOperation(
                    tool_name=tool_name,
                    payload=parent_tool_call,
                ),
            )
        )

    freeze_node_tool_contracts(server)


@overload
async def run_node_operation(
    *,
    task_id: str,
    session_key: str,
    operation: CheckpointNodeOperation,
) -> CheckpointRead: ...


@overload
async def run_node_operation(
    *,
    task_id: str,
    session_key: str,
    operation: BoundaryNodeOperation,
) -> BoundaryRead: ...


@overload
async def run_node_operation(
    *,
    task_id: str,
    session_key: str,
    operation: ParentToolNodeOperation,
) -> ParentToolSuccess: ...


async def run_node_operation(
    *,
    task_id: str,
    session_key: str,
    operation: NodeOperation,
) -> CheckpointRead | BoundaryRead | ParentToolSuccess:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await execute_node_operation(
            session,
            task_id=task_id,
            session_key=session_key,
            operation=operation,
            invalid_summary="invalid node session key",
            stale_summary="stale node session key",
            inactive_summary="inactive node session key",
        )


def freeze_node_tool_contracts(server: FastMCP) -> None:
    override_tool_schemas(
        server,
        tool_name="record_checkpoint",
        output_schema=CHECKPOINT_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="return_boundary",
        output_schema=BOUNDARY_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="call_parent_tool",
        input_schema=NODE_PARENT_TOOL_INPUT_SCHEMA,
        output_schema=PARENT_TOOL_OUTPUT_SCHEMA,
    )


def override_tool_schemas(
    server: FastMCP,
    *,
    tool_name: str,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> None:
    tool = server._tool_manager.get_tool(tool_name)
    assert tool is not None
    if input_schema is not None:
        tool.parameters = input_schema
    if output_schema is not None:
        tool.__dict__["output_schema"] = output_schema


def node_success_tool_result(result: BaseModel) -> CallToolResult:
    payload = result.model_dump(mode="json")
    return CallToolResult(
        content=[TextContent(type="text", text=result.model_dump_json(indent=2))],
        structuredContent=payload,
    )


__all__ = [
    "freeze_node_tool_contracts",
    "node_success_tool_result",
    "override_tool_schemas",
    "register_node_runtime_tools",
    "run_node_operation",
]
