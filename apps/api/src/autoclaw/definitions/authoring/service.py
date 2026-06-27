from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.authoring.contracts import (
    DefinitionDraftApplyRequest,
    DefinitionDraftApplyResponse,
    DefinitionDraftFileRematerializeCurrentRequest,
    DefinitionDraftFileResetRequest,
    DefinitionDraftFileWriteRequest,
    DefinitionDraftMaterializeRequest,
    DefinitionDraftSetCreateRequest,
    DefinitionDraftSetDetailResponse,
    DefinitionDraftSetListQuery,
    DefinitionDraftSetListResponse,
    DefinitionDraftSetState,
    DefinitionDraftTaskComposePreviewRequest,
    DefinitionDraftTaskComposePreviewResponse,
    DefinitionDraftTaskStartFailure,
    DefinitionDraftTaskStartStatus,
    DefinitionDraftValidationResponse,
)
from autoclaw.definitions.authoring.publishing import publish_valid_definitions
from autoclaw.definitions.authoring.readback import (
    build_draft_set_detail,
    build_draft_set_summary,
    load_current_definition_snapshot,
    load_current_definition_snapshots,
    materialize_definition_entry,
    next_cursor,
    parse_cursor_offset,
    parse_definition_body_for_storage,
    require_manifest_file_entry,
)
from autoclaw.definitions.authoring.storage import (
    PREVIEW_TASK_COMPOSE_RELATIVE_PATH,
    StoredDraftBaseline,
    StoredDraftFileEntry,
    StoredDraftSetManifest,
    delete_definition_draft_files,
    delete_stored_draft_set,
    draft_body_content_hash,
    draft_file_relative_path,
    find_manifest_file_entry,
    list_stored_draft_sets,
    normalized_file_relative_path,
    read_stored_draft_set,
    utc_now,
    write_definition_draft_files,
    write_preview_task_compose_body,
    write_stored_draft_set,
)
from autoclaw.definitions.authoring.validation import validate_draft_set
from autoclaw.definitions.contracts import DefinitionKind
from autoclaw.definitions.registry.task_start import start_task_from_definition
from autoclaw.runtime.contracts import TaskStartRequest
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.errors import (
    RuntimeOperationError,
    illegal_state_error,
    invalid_request_shape_error,
)
from autoclaw.runtime.post_commit.operations import write_session_operation


async def list_definition_draft_sets(
    session: AsyncSession,
    *,
    data_dir: Path,
    query: DefinitionDraftSetListQuery,
) -> DefinitionDraftSetListResponse:
    manifests = list_stored_draft_sets(data_dir)
    summaries = [
        await build_draft_set_summary(session, data_dir=data_dir, manifest=manifest)
        for manifest in manifests
    ]
    ordered = sorted(summaries, key=lambda item: item.updated_at, reverse=True)
    offset = parse_cursor_offset(query.cursor)
    selected = ordered[offset : offset + query.limit + 1]
    return DefinitionDraftSetListResponse(
        items=tuple(selected[: query.limit]),
        next_cursor=next_cursor(offset, query.limit, len(selected)),
    )


async def create_definition_draft_set(
    session: AsyncSession,
    *,
    data_dir: Path,
    request: DefinitionDraftSetCreateRequest,
) -> DefinitionDraftSetDetailResponse:
    draft_set_id = f"draft-set.{uuid4().hex[:12]}"
    created_at = utc_now()
    manifest = StoredDraftSetManifest(
        draft_set_id=draft_set_id,
        title=request.title,
        created_at=created_at,
        updated_at=created_at,
        state=DefinitionDraftSetState.OPEN.value,
        preview_task_compose_path=(
            PREVIEW_TASK_COMPOSE_RELATIVE_PATH if request.preview_task_compose is not None else None
        ),
    )
    try:
        write_stored_draft_set(data_dir, manifest)
        if request.preview_task_compose is not None:
            write_preview_task_compose_body(data_dir, draft_set_id, request.preview_task_compose)
        for item in request.materialize:
            await materialize_definition_entry(
                session,
                data_dir=data_dir,
                manifest=manifest,
                kind=item.kind,
                key=item.key,
                should_allow_existing_entry=False,
            )
        write_stored_draft_set(data_dir, manifest)
    except Exception:
        draft_set_root = data_dir / "drafts" / "definitions" / draft_set_id
        if draft_set_root.exists():
            delete_stored_draft_set(data_dir, draft_set_id)
        raise
    return DefinitionDraftSetDetailResponse(
        draft_set=await build_draft_set_detail(session, data_dir=data_dir, manifest=manifest)
    )


async def read_definition_draft_set(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
) -> DefinitionDraftSetDetailResponse:
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    return DefinitionDraftSetDetailResponse(
        draft_set=await build_draft_set_detail(session, data_dir=data_dir, manifest=manifest)
    )


def delete_definition_draft_set_by_id(
    *,
    data_dir: Path,
    draft_set_id: str,
) -> None:
    delete_stored_draft_set(data_dir, draft_set_id)


