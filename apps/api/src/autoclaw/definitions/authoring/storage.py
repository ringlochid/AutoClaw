from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

import yaml
from pydantic import BaseModel, ConfigDict, Field

from autoclaw.definitions.contracts import (
    DefinitionContent,
    DefinitionKind,
    PolicyDefinitionFile,
    PolicyDefinitionInput,
    RoleDefinitionFile,
    RoleDefinitionInput,
    WorkflowDefinitionFile,
    WorkflowDefinitionInput,
)
from autoclaw.runtime.errors import missing_resource_error


class StoredDraftBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_no: int | None = Field(default=None, ge=1)
    content_hash: str | None = None
    source_path: str | None = None


class StoredDraftFileEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: DefinitionKind
    key: str
    draft_path: str
    normalized_path: str
    body_format: str = "yaml"
    content_hash: str
    based_on: StoredDraftBaseline = Field(default_factory=StoredDraftBaseline)
    baseline_body: str
    baseline_normalized_content: dict[str, Any] | None = None


class StoredDraftSetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_set_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    state: str = "open"
    files: list[StoredDraftFileEntry] = Field(default_factory=list)
    preview_task_compose_path: str | None = None


PREVIEW_TASK_COMPOSE_RELATIVE_PATH = "task-compose.preview.yaml"


def read_stored_draft_set(data_dir: Path, draft_set_id: str) -> StoredDraftSetManifest:
    manifest_path = _draft_set_directory(data_dir, draft_set_id) / "draft-set.json"
    if not manifest_path.is_file():
        raise missing_resource_error(f"unknown draft set '{draft_set_id}'")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return StoredDraftSetManifest.model_validate(payload)


def list_stored_draft_sets(data_dir: Path) -> list[StoredDraftSetManifest]:
    root = _draft_sets_root(data_dir)
    if not root.is_dir():
        return []

    manifests: list[StoredDraftSetManifest] = []
    for draft_dir in sorted(root.iterdir()):
        manifest_path = draft_dir / "draft-set.json"
        if not manifest_path.is_file():
            continue
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifests.append(StoredDraftSetManifest.model_validate(payload))
    return manifests


