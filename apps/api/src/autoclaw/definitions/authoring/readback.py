from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from autoclaw.definitions.authoring.contracts import (
    DefinitionDraftBaselineRead,
    DefinitionDraftFileDetail,
    DefinitionDraftFileStatus,
    DefinitionDraftFileSummary,
    DefinitionDraftSetDetail,
    DefinitionDraftSetState,
    DefinitionDraftSetSummary,
)
from autoclaw.definitions.authoring.storage import (
    StoredDraftBaseline,
    StoredDraftFileEntry,
    StoredDraftSetManifest,
    draft_body_content_hash,
    draft_file_relative_path,
    find_manifest_file_entry,
    normalize_definition_content,
    normalized_file_relative_path,
    parse_definition_body,
    read_definition_draft_body,
    read_definition_draft_normalized_content,
    read_preview_task_compose_body,
    serialize_definition_content,
    write_definition_draft_files,
)
from autoclaw.definitions.contracts import (
    DefinitionContent,
    DefinitionKind,
    PolicyDefinitionInput,
    RoleDefinitionInput,
    WorkflowDefinitionInput,
)
from autoclaw.persistence.models import (
    PolicyDefinitionModel,
    RoleDefinitionModel,
    WorkflowDefinitionModel,
)
from autoclaw.runtime.errors import invalid_request_shape_error


@dataclass(frozen=True)
class CurrentDefinitionSnapshot:
    kind: DefinitionKind
    key: str
    content: DefinitionContent
    revision_no: int
    content_hash: str
    source_path: str | None


@dataclass(frozen=True)
class ParsedDraftDefinition:
    content: DefinitionContent | None
    normalized_content: dict[str, Any] | None
    error: str | None


async def build_draft_set_summary(
    session: AsyncSession,
    *,
    data_dir: Path,
    manifest: StoredDraftSetManifest,
) -> DefinitionDraftSetSummary:
    current_snapshots = await load_current_definition_snapshots(session, entries=manifest.files)
    file_summaries: list[DefinitionDraftFileSummary] = []
    for entry in manifest.files:
        body = read_definition_draft_body(data_dir, manifest.draft_set_id, entry)
        parsed = parse_definition_body_for_storage(kind=entry.kind, key=entry.key, body=body)
        file_summaries.append(
            build_file_summary(
                entry=entry,
                body=body,
                parsed=parsed,
                current_snapshot=current_snapshots.get((entry.kind, entry.key)),
            )
        )

    return DefinitionDraftSetSummary(
        draft_set_id=manifest.draft_set_id,
        title=manifest.title,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        state=draft_set_state(manifest, tuple(file_summaries)),
        files=tuple(file_summaries),
        preview_task_compose_path=manifest.preview_task_compose_path,
    )


async def build_draft_set_detail(
    session: AsyncSession,
    *,
    data_dir: Path,
    manifest: StoredDraftSetManifest,
) -> DefinitionDraftSetDetail:
    current_snapshots = await load_current_definition_snapshots(session, entries=manifest.files)
    file_details: list[DefinitionDraftFileDetail] = []
    for entry in manifest.files:
        body = read_definition_draft_body(data_dir, manifest.draft_set_id, entry)
        parsed = parse_definition_body_for_storage(kind=entry.kind, key=entry.key, body=body)
        normalized_content = read_definition_draft_normalized_content(
            data_dir,
            manifest.draft_set_id,
            entry,
        )
        summary = build_file_summary(
            entry=entry,
            body=body,
            parsed=parsed,
            current_snapshot=current_snapshots.get((entry.kind, entry.key)),
        )
        file_details.append(
            DefinitionDraftFileDetail(
                **summary.model_dump(mode="python"),
                body=body,
                normalized_content=normalized_content,
                baseline_body=entry.baseline_body,
                baseline_normalized_content=entry.baseline_normalized_content,
            )
        )

    return DefinitionDraftSetDetail(
        draft_set_id=manifest.draft_set_id,
        title=manifest.title,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        state=draft_set_state(manifest, tuple(file_details)),
        files=tuple(file_details),
        preview_task_compose_path=manifest.preview_task_compose_path,
        preview_task_compose_body=read_preview_task_compose_body(data_dir, manifest.draft_set_id),
    )


