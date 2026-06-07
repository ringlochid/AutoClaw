from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from autoclaw.definitions.compiler import NormalizedCompiledPlan
from autoclaw.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    ManifestProjection,
    PersistedPromptRecord,
    TaskRootPaths,
)
from autoclaw.runtime.prompt.bundle import (
    render_assignment_markdown,
    render_checkpoint_markdown,
    render_manifest_markdown,
)
from autoclaw.runtime.task_root.paths import (
    assignment_json_path,
    assignment_markdown_path,
    attempt_dir_path,
    checkpoint_json_path,
    checkpoint_markdown_path,
    criteria_file_path,
    manifest_json_path,
    manifest_markdown_path,
)


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


def stable_json_hash(payload: object) -> str:
    materialized = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    encoded = json.dumps(materialized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def write_manifest_projection(*, paths: TaskRootPaths, manifest: ManifestProjection) -> None:
    write_json_file(manifest_json_path(paths), manifest)
    manifest_markdown_path(paths).write_text(render_manifest_markdown(manifest), encoding="utf-8")


def write_assignment_projection(
    *,
    paths: TaskRootPaths,
    attempt_id: str,
    assignment: AssignmentProjection,
) -> None:
    attempt_dir = attempt_dir_path(paths=paths, attempt_id=attempt_id)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    write_json_file(assignment_json_path(paths=paths, attempt_id=attempt_id), assignment)
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
    write_json_file(checkpoint_json_path(paths=paths, attempt_id=attempt_id), checkpoint)
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
    write_json_file(
        prompt_record.transport_request_path,
        {
            "dispatch_id": prompt_record.dispatch_id,
            "node_key": prompt_record.node_key,
            "attempt_id": prompt_record.attempt_id,
            "assignment_key": prompt_record.assignment_key,
            "prompt_name": prompt_record.prompt_name,
            "send_mode": prompt_record.send_mode,
            "instructions_text": prompt_record.transport_request.instructions_text,
            "input_text": prompt_record.transport_request.input_text,
            "content_hash": prompt_record.content_hash,
            "transport_request_hash": prompt_record.transport_request_hash,
            "rendered_at": prompt_record.rendered_at.isoformat(),
        },
    )


def write_json_file(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(json.dumps(materialized, indent=2, sort_keys=True), encoding="utf-8")


def write_ndjson_file(path: Path, rows: Sequence[object]) -> None:
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
