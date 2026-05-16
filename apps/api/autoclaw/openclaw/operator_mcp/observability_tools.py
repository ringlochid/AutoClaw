from __future__ import annotations

from app.runtime.control.observability import OBSERVABILITY_FILE_SPECS, observability_ref
from app.schemas.runtime import ObservabilityFileRef
from mcp.server.fastmcp import FastMCP

from autoclaw.openclaw.common import run_read_operation


def register_observability_ref_tools(server: FastMCP) -> None:
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
    async def tool(task_id: str) -> ObservabilityFileRef:
        return await run_read_operation(
            lambda session: observability_ref(
                session,
                task_id,
                filename,
                description,
            )
        )