async def materialize_definition_draft_set(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
    request: DefinitionDraftMaterializeRequest,
) -> DefinitionDraftSetDetailResponse:
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    materialized_entries: list[StoredDraftFileEntry] = []
    try:
        for definition in request.definitions:
            materialized_entries.append(
                await materialize_definition_entry(
                    session,
                    data_dir=data_dir,
                    manifest=manifest,
                    kind=definition.kind,
                    key=definition.key,
                    should_allow_existing_entry=False,
                )
            )
    except Exception:
        for entry in reversed(materialized_entries):
            delete_definition_draft_files(
                data_dir,
                draft_set_id,
                entry=entry,
            )
        raise
    _reopen_draft_set_for_local_change(manifest)
    write_stored_draft_set(data_dir, manifest)
    return DefinitionDraftSetDetailResponse(
        draft_set=await build_draft_set_detail(session, data_dir=data_dir, manifest=manifest)
    )


async def write_definition_draft_file(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
    kind: DefinitionKind,
    key: str,
    request: DefinitionDraftFileWriteRequest,
) -> DefinitionDraftSetDetailResponse:
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    if request.body_format != "yaml":
        raise invalid_request_shape_error("draft file body_format must be yaml")

    entry = find_manifest_file_entry(manifest, kind=kind, key=key)
    parsed = parse_definition_body_for_storage(kind=kind, key=key, body=request.body)
    if entry is None:
        current_snapshot = await load_current_definition_snapshot(session, kind=kind, key=key)
        if current_snapshot is not None:
            raise illegal_state_error(
                f"draft set does not yet materialize current {kind.value} '{key}'"
            )
        entry = StoredDraftFileEntry(
            kind=kind,
            key=key,
            draft_path=draft_file_relative_path(kind, key),
            normalized_path=normalized_file_relative_path(kind, key),
            body_format=request.body_format,
            content_hash=draft_body_content_hash(request.body),
            based_on=StoredDraftBaseline(),
            baseline_body=request.body,
            baseline_normalized_content=parsed.normalized_content,
        )
    else:
        entry.body_format = request.body_format
        entry.content_hash = draft_body_content_hash(request.body)

    write_definition_draft_files(
        data_dir,
        draft_set_id,
        entry=entry,
        body=request.body,
        normalized_content=parsed.normalized_content,
    )
    if find_manifest_file_entry(manifest, kind=kind, key=key) is None:
        manifest.files.append(entry)
    _reopen_draft_set_for_local_change(manifest)
    write_stored_draft_set(data_dir, manifest)
    return DefinitionDraftSetDetailResponse(
        draft_set=await build_draft_set_detail(session, data_dir=data_dir, manifest=manifest)
    )


async def reset_definition_draft_file(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
    kind: DefinitionKind,
    key: str,
    request: DefinitionDraftFileResetRequest,
) -> DefinitionDraftSetDetailResponse:
    _ = request
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    entry = require_manifest_file_entry(manifest, kind=kind, key=key)
    write_definition_draft_files(
        data_dir,
        draft_set_id,
        entry=entry,
        body=entry.baseline_body,
        normalized_content=entry.baseline_normalized_content,
    )
    entry.content_hash = draft_body_content_hash(entry.baseline_body)
    _reopen_draft_set_for_local_change(manifest)
    write_stored_draft_set(data_dir, manifest)
    return DefinitionDraftSetDetailResponse(
        draft_set=await build_draft_set_detail(session, data_dir=data_dir, manifest=manifest)
    )


async def rematerialize_current_definition_draft_file(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
    kind: DefinitionKind,
    key: str,
    request: DefinitionDraftFileRematerializeCurrentRequest,
) -> DefinitionDraftSetDetailResponse:
    _ = request
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    await materialize_definition_entry(
        session,
        data_dir=data_dir,
        manifest=manifest,
        kind=kind,
        key=key,
        should_allow_existing_entry=True,
    )
    _reopen_draft_set_for_local_change(manifest)
    write_stored_draft_set(data_dir, manifest)
    return DefinitionDraftSetDetailResponse(
        draft_set=await build_draft_set_detail(session, data_dir=data_dir, manifest=manifest)
    )


async def validate_definition_draft_set(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
) -> DefinitionDraftValidationResponse:
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    return (
        await validate_draft_set(
            session,
            data_dir=data_dir,
            manifest=manifest,
            is_preview_required=False,
        )
    ).response


async def preview_definition_draft_set_task_compose(
    session: AsyncSession,
    *,
    data_dir: Path,
    draft_set_id: str,
    request: DefinitionDraftTaskComposePreviewRequest,
) -> DefinitionDraftTaskComposePreviewResponse:
    if request.body_format != "yaml":
        raise invalid_request_shape_error("preview body_format must be yaml")
    manifest = read_stored_draft_set(data_dir, draft_set_id)
    manifest.preview_task_compose_path = PREVIEW_TASK_COMPOSE_RELATIVE_PATH
    _reopen_draft_set_for_local_change(manifest)
    write_preview_task_compose_body(data_dir, draft_set_id, request.body)
    write_stored_draft_set(data_dir, manifest)
    outcome = await validate_draft_set(
        session,
        data_dir=data_dir,
        manifest=manifest,
        is_preview_required=True,
        preview_body=request.body,
    )
    return DefinitionDraftTaskComposePreviewResponse(
        status="valid" if outcome.response.status == "valid" else "invalid",
        validation=outcome.response,
    )


