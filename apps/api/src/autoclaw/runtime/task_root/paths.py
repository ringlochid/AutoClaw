from __future__ import annotations

from pathlib import Path

from autoclaw.runtime.contracts import (
    TaskComposeInput,
    TaskRootBindingInput,
    TaskRootMode,
    TaskRootPaths,
)


def resolve_task_root_paths(
    *,
    task_root: Path,
    task_compose: TaskComposeInput,
) -> TaskRootPaths:
    roots = task_compose.roots
    task_root_path = coerce_path(task_root)
    workspace_binding = _binding_or_default(roots.workspace if roots is not None else None)
    context_binding = _binding_or_default(roots.context if roots is not None else None)
    context_path = _resolve_bound_root(
        task_root=task_root_path,
        root_name="context",
        binding=context_binding,
    )
    runtime_path = task_root_path / "_runtime"
    return TaskRootPaths(
        task_root=task_root_path,
        workspace_path=_resolve_bound_root(
            task_root=task_root_path,
            root_name="workspace",
            binding=workspace_binding,
        ),
        context_path=context_path,
        criteria_path=runtime_path / "criteria",
        wiki_path=context_path / "wiki",
        outputs_path=task_root_path / "outputs",
        artifacts_path=task_root_path / "outputs" / "artifacts",
        tmp_path=task_root_path / "tmp",
        transfers_path=task_root_path / "tmp" / "transfers",
        runtime_path=runtime_path,
        attempts_path=runtime_path / "attempts",
        dispatch_path=runtime_path / "dispatch",
    )


def ensure_task_root_layout(paths: TaskRootPaths) -> None:
    for path in (
        paths.task_root,
        paths.workspace_path,
        paths.context_path,
        paths.criteria_path,
        paths.wiki_path,
        paths.outputs_path,
        paths.artifacts_path,
        paths.tmp_path,
        paths.transfers_path,
        paths.runtime_path,
        paths.attempts_path,
        paths.dispatch_path,
    ):
        path.mkdir(parents=True, exist_ok=True)


def assignment_json_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return attempt_dir_path(paths=paths, attempt_id=attempt_id) / "assignment.json"


def assignment_markdown_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return attempt_dir_path(paths=paths, attempt_id=attempt_id) / "assignment.md"


def checkpoint_json_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return attempt_dir_path(paths=paths, attempt_id=attempt_id) / "latest-checkpoint.json"


def checkpoint_markdown_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return attempt_dir_path(paths=paths, attempt_id=attempt_id) / "latest-checkpoint.md"


def artifact_index_json_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return attempt_dir_path(paths=paths, attempt_id=attempt_id) / "artifact-index.json"


def transient_index_json_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return attempt_dir_path(paths=paths, attempt_id=attempt_id) / "transient-index.json"


def prompt_markdown_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return dispatch_dir_path(paths=paths, dispatch_id=dispatch_id) / "prompt.md"


def prompt_request_json_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return dispatch_dir_path(paths=paths, dispatch_id=dispatch_id) / "prompt-request.json"


def delivery_state_json_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return dispatch_dir_path(paths=paths, dispatch_id=dispatch_id) / "delivery-state.json"


def continuity_state_json_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return dispatch_dir_path(paths=paths, dispatch_id=dispatch_id) / "continuity-state.json"


def watchdog_state_json_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return dispatch_dir_path(paths=paths, dispatch_id=dispatch_id) / "watchdog-state.json"


def provider_events_ndjson_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return dispatch_dir_path(paths=paths, dispatch_id=dispatch_id) / "provider-events.ndjson"


def criteria_file_path(
    *,
    paths: TaskRootPaths,
    slot: str,
    version: int | None = None,
) -> Path:
    if version is None:
        return paths.criteria_path / f"{slot}.md"
    return paths.criteria_path / f"{slot}.v{version:02d}.md"


def manifest_json_path(paths: TaskRootPaths) -> Path:
    return paths.runtime_path / "workflow-manifest.json"


def manifest_markdown_path(paths: TaskRootPaths) -> Path:
    return paths.runtime_path / "workflow-manifest.md"


def artifact_current_json_path(
    *,
    paths: TaskRootPaths,
    owner_node_key: str,
    slot: str,
) -> Path:
    return paths.artifacts_path / owner_node_key / slot / "current.json"


def attempt_dir_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return paths.attempts_path / attempt_id


def dispatch_dir_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return paths.dispatch_path / dispatch_id


def coerce_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _binding_or_default(binding: TaskRootBindingInput | None) -> TaskRootBindingInput:
    if binding is not None:
        return binding
    return TaskRootBindingInput()


def _resolve_bound_root(
    *,
    task_root: Path,
    root_name: str,
    binding: TaskRootBindingInput,
) -> Path:
    if binding.mode == TaskRootMode.ENSURE_TASK_DEFAULT:
        return task_root / root_name

    assert binding.host_path is not None
    host_path = coerce_path(binding.host_path)
    if binding.mode == TaskRootMode.USE_EXISTING_HOST and not host_path.exists():
        raise FileNotFoundError(
            f"{root_name} host path does not exist for use_existing_host: {host_path}"
        )
    return host_path