def write_stored_draft_set(data_dir: Path, manifest: StoredDraftSetManifest) -> None:
    draft_dir = _draft_set_directory(data_dir, manifest.draft_set_id)
    draft_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = draft_dir / "draft-set.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def delete_stored_draft_set(data_dir: Path, draft_set_id: str) -> None:
    draft_dir = _draft_set_directory(data_dir, draft_set_id)
    if not draft_dir.is_dir():
        raise missing_resource_error(f"unknown draft set '{draft_set_id}'")
    for path in sorted(draft_dir.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    draft_dir.rmdir()


def find_manifest_file_entry(
    manifest: StoredDraftSetManifest,
    *,
    kind: DefinitionKind,
    key: str,
) -> StoredDraftFileEntry | None:
    for entry in manifest.files:
        if entry.kind == kind and entry.key == key:
            return entry
    return None


def write_definition_draft_files(
    data_dir: Path,
    draft_set_id: str,
    *,
    entry: StoredDraftFileEntry,
    body: str,
    normalized_content: dict[str, Any] | None,
) -> None:
    draft_path = _draft_set_directory(data_dir, draft_set_id) / entry.draft_path
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(body, encoding="utf-8")

    normalized_path = _draft_set_directory(data_dir, draft_set_id) / entry.normalized_path
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    if normalized_content is None:
        if normalized_path.exists():
            normalized_path.unlink()
        return
    normalized_path.write_text(
        json.dumps(normalized_content, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def delete_definition_draft_files(
    data_dir: Path,
    draft_set_id: str,
    *,
    entry: StoredDraftFileEntry,
) -> None:
    draft_dir = _draft_set_directory(data_dir, draft_set_id)
    for relative_path in (entry.draft_path, entry.normalized_path):
        path = draft_dir / relative_path
        if path.is_file():
            path.unlink()
        _prune_empty_draft_directories(path.parent, stop_at=draft_dir)


def write_preview_task_compose_body(data_dir: Path, draft_set_id: str, body: str) -> None:
    preview_path = _preview_task_compose_path(data_dir, draft_set_id)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(body, encoding="utf-8")


def read_preview_task_compose_body(data_dir: Path, draft_set_id: str) -> str | None:
    preview_path = _preview_task_compose_path(data_dir, draft_set_id)
    if not preview_path.is_file():
        return None
    return preview_path.read_text(encoding="utf-8")


def read_definition_draft_body(
    data_dir: Path,
    draft_set_id: str,
    entry: StoredDraftFileEntry,
) -> str:
    draft_path = _draft_set_directory(data_dir, draft_set_id) / entry.draft_path
    return draft_path.read_text(encoding="utf-8")


def read_definition_draft_normalized_content(
    data_dir: Path,
    draft_set_id: str,
    entry: StoredDraftFileEntry,
) -> dict[str, Any] | None:
    normalized_path = _draft_set_directory(data_dir, draft_set_id) / entry.normalized_path
    if not normalized_path.is_file():
        return None
    return cast(
        dict[str, Any],
        json.loads(normalized_path.read_text(encoding="utf-8")),
    )


def draft_file_relative_path(kind: DefinitionKind, key: str) -> str:
    return f"{kind.value}s/{_quoted_key_filename(key)}.yaml"


def normalized_file_relative_path(kind: DefinitionKind, key: str) -> str:
    return f"_normalized/{kind.value}s/{_quoted_key_filename(key)}.json"


def draft_body_content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def serialize_definition_content(kind: DefinitionKind, content: DefinitionContent) -> str:
    payload = {"kind": kind.value, **content.model_dump(mode="json")}
    return yaml.safe_dump(payload, sort_keys=False)


def normalize_definition_content(content: DefinitionContent) -> dict[str, Any]:
    return content.model_dump(mode="json")


def parse_definition_body(
    kind: DefinitionKind,
    key: str,
    body: str,
) -> DefinitionContent:
    try:
        payload = yaml.safe_load(body)
    except yaml.YAMLError as exc:  # pragma: no cover - exercised through invalid YAML tests
        raise ValueError(f"invalid YAML: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("expected YAML mapping content")
    payload_kind = payload.get("kind")
    if payload_kind != kind.value:
        raise ValueError(
            f"draft body kind '{payload_kind}' does not match requested kind '{kind.value}'"
        )

    content: DefinitionContent
    if kind == DefinitionKind.ROLE:
        content = RoleDefinitionInput.model_validate(
            RoleDefinitionFile.model_validate(payload).model_dump(exclude={"kind"})
        )
    elif kind == DefinitionKind.POLICY:
        content = PolicyDefinitionInput.model_validate(
            PolicyDefinitionFile.model_validate(payload).model_dump(exclude={"kind"})
        )
    else:
        content = WorkflowDefinitionInput.model_validate(
            WorkflowDefinitionFile.model_validate(payload).model_dump(exclude={"kind"})
        )
    if content.id != key:
        raise ValueError(f"draft body id '{content.id}' does not match requested key '{key}'")
    return content


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _quoted_key_filename(key: str) -> str:
    return quote(key, safe="._-")


def _draft_sets_root(data_dir: Path) -> Path:
    return data_dir / "drafts" / "definitions"


def _draft_set_directory(data_dir: Path, draft_set_id: str) -> Path:
    return _draft_sets_root(data_dir) / draft_set_id


def _preview_task_compose_path(data_dir: Path, draft_set_id: str) -> Path:
    return _draft_set_directory(data_dir, draft_set_id) / PREVIEW_TASK_COMPOSE_RELATIVE_PATH


def _prune_empty_draft_directories(path: Path, *, stop_at: Path) -> None:
    current = path
    while current != stop_at and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


__all__ = [
    "PREVIEW_TASK_COMPOSE_RELATIVE_PATH",
    "StoredDraftBaseline",
    "StoredDraftFileEntry",
    "StoredDraftSetManifest",
    "delete_definition_draft_files",
    "delete_stored_draft_set",
    "draft_body_content_hash",
    "draft_file_relative_path",
    "find_manifest_file_entry",
    "list_stored_draft_sets",
    "normalize_definition_content",
    "normalized_file_relative_path",
    "parse_definition_body",
    "read_definition_draft_body",
    "read_definition_draft_normalized_content",
    "read_preview_task_compose_body",
    "read_stored_draft_set",
    "serialize_definition_content",
    "utc_now",
    "write_definition_draft_files",
    "write_preview_task_compose_body",
    "write_stored_draft_set",
]