async def publish_definition_draft_set(
    session: AsyncSession | None,
    *,
    data_dir: Path,
    draft_set_id: str,
    request: DefinitionDraftApplyRequest,
) -> DefinitionDraftApplyResponse:
    manifest = read_stored_draft_set(data_dir, draft_set_id)

    async def _apply(
        active_session: AsyncSession,
    ) -> tuple[
        DefinitionDraftApplyResponse,
        StoredDraftSetManifest | None,
        object | None,
    ]:
        outcome = await validate_draft_set(
            active_session,
            data_dir=data_dir,
            manifest=manifest,
            is_preview_required=request.should_start_task_after_apply,
        )
        if outcome.response.status != "valid":
            return (
                DefinitionDraftApplyResponse(
                    draft_set_id=draft_set_id,
                    status="stale" if outcome.response.status == "stale" else "invalid",
                    published_revisions=(),
                    started_task_id=None,
                    validation=outcome.response,
                ),
                None,
                None,
            )

        current_snapshots = await load_current_definition_snapshots(
            active_session,
            entries=manifest.files,
        )
        published_revisions, refreshed_manifest = await publish_valid_definitions(
            active_session,
            manifest=manifest,
            data_dir=data_dir,
            valid_definitions=outcome.valid_definitions,
            existing_content_hashes={
                key: snapshot.content_hash for key, snapshot in current_snapshots.items()
            },
        )
        return (
            DefinitionDraftApplyResponse(
                draft_set_id=draft_set_id,
                status="applied",
                published_revisions=tuple(published_revisions),
                started_task_id=None,
                validation=outcome.response,
            ),
            refreshed_manifest,
            outcome.preview_request,
        )

    apply_response, refreshed_manifest, preview_request = await write_session_operation(
        _apply,
        session=session,
    )
    if refreshed_manifest is None:
        return apply_response

    write_stored_draft_set(data_dir, refreshed_manifest)
    if request.should_start_task_after_apply:
        assert preview_request is not None
        task_start_status, started_task_id, task_start_failure = await _start_task_after_apply(
            cast(TaskStartRequest, preview_request)
        )
        return apply_response.model_copy(
            update={
                "started_task_id": started_task_id,
                "task_start_status": task_start_status,
                "task_start_failure": task_start_failure,
            }
        )
    return apply_response


def _reopen_draft_set_for_local_change(manifest: StoredDraftSetManifest) -> None:
    manifest.state = DefinitionDraftSetState.OPEN.value
    manifest.updated_at = utc_now()


async def _start_task_after_apply(
    request: TaskStartRequest,
) -> tuple[
    DefinitionDraftTaskStartStatus,
    str | None,
    DefinitionDraftTaskStartFailure | None,
]:
    try:
        started_task = await start_task_from_definition(request)
    except Exception as exc:
        return (
            DefinitionDraftTaskStartStatus.FAILED,
            None,
            _task_start_failure_from_exception(exc),
        )
    return DefinitionDraftTaskStartStatus.STARTED, started_task.task_id, None


def _task_start_failure_from_exception(exc: Exception) -> DefinitionDraftTaskStartFailure:
    if isinstance(exc, RuntimeOperationError):
        return DefinitionDraftTaskStartFailure(
            code=exc.code,
            summary=exc.summary,
            is_retryable=exc.is_retryable,
            suggested_next_step=exc.suggested_next_step,
        )
    if isinstance(exc, FileNotFoundError):
        return DefinitionDraftTaskStartFailure(
            code=OperationFailureCode.MISSING_RESOURCE,
            summary=str(exc),
            is_retryable=False,
            suggested_next_step=(
                "Verify the published workflow, role, and policy keys, then resend the saved "
                "preview task-start request against current registry truth."
            ),
        )
    return DefinitionDraftTaskStartFailure(
        code=OperationFailureCode.INTERNAL_ERROR,
        summary=str(exc),
        is_retryable=False,
        suggested_next_step=(
            "Do not treat registry apply as rolled back. Reread the published definition "
            "revision and the saved preview task-start body before retrying task start."
        ),
    )


__all__ = [
    "create_definition_draft_set",
    "delete_definition_draft_set_by_id",
    "list_definition_draft_sets",
    "materialize_definition_draft_set",
    "preview_definition_draft_set_task_compose",
    "publish_definition_draft_set",
    "read_definition_draft_set",
    "rematerialize_current_definition_draft_file",
    "reset_definition_draft_file",
    "validate_definition_draft_set",
    "write_definition_draft_file",
]