def build_file_summary(
    *,
    entry: StoredDraftFileEntry,
    body: str,
    parsed: ParsedDraftDefinition,
    current_snapshot: CurrentDefinitionSnapshot | None,
) -> DefinitionDraftFileSummary:
    return DefinitionDraftFileSummary(
        kind=entry.kind,
        key=entry.key,
        draft_path=entry.draft_path,
        normalized_path=entry.normalized_path,
        body_format="yaml",
        content_hash=entry.content_hash,
        based_on=DefinitionDraftBaselineRead.model_validate(
            entry.based_on.model_dump(mode="python")
        ),
        status=draft_file_status(
            entry=entry,
            body=body,
            parsed=parsed,
            current_snapshot=current_snapshot,
        ),
    )


def draft_set_state(
    manifest: StoredDraftSetManifest,
    files: tuple[DefinitionDraftFileSummary, ...] | tuple[DefinitionDraftFileDetail, ...],
) -> DefinitionDraftSetState:
    if any(file.status == DefinitionDraftFileStatus.STALE for file in files):
        return DefinitionDraftSetState.STALE
    if manifest.state == DefinitionDraftSetState.APPLIED.value:
        return DefinitionDraftSetState.APPLIED
    return DefinitionDraftSetState.OPEN


def draft_file_status(
    *,
    entry: StoredDraftFileEntry,
    body: str,
    parsed: ParsedDraftDefinition,
    current_snapshot: CurrentDefinitionSnapshot | None,
) -> DefinitionDraftFileStatus:
    if parsed.error is not None:
        return DefinitionDraftFileStatus.INVALID
    if entry_is_stale(entry, current_snapshot=current_snapshot):
        return DefinitionDraftFileStatus.STALE
    if entry.based_on.revision_no is None:
        return DefinitionDraftFileStatus.ADDED
    if body == entry.baseline_body:
        return DefinitionDraftFileStatus.CLEAN
    return DefinitionDraftFileStatus.MODIFIED


def entry_is_stale(
    entry: StoredDraftFileEntry,
    *,
    current_snapshot: CurrentDefinitionSnapshot | None,
) -> bool:
    if entry.based_on.revision_no is None:
        return current_snapshot is not None
    if current_snapshot is None:
        return True
    return (
        entry.based_on.revision_no != current_snapshot.revision_no
        or entry.based_on.content_hash != current_snapshot.content_hash
    )


async def materialize_definition_entry(
    session: AsyncSession,
    *,
    data_dir: Path,
    manifest: StoredDraftSetManifest,
    kind: DefinitionKind,
    key: str,
    should_allow_existing_entry: bool,
) -> StoredDraftFileEntry:
    existing_entry = find_manifest_file_entry(manifest, kind=kind, key=key)
    if existing_entry is not None and not should_allow_existing_entry:
        raise invalid_request_shape_error(f"draft set already materializes {kind.value} '{key}'")
    current_snapshot = await _require_current_definition_snapshot(session, kind=kind, key=key)
    body = serialize_definition_content(kind, current_snapshot.content)
    normalized_content = normalize_definition_content(current_snapshot.content)
    entry = StoredDraftFileEntry(
        kind=kind,
        key=key,
        draft_path=draft_file_relative_path(kind, key),
        normalized_path=normalized_file_relative_path(kind, key),
        body_format="yaml",
        content_hash=draft_body_content_hash(body),
        based_on=StoredDraftBaseline(
            revision_no=current_snapshot.revision_no,
            content_hash=current_snapshot.content_hash,
            source_path=current_snapshot.source_path,
        ),
        baseline_body=body,
        baseline_normalized_content=normalized_content,
    )
    write_definition_draft_files(
        data_dir,
        manifest.draft_set_id,
        entry=entry,
        body=body,
        normalized_content=normalized_content,
    )
    _update_manifest_file_entry(manifest, entry)
    return entry


async def load_current_definition_snapshots(
    session: AsyncSession,
    *,
    entries: list[StoredDraftFileEntry],
) -> dict[tuple[DefinitionKind, str], CurrentDefinitionSnapshot]:
    snapshots: dict[tuple[DefinitionKind, str], CurrentDefinitionSnapshot] = {}
    for entry in entries:
        snapshot = await load_current_definition_snapshot(session, kind=entry.kind, key=entry.key)
        if snapshot is not None:
            snapshots[(entry.kind, entry.key)] = snapshot
    return snapshots


