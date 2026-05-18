from __future__ import annotations

from dataclasses import dataclass

from mcp.types import ToolAnnotations

READ_ONLY_PREFIX = "Read-only:"
MUTATING_PREFIX = "Mutating:"
LOCAL_FILE_PATH_NOTE = "Local file path on the AutoClaw host."
STATUS_CHECK_WARNING = "Do not use for status checks."
RUNTIME_STATE_WARNING = "This changes runtime state."
SUPPORT_FILE_REF_NOTE = "Returns a task-scoped support file ref/path, not a parsed status answer."
NODE_AUTHORITY_NOTE = (
    "Pass the current dispatch-local session_key and task_id as explicit authority inputs."
)
OPERATOR_OBSERVE_ORDER_NOTE = (
    "Recommended order: get_runtime_task -> get_operator_snapshot -> get_operator_trace -> "
    "get_delivery_state_ref/get_continuity_state_ref/get_watchdog_state_ref/"
    "get_provider_events_ref when deeper support inspection is needed."
)


@dataclass(frozen=True)
class ToolTeaching:
    title: str
    description: str
    annotations: ToolAnnotations


def read_only_tool_teaching(
    *,
    name: str,
    summary: str,
    details: tuple[str, ...] = (),
) -> ToolTeaching:
    return ToolTeaching(
        title=tool_title(name),
        description=_join_sentences(f"{READ_ONLY_PREFIX} {summary}", *details),
        annotations=ToolAnnotations(readOnlyHint=True),
    )


def mutating_tool_teaching(
    *,
    name: str,
    summary: str,
    details: tuple[str, ...] = (),
) -> ToolTeaching:
    return ToolTeaching(
        title=tool_title(name),
        description=_join_sentences(f"{MUTATING_PREFIX} {summary}", *details),
        annotations=ToolAnnotations(readOnlyHint=False),
    )


def tool_title(name: str) -> str:
    return name.replace("_", " ").title()


def _join_sentences(*parts: str) -> str:
    return " ".join(part.strip() for part in parts if part.strip())


__all__ = [
    "LOCAL_FILE_PATH_NOTE",
    "MUTATING_PREFIX",
    "NODE_AUTHORITY_NOTE",
    "OPERATOR_OBSERVE_ORDER_NOTE",
    "READ_ONLY_PREFIX",
    "RUNTIME_STATE_WARNING",
    "STATUS_CHECK_WARNING",
    "SUPPORT_FILE_REF_NOTE",
    "ToolTeaching",
    "mutating_tool_teaching",
    "read_only_tool_teaching",
    "tool_title",
]
