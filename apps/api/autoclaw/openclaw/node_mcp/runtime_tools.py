from __future__ import annotations

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
    AddChildPayload,
    AddChildSuccess,
    AssignChildPayload,
    AssignChildSuccess,
    BoundaryRead,
    BoundaryWrite,
    CheckpointRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ParentToolSuccess,
    ReleaseBlockedSuccess,
    ReleaseGreenSuccess,
    RemoveChildPayload,
    RemoveChildSuccess,
    UpdateChildPayload,
    UpdateChildSuccess,
)
from app.schemas.runtime.parent_tools import ParentToolCall
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from autoclaw.openclaw.node_mcp.contracts import (
    ADD_CHILD_INPUT_SCHEMA,
    ADD_CHILD_OUTPUT_SCHEMA,
    ADD_CHILD_TEACHING,
    ASSIGN_CHILD_INPUT_SCHEMA,
    ASSIGN_CHILD_OUTPUT_SCHEMA,
    ASSIGN_CHILD_TEACHING,
    BOUNDARY_OUTPUT_SCHEMA,
    CHECKPOINT_OUTPUT_SCHEMA,
    NODE_BOUNDARY_INPUT_SCHEMA,
    NODE_CHECKPOINT_INPUT_SCHEMA,
    RECORD_CHECKPOINT_TEACHING,
    RELEASE_BLOCKED_INPUT_SCHEMA,
    RELEASE_BLOCKED_OUTPUT_SCHEMA,
    RELEASE_BLOCKED_TEACHING,
    RELEASE_GREEN_INPUT_SCHEMA,
    RELEASE_GREEN_OUTPUT_SCHEMA,
    RELEASE_GREEN_TEACHING,
    REMOVE_CHILD_INPUT_SCHEMA,
    REMOVE_CHILD_OUTPUT_SCHEMA,
    REMOVE_CHILD_TEACHING,
    RETURN_BOUNDARY_TEACHING,
    UPDATE_CHILD_INPUT_SCHEMA,
    UPDATE_CHILD_OUTPUT_SCHEMA,
    UPDATE_CHILD_TEACHING,
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
        name="assign_child",
        title=ASSIGN_CHILD_TEACHING.title,
        description=ASSIGN_CHILD_TEACHING.description,
        annotations=ASSIGN_CHILD_TEACHING.annotations,
    )
    async def assign_child_tool(
        session_key: str,
        task_id: str,
        payload: AssignChildPayload,
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_parent_tool_operation(
                task_id=task_id,
                session_key=session_key,
                tool_name=ParentRootToolName.ASSIGN_CHILD,
                payload=payload,
                expected_structural_revision_id=expected_structural_revision_id,
            )
        )

    @server.tool(
        name="add_child",
        title=ADD_CHILD_TEACHING.title,
        description=ADD_CHILD_TEACHING.description,
        annotations=ADD_CHILD_TEACHING.annotations,
    )
    async def add_child_tool(
        session_key: str,
        task_id: str,
        payload: AddChildPayload,
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_parent_tool_operation(
                task_id=task_id,
                session_key=session_key,
                tool_name=ParentRootToolName.ADD_CHILD,
                payload=payload,
                expected_structural_revision_id=expected_structural_revision_id,
            )
        )

    @server.tool(
        name="update_child",
        title=UPDATE_CHILD_TEACHING.title,
        description=UPDATE_CHILD_TEACHING.description,
        annotations=UPDATE_CHILD_TEACHING.annotations,
    )
    async def update_child_tool(
        session_key: str,
        task_id: str,
        payload: UpdateChildPayload,
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_parent_tool_operation(
                task_id=task_id,
                session_key=session_key,
                tool_name=ParentRootToolName.UPDATE_CHILD,
                payload=payload,
                expected_structural_revision_id=expected_structural_revision_id,
            )
        )

    @server.tool(
        name="remove_child",
        title=REMOVE_CHILD_TEACHING.title,
        description=REMOVE_CHILD_TEACHING.description,
        annotations=REMOVE_CHILD_TEACHING.annotations,
    )
    async def remove_child_tool(
        session_key: str,
        task_id: str,
        payload: RemoveChildPayload,
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_parent_tool_operation(
                task_id=task_id,
                session_key=session_key,
                tool_name=ParentRootToolName.REMOVE_CHILD,
                payload=payload,
                expected_structural_revision_id=expected_structural_revision_id,
            )
        )

    @server.tool(
        name="release_green",
        title=RELEASE_GREEN_TEACHING.title,
        description=RELEASE_GREEN_TEACHING.description,
        annotations=RELEASE_GREEN_TEACHING.annotations,
    )
    async def release_green_tool(
        session_key: str,
        task_id: str,
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_parent_tool_operation(
                task_id=task_id,
                session_key=session_key,
                tool_name=ParentRootToolName.RELEASE_GREEN,
                payload={},
                expected_structural_revision_id=expected_structural_revision_id,
            )
        )

    @server.tool(
        name="release_blocked",
        title=RELEASE_BLOCKED_TEACHING.title,
        description=RELEASE_BLOCKED_TEACHING.description,
        annotations=RELEASE_BLOCKED_TEACHING.annotations,
    )
    async def release_blocked_tool(
        session_key: str,
        task_id: str,
        expected_structural_revision_id: str | None = None,
    ) -> CallToolResult:
        return node_success_tool_result(
            await run_parent_tool_operation(
                task_id=task_id,
                session_key=session_key,
                tool_name=ParentRootToolName.RELEASE_BLOCKED,
                payload={},
                expected_structural_revision_id=expected_structural_revision_id,
            )
        )

    freeze_node_tool_contracts(server)