async def load_current_definition_snapshot(
    session: AsyncSession,
    *,
    kind: DefinitionKind,
    key: str,
) -> CurrentDefinitionSnapshot | None:
    if kind == DefinitionKind.ROLE:
        row = await session.scalar(
            select(RoleDefinitionModel)
            .options(joinedload(RoleDefinitionModel.current_revision))
            .where(RoleDefinitionModel.role_key == key)
        )
        if row is None or row.current_revision is None or row.current_revision_no is None:
            return None
        return CurrentDefinitionSnapshot(
            kind=kind,
            key=key,
            content=RoleDefinitionInput.model_validate(row.current_revision.content_json),
            revision_no=row.current_revision.revision_no,
            content_hash=row.current_revision.content_hash,
            source_path=row.current_revision.source_path,
        )

    if kind == DefinitionKind.POLICY:
        row = await session.scalar(
            select(PolicyDefinitionModel)
            .options(joinedload(PolicyDefinitionModel.current_revision))
            .where(PolicyDefinitionModel.policy_key == key)
        )
        if row is None or row.current_revision is None or row.current_revision_no is None:
            return None
        return CurrentDefinitionSnapshot(
            kind=kind,
            key=key,
            content=PolicyDefinitionInput.model_validate(row.current_revision.content_json),
            revision_no=row.current_revision.revision_no,
            content_hash=row.current_revision.content_hash,
            source_path=row.current_revision.source_path,
        )

    row = await session.scalar(
        select(WorkflowDefinitionModel)
        .options(joinedload(WorkflowDefinitionModel.current_revision))
        .where(WorkflowDefinitionModel.workflow_key == key)
    )
    if row is None or row.current_revision is None or row.current_revision_no is None:
        return None
    return CurrentDefinitionSnapshot(
        kind=kind,
        key=key,
        content=WorkflowDefinitionInput.model_validate(row.current_revision.content_json),
        revision_no=row.current_revision.revision_no,
        content_hash=row.current_revision.content_hash,
        source_path=row.current_revision.source_path,
    )


def parse_definition_body_for_storage(
    *,
    kind: DefinitionKind,
    key: str,
    body: str,
) -> ParsedDraftDefinition:
    try:
        content = parse_definition_body(kind, key, body)
    except ValueError as exc:
        return ParsedDraftDefinition(content=None, normalized_content=None, error=str(exc))
    return ParsedDraftDefinition(
        content=content,
        normalized_content=normalize_definition_content(content),
        error=None,
    )


def require_manifest_file_entry(
    manifest: StoredDraftSetManifest,
    *,
    kind: DefinitionKind,
    key: str,
) -> StoredDraftFileEntry:
    entry = find_manifest_file_entry(manifest, kind=kind, key=key)
    if entry is None:
        raise FileNotFoundError(
            f"draft set '{manifest.draft_set_id}' does not include {kind.value} '{key}'"
        )
    return entry


def parse_cursor_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise invalid_request_shape_error("cursor must be an integer offset") from exc
    if offset < 0:
        raise invalid_request_shape_error("cursor must be non-negative")
    return offset


def next_cursor(offset: int, limit: int, selected_count: int) -> str | None:
    return str(offset + limit) if selected_count > limit else None


async def _require_current_definition_snapshot(
    session: AsyncSession,
    *,
    kind: DefinitionKind,
    key: str,
) -> CurrentDefinitionSnapshot:
    snapshot = await load_current_definition_snapshot(session, kind=kind, key=key)
    if snapshot is None:
        raise FileNotFoundError(f"unknown definition key '{key}'")
    return snapshot


def _update_manifest_file_entry(
    manifest: StoredDraftSetManifest,
    entry: StoredDraftFileEntry,
) -> None:
    for index, existing_entry in enumerate(manifest.files):
        if existing_entry.kind == entry.kind and existing_entry.key == entry.key:
            manifest.files[index] = entry
            break
    else:
        manifest.files.append(entry)


__all__ = [
    "CurrentDefinitionSnapshot",
    "ParsedDraftDefinition",
    "build_draft_set_detail",
    "build_draft_set_summary",
    "build_file_summary",
    "draft_file_status",
    "draft_set_state",
    "entry_is_stale",
    "load_current_definition_snapshot",
    "load_current_definition_snapshots",
    "materialize_definition_entry",
    "next_cursor",
    "parse_cursor_offset",
    "parse_definition_body_for_storage",
    "require_manifest_file_entry",
]
