from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from pydantic import BaseModel

from app.compiler import NormalizedCompiledPlan
from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    ManifestProjection,
    PersistedPromptRecord,
    TaskComposeInput,
    TaskRootBindingInput,
    TaskRootMode,
    TaskRootPaths,
)
from app.runtime.prompt.bundle import (
    render_assignment_markdown,
    render_checkpoint_markdown,
    render_manifest_markdown,
)


def _coerce_path(path: str | Path) -> Path:
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
    host_path = _coerce_path(binding.host_path)
    if binding.mode == TaskRootMode.USE_EXISTING_HOST and not host_path.exists():
        raise FileNotFoundError(
            f"{root_name} host path does not exist for use_existing_host: {host_path}"
        )
    return host_path


def resolve_task_root_paths(
    *,
    task_root: Path,
    task_compose: TaskComposeInput,
) -> TaskRootPaths:
    roots = task_compose.roots
    task_root_path = _coerce_path(task_root)
    workspace_binding = _binding_or_default(roots.workspace if roots is not None else None)
    context_binding = _binding_or_default(roots.context if roots is not None else None)
    context_path = _resolve_bound_root(
        task_root=task_root_path,
        root_name="context",
        binding=context_binding,
    )
    return TaskRootPaths(
        task_root=task_root_path,
        workspace_path=_resolve_bound_root(
            task_root=task_root_path,
            root_name="workspace",
            binding=workspace_binding,
        ),
        context_path=context_path,
        criteria_path=context_path / "criteria",
        wiki_path=context_path / "wiki",
        outputs_path=task_root_path / "outputs",
        artifacts_path=task_root_path / "outputs" / "artifacts",
        tmp_path=task_root_path / "tmp",
        transfers_path=task_root_path / "tmp" / "transfers",
        runtime_path=task_root_path / "_runtime",
        attempts_path=task_root_path / "_runtime" / "attempts",
        dispatch_path=task_root_path / "_runtime" / "dispatch",
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


def criteria_file_path(*, paths: TaskRootPaths, slot: str, version: int | None = None) -> Path:
    if version is None:
        return paths.criteria_path / f"{slot}.md"
    return paths.criteria_path / f"{slot}.v{version:02d}.md"


def manifest_json_path(paths: TaskRootPaths) -> Path:
    return paths.runtime_path / "workflow-manifest.json"


def manifest_markdown_path(paths: TaskRootPaths) -> Path:
    return paths.runtime_path / "workflow-manifest.md"


def attempt_dir_path(*, paths: TaskRootPaths, attempt_id: str) -> Path:
    return paths.attempts_path / attempt_id


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


def dispatch_dir_path(*, paths: TaskRootPaths, dispatch_id: str) -> Path:
    return paths.dispatch_path / dispatch_id


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


def artifact_current_json_path(
    *,
    paths: TaskRootPaths,
    owner_node_key: str,
    slot: str,
) -> Path:
    return paths.artifacts_path / owner_node_key / slot / "current.json"


def write_criteria_files(
    *,
    paths: TaskRootPaths,
    compiled_plan: NormalizedCompiledPlan,
) -> dict[str, Path]:
    criteria_paths: dict[str, Path] = {}
    for node in compiled_plan.nodes:
        for criteria in node.criteria:
            path = criteria_file_path(paths=paths, slot=criteria.slot, version=1)
            lines = [f"# {criteria.slot}", "", criteria.description, ""]
            lines.extend(f"- {criterion}" for criterion in criteria.criteria)
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            compatibility_path = criteria_file_path(paths=paths, slot=criteria.slot)
            compatibility_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            criteria_paths[criteria.slot] = path
    return criteria_paths


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(json.dumps(materialized, indent=2, sort_keys=True), encoding="utf-8")


def write_json_file(path: Path, payload: object) -> None:
    _write_json(path, payload)


def stable_json_hash(payload: object) -> str:
    materialized = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    encoded = json.dumps(materialized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def write_manifest_projection(*, paths: TaskRootPaths, manifest: ManifestProjection) -> None:
    _write_json(manifest_json_path(paths), manifest)
    manifest_markdown_path(paths).write_text(render_manifest_markdown(manifest), encoding="utf-8")


def write_assignment_projection(
    *,
    paths: TaskRootPaths,
    attempt_id: str,
    assignment: AssignmentProjection,
) -> None:
    attempt_dir = attempt_dir_path(paths=paths, attempt_id=attempt_id)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    _write_json(assignment_json_path(paths=paths, attempt_id=attempt_id), assignment)
    assignment_markdown_path(paths=paths, attempt_id=attempt_id).write_text(
        render_assignment_markdown(assignment),
        encoding="utf-8",
    )


def write_checkpoint_projection(
    *,
    paths: TaskRootPaths,
    attempt_id: str,
    checkpoint: CheckpointProjection,
) -> None:
    attempt_dir = attempt_dir_path(paths=paths, attempt_id=attempt_id)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    _write_json(checkpoint_json_path(paths=paths, attempt_id=attempt_id), checkpoint)
    checkpoint_markdown_path(paths=paths, attempt_id=attempt_id).write_text(
        render_checkpoint_markdown(checkpoint),
        encoding="utf-8",
    )


def write_prompt_artifact(
    *,
    paths: TaskRootPaths,
    prompt_record: PersistedPromptRecord,
    full_markdown: str,
) -> None:
    del paths
    prompt_path = prompt_record.rendered_markdown_path
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(full_markdown, encoding="utf-8")
    _write_json(
        prompt_record.transport_request_path,
        {
            "dispatch_id": prompt_record.dispatch_id,
            "node_key": prompt_record.node_key,
            "attempt_id": prompt_record.attempt_id,
            "assignment_key": prompt_record.assignment_key,
            "prompt_name": prompt_record.prompt_name,
            "send_mode": prompt_record.send_mode,
            "previous_response_id": prompt_record.transport_request.previous_response_id,
            "instructions_text": prompt_record.transport_request.instructions_text,
            "input_text": prompt_record.transport_request.input_text,
            "content_hash": prompt_record.content_hash,
            "transport_request_hash": prompt_record.transport_request_hash,
            "rendered_at": prompt_record.rendered_at.isoformat(),
        },
    )


def write_ndjson_file(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded_rows: list[str] = []
    for row in rows:
        materialized: object
        if isinstance(row, BaseModel):
            materialized = row.model_dump(mode="json")
        else:
            materialized = row
        encoded_rows.append(json.dumps(materialized, sort_keys=True))
    path.write_text("\n".join(encoded_rows) + ("\n" if encoded_rows else ""), encoding="utf-8")


def localize_external_resource(
    *,
    paths: TaskRootPaths,
    source_path: Path,
    target_name: str | None = None,
) -> Path:
    resolved_source = _coerce_path(source_path)
    if not resolved_source.is_file():
        raise FileNotFoundError(f"external resource does not exist: {resolved_source}")

    try:
        resolved_source.relative_to(paths.task_root)
    except ValueError:
        pass
    else:
        return resolved_source

    destination_name = target_name or resolved_source.name
    destination = paths.context_path / destination_name
    if destination.exists():
        if (
            hashlib.sha256(destination.read_bytes()).digest()
            == hashlib.sha256(resolved_source.read_bytes()).digest()
        ):
            return destination
        suffix_hash = hashlib.sha256(resolved_source.read_bytes()).hexdigest()[:8]
        destination = paths.context_path / (
            f"{resolved_source.stem}-{suffix_hash}{resolved_source.suffix}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved_source, destination)
    return destination


def localize_transient_surface(
    *,
    paths: TaskRootPaths,
    source_path: Path,
    owner_node_key: str,
    target_name: str | None = None,
) -> Path:
    destination = planned_transient_surface_path(
        paths=paths,
        source_path=source_path,
        owner_node_key=owner_node_key,
        target_name=target_name,
    )
    resolved_source = _coerce_path(source_path)
    copy_file_if_needed(source_path=resolved_source, destination=destination)
    return destination


def planned_transient_surface_path(
    *,
    paths: TaskRootPaths,
    source_path: Path,
    owner_node_key: str,
    target_name: str | None = None,
) -> Path:
    resolved_source = _coerce_path(source_path)
    if not resolved_source.is_file():
        raise FileNotFoundError(f"transient surface does not exist: {resolved_source}")

    try:
        resolved_source.relative_to(paths.transfers_path)
    except ValueError:
        pass
    else:
        return resolved_source

    try:
        resolved_source.relative_to(paths.task_root)
    except ValueError:
        pass

    destination_root = paths.transfers_path / owner_node_key
    destination_name = target_name or resolved_source.name
    destination = destination_root / destination_name
    if destination.exists():
        if (
            hashlib.sha256(destination.read_bytes()).digest()
            == hashlib.sha256(resolved_source.read_bytes()).digest()
        ):
            return destination
        suffix_hash = hashlib.sha256(resolved_source.read_bytes()).hexdigest()[:8]
        destination = (
            destination_root / f"{resolved_source.stem}-{suffix_hash}{resolved_source.suffix}"
        )

    return destination


def copy_file_if_needed(*, source_path: Path, destination: Path) -> None:
    if source_path == destination:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)
