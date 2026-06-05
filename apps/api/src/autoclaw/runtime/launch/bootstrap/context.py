from __future__ import annotations

from dataclasses import dataclass

from autoclaw.runtime.contracts import (
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
)
from autoclaw.runtime.ids import compiled_plan_id_for_task, flow_id_for_task


@dataclass(frozen=True)
class LaunchBootstrapPersistenceContext:
    binding_paths: dict[str, str]
    compiled_plan_id: str
    context_binding_mode: str
    flow_id: str
    workspace_binding_mode: str


def build_launch_bootstrap_persistence_context(
    *,
    result: RuntimeBootstrapResult,
    bootstrap_input: RuntimeBootstrapProjectionInput,
) -> LaunchBootstrapPersistenceContext:
    roots = bootstrap_input.task_compose.roots
    workspace_binding_mode = (
        roots.workspace.mode.value
        if roots is not None and roots.workspace is not None
        else "ensure_task_default"
    )
    context_binding_mode = (
        roots.context.mode.value
        if roots is not None and roots.context is not None
        else "ensure_task_default"
    )
    return LaunchBootstrapPersistenceContext(
        binding_paths={
            "workspace": str(result.paths.workspace_path),
            "context": str(result.paths.context_path),
            "criteria": str(result.paths.criteria_path),
            "wiki": str(result.paths.wiki_path),
            "outputs": str(result.paths.outputs_path),
            "artifacts": str(result.paths.artifacts_path),
            "tmp": str(result.paths.tmp_path),
            "transfers": str(result.paths.transfers_path),
            "runtime": str(result.paths.runtime_path),
            "attempts": str(result.paths.attempts_path),
            "dispatch": str(result.paths.dispatch_path),
        },
        compiled_plan_id=compiled_plan_id_for_task(bootstrap_input.task_id),
        context_binding_mode=context_binding_mode,
        flow_id=flow_id_for_task(bootstrap_input.task_id),
        workspace_binding_mode=workspace_binding_mode,
    )
