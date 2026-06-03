from __future__ import annotations

from dataclasses import dataclass

from mcp.types import ToolAnnotations

READ_ONLY_PREFIX = "Read-only:"
MUTATING_PREFIX = "Mutating:"
LOCAL_FILE_PATH_NOTE = "Local file path on the AutoClaw host."
STATUS_CHECK_WARNING = "Do not use for status checks."
RUNTIME_STATE_WARNING = "This changes runtime state."
FRESH_REVISION_NOTE = (
    "Use only with a fresh expected_active_flow_revision_id from get_runtime_task "
    "or get_operator_snapshot."
)
INSPECT_FIRST_NOTE = "Use only after inspecting current runtime state."
SUPPORT_FILE_REF_NOTE = "Returns a task-scoped support file ref/path, not a parsed status answer."
SUPPORT_ONLY_REREAD_NOTE = "Support-only reread surface."
CONTROLLER_TRUTH_WINS_NOTE = (
    "If this reread disagrees with controller/runtime truth, controller/runtime truth wins."
)
NODE_AUTHORITY_NOTE = (
    "Pass the current dispatch-local session_key and task_id as explicit authority inputs."
)
LIVE_STRUCTURAL_EDIT_LANE_NOTE = (
    "Use only when the surfaced prompt or manifest still lacks the needed role or "
    "policy choice for the live structural-edit lane."
)
NOT_BROAD_BROWSING_NOTE = "Not for broad browsing or provenance."
RECORD_BEFORE_TERMINAL_BOUNDARY_NOTE = (
    "Use this before a terminal boundary when later readers need the progress state."
)
RETURN_BOUNDARY_TERMINALITY_NOTE = (
    "`yield` is non-terminal workflow progress; `green`, `retry`, and `blocked` "
    "end the current dispatch turn terminally."
)
STOP_AFTER_BOUNDARY_NOTE = (
    "After a successful boundary call, stop the current outer assistant turn immediately. "
    "Do not keep reasoning, do not make another tool call, and do not append extra prose "
    "after the boundary result."
)
CALL_PARENT_TOOL_LEGALITY_NOTE = (
    "Use only when the current dispatch allows legal parent/root mutation for this turn."
)
DISCOVER_CANDIDATES_NOTE = "Use this to discover candidates before choosing or mutating."
INSPECT_CURRENT_REVISION_NOTE = "Use this to inspect one current revision."
AUDIT_ONLY_NOTE = "Use this for audit or provenance, not normal planning."
INSPECT_IF_UNSURE_NOTE = (
    "Inspect current definitions first if you are unsure which definition to change."
)
REAL_RUNTIME_EFFECTS_NOTE = "Creates task root and starts real runtime effects."


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
    "AUDIT_ONLY_NOTE",
    "CALL_PARENT_TOOL_LEGALITY_NOTE",
    "CONTROLLER_TRUTH_WINS_NOTE",
    "DISCOVER_CANDIDATES_NOTE",
    "FRESH_REVISION_NOTE",
    "INSPECT_CURRENT_REVISION_NOTE",
    "INSPECT_FIRST_NOTE",
    "INSPECT_IF_UNSURE_NOTE",
    "LIVE_STRUCTURAL_EDIT_LANE_NOTE",
    "LOCAL_FILE_PATH_NOTE",
    "MUTATING_PREFIX",
    "NODE_AUTHORITY_NOTE",
    "NOT_BROAD_BROWSING_NOTE",
    "READ_ONLY_PREFIX",
    "REAL_RUNTIME_EFFECTS_NOTE",
    "RECORD_BEFORE_TERMINAL_BOUNDARY_NOTE",
    "RETURN_BOUNDARY_TERMINALITY_NOTE",
    "RUNTIME_STATE_WARNING",
    "STATUS_CHECK_WARNING",
    "STOP_AFTER_BOUNDARY_NOTE",
    "SUPPORT_FILE_REF_NOTE",
    "SUPPORT_ONLY_REREAD_NOTE",
    "ToolTeaching",
    "mutating_tool_teaching",
    "read_only_tool_teaching",
    "tool_title",
]
