from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointKind,
    CheckpointOutcome,
    CheckpointProjection,
    DispatchDeliveryStatus,
    EgressBoundary,
    EvidenceKind,
    EvidenceRef,
    FlowStatus,
    ParentRootToolName,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    RuntimeLaunchInput,
    TaskComposeInput,
    TaskRootBindingInput,
    TaskRootMode,
)

if TYPE_CHECKING:
    from app.runtime.control.boundary.service import accept_boundary
    from app.runtime.control.checkpoint.recording import record_checkpoint
    from app.runtime.control.flow.service import (
        cancel_runtime_flow,
        continue_runtime_flow,
        list_runtime_flows,
        pause_runtime_flow,
        runtime_flow_read,
    )
    from app.runtime.control.observability import (
        observability_ref,
        operator_snapshot,
        operator_trace,
    )
    from app.runtime.control.parent_tools import call_parent_tool
    from app.runtime.launch.service import launch_task_runtime
    from app.runtime.prompt.bundle import render_prompt_bundle
    from app.runtime.task_root import localize_external_resource, resolve_task_root_paths

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "accept_boundary": ("app.runtime.control.boundary.service", "accept_boundary"),
    "call_parent_tool": ("app.runtime.control.parent_tools", "call_parent_tool"),
    "cancel_runtime_flow": ("app.runtime.control.flow.service", "cancel_runtime_flow"),
    "continue_runtime_flow": ("app.runtime.control.flow.service", "continue_runtime_flow"),
    "launch_task_runtime": ("app.runtime.launch.service", "launch_task_runtime"),
    "list_runtime_flows": ("app.runtime.control.flow.service", "list_runtime_flows"),
    "localize_external_resource": ("app.runtime.task_root", "localize_external_resource"),
    "observability_ref": ("app.runtime.control.observability", "observability_ref"),
    "operator_snapshot": ("app.runtime.control.observability", "operator_snapshot"),
    "operator_trace": ("app.runtime.control.observability", "operator_trace"),
    "pause_runtime_flow": ("app.runtime.control.flow.service", "pause_runtime_flow"),
    "record_checkpoint": ("app.runtime.control.checkpoint.recording", "record_checkpoint"),
    "render_prompt_bundle": ("app.runtime.prompt.bundle", "render_prompt_bundle"),
    "resolve_task_root_paths": ("app.runtime.task_root", "resolve_task_root_paths"),
    "runtime_flow_read": ("app.runtime.control.flow.service", "runtime_flow_read"),
}


def __getattr__(name: str) -> Any:
    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "AssignmentProjection",
    "CheckpointHandoff",
    "CheckpointKind",
    "CheckpointOutcome",
    "CheckpointProjection",
    "DispatchDeliveryStatus",
    "EgressBoundary",
    "EvidenceKind",
    "EvidenceRef",
    "FlowStatus",
    "ParentRootToolName",
    "PromptFamily",
    "PromptRenderRequest",
    "PromptSendMode",
    "RuntimeLaunchInput",
    "TaskComposeInput",
    "TaskRootBindingInput",
    "TaskRootMode",
    "accept_boundary",
    "call_parent_tool",
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "launch_task_runtime",
    "list_runtime_flows",
    "localize_external_resource",
    "observability_ref",
    "operator_snapshot",
    "operator_trace",
    "pause_runtime_flow",
    "record_checkpoint",
    "render_prompt_bundle",
    "resolve_task_root_paths",
    "runtime_flow_read",
]