async def run_parent_tool_operation(
    *,
    task_id: str,
    session_key: str,
    tool_name: ParentRootToolName,
    payload: object,
    expected_structural_revision_id: str | None,
) -> ParentToolSuccess:
    parent_tool_call = ParentToolCall(
        tool_name=tool_name,
        payload=payload,
        expected_structural_revision_id=expected_structural_revision_id,
    )
    return await run_node_operation(
        task_id=task_id,
        session_key=session_key,
        operation=ParentToolNodeOperation(
            tool_name=tool_name,
            payload=parent_tool_call,
        ),
    )


async def run_node_operation(
    *,
    task_id: str,
    session_key: str,
    operation: NodeOperation,
) -> (
    CheckpointRead
    | BoundaryRead
    | AssignChildSuccess
    | AddChildSuccess
    | UpdateChildSuccess
    | RemoveChildSuccess
    | ReleaseGreenSuccess
    | ReleaseBlockedSuccess
):
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
        input_schema=NODE_CHECKPOINT_INPUT_SCHEMA,
        output_schema=CHECKPOINT_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="return_boundary",
        input_schema=NODE_BOUNDARY_INPUT_SCHEMA,
        output_schema=BOUNDARY_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="assign_child",
        input_schema=ASSIGN_CHILD_INPUT_SCHEMA,
        output_schema=ASSIGN_CHILD_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="add_child",
        input_schema=ADD_CHILD_INPUT_SCHEMA,
        output_schema=ADD_CHILD_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="update_child",
        input_schema=UPDATE_CHILD_INPUT_SCHEMA,
        output_schema=UPDATE_CHILD_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="remove_child",
        input_schema=REMOVE_CHILD_INPUT_SCHEMA,
        output_schema=REMOVE_CHILD_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="release_green",
        input_schema=RELEASE_GREEN_INPUT_SCHEMA,
        output_schema=RELEASE_GREEN_OUTPUT_SCHEMA,
    )
    override_tool_schemas(
        server,
        tool_name="release_blocked",
        input_schema=RELEASE_BLOCKED_INPUT_SCHEMA,
        output_schema=RELEASE_BLOCKED_OUTPUT_SCHEMA,
    )


def override_tool_schemas(
    server: FastMCP,
    *,
    tool_name: str,
    input_schema: dict[str, object] | None = None,
    output_schema: dict[str, object] | None = None,
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
    "run_parent_tool_operation",
]
