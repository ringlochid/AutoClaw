from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from autoclaw.integrations.openclaw.runtime_io import read_openclaw_operation
from autoclaw.runtime.contracts import ObservabilityFileRef
from autoclaw.runtime.observability import (
    OBSERVABILITY_FILE_SPECS,
    observability_ref,
)

from ..tool_teaching import (
    CONTROLLER_TRUTH_WINS_NOTE,
    SUPPORT_FILE_REF_NOTE,
    SUPPORT_ONLY_REREAD_NOTE,
    read_only_tool_teaching,
)


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
    teaching = read_only_tool_teaching(
        name=tool_name,
        summary=f"Return the task-scoped support file ref/path for {filename}.",
        details=(
            SUPPORT_ONLY_REREAD_NOTE,
            SUPPORT_FILE_REF_NOTE,
            "Use this after get_runtime_task, get_operator_snapshot, or "
            f"get_operator_trace when you need deeper investigation. {description}",
            CONTROLLER_TRUTH_WINS_NOTE,
        ),
    )

    @server.tool(
        name=tool_name,
        title=teaching.title,
        description=teaching.description,
        annotations=teaching.annotations,
    )
    async def tool(task_id: str) -> ObservabilityFileRef:
        return await read_openclaw_operation(
            lambda session: observability_ref(
                session,
                task_id,
                filename,
                description,
            )
        )
