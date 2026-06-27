from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.definitions.authoring import (
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
    DefinitionDraftTaskComposePreviewRequest,
    DefinitionDraftTaskComposePreviewResponse,
    DefinitionDraftValidationResponse,
    create_definition_draft_set,
    delete_definition_draft_set_by_id,
    list_definition_draft_sets,
    materialize_definition_draft_set,
    preview_definition_draft_set_task_compose,
    publish_definition_draft_set,
    read_definition_draft_set,
    rematerialize_current_definition_draft_file,
    reset_definition_draft_file,
    validate_definition_draft_set,
    write_definition_draft_file,
)
from autoclaw.definitions.contracts import DefinitionKind
from autoclaw.interfaces.http.dependencies import require_api_key
from autoclaw.interfaces.http.errors import raise_runtime_exception
from autoclaw.persistence.session import get_db_session

router = APIRouter(
    prefix="/authoring",
    tags=["authoring"],
    dependencies=[Depends(require_api_key)],
)
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]
type DefinitionDraftSetListParams = Annotated[DefinitionDraftSetListQuery, Query()]


@router.get("/definition-draft-sets", response_model=DefinitionDraftSetListResponse)
async def get_definition_draft_sets(
    session: DBSession,
    query: DefinitionDraftSetListParams,
) -> DefinitionDraftSetListResponse:
    try:
        return await list_definition_draft_sets(
            session,
            data_dir=get_settings().data_dir,
            query=query,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post("/definition-draft-sets", response_model=DefinitionDraftSetDetailResponse)
async def post_definition_draft_set(
    request: DefinitionDraftSetCreateRequest,
    session: DBSession,
) -> DefinitionDraftSetDetailResponse:
    try:
        return await create_definition_draft_set(
            session,
            data_dir=get_settings().data_dir,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.get(
    "/definition-draft-sets/{draft_set_id}",
    response_model=DefinitionDraftSetDetailResponse,
)
async def get_definition_draft_set(
    draft_set_id: str,
    session: DBSession,
) -> DefinitionDraftSetDetailResponse:
    try:
        return await read_definition_draft_set(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.delete("/definition-draft-sets/{draft_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_definition_draft_set(
    draft_set_id: str,
) -> Response:
    try:
        delete_definition_draft_set_by_id(
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/definition-draft-sets/{draft_set_id}/materialize",
    response_model=DefinitionDraftSetDetailResponse,
)
async def post_definition_draft_set_materialize(
    draft_set_id: str,
    request: DefinitionDraftMaterializeRequest,
    session: DBSession,
) -> DefinitionDraftSetDetailResponse:
    try:
        return await materialize_definition_draft_set(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.put(
    "/definition-draft-sets/{draft_set_id}/files/{kind}/{key}",
    response_model=DefinitionDraftSetDetailResponse,
)
async def put_definition_draft_file(
    draft_set_id: str,
    kind: DefinitionKind,
    key: str,
    request: DefinitionDraftFileWriteRequest,
    session: DBSession,
) -> DefinitionDraftSetDetailResponse:
    try:
        return await write_definition_draft_file(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
            kind=kind,
            key=key,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post(
    "/definition-draft-sets/{draft_set_id}/files/{kind}/{key}/reset",
    response_model=DefinitionDraftSetDetailResponse,
)
async def post_definition_draft_file_reset(
    draft_set_id: str,
    kind: DefinitionKind,
    key: str,
    request: DefinitionDraftFileResetRequest,
    session: DBSession,
) -> DefinitionDraftSetDetailResponse:
    try:
        return await reset_definition_draft_file(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
            kind=kind,
            key=key,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post(
    "/definition-draft-sets/{draft_set_id}/files/{kind}/{key}/rematerialize-current",
    response_model=DefinitionDraftSetDetailResponse,
)
async def post_definition_draft_file_rematerialize_current(
    draft_set_id: str,
    kind: DefinitionKind,
    key: str,
    request: DefinitionDraftFileRematerializeCurrentRequest,
    session: DBSession,
) -> DefinitionDraftSetDetailResponse:
    try:
        return await rematerialize_current_definition_draft_file(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
            kind=kind,
            key=key,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post(
    "/definition-draft-sets/{draft_set_id}/validate",
    response_model=DefinitionDraftValidationResponse,
)
async def post_definition_draft_set_validate(
    draft_set_id: str,
    session: DBSession,
) -> DefinitionDraftValidationResponse:
    try:
        return await validate_definition_draft_set(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post(
    "/definition-draft-sets/{draft_set_id}/apply",
    response_model=DefinitionDraftApplyResponse,
)
async def post_definition_draft_set_apply(
    draft_set_id: str,
    request: DefinitionDraftApplyRequest,
    session: DBSession,
) -> DefinitionDraftApplyResponse:
    try:
        return await publish_definition_draft_set(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post(
    "/definition-draft-sets/{draft_set_id}/preview-task-compose",
    response_model=DefinitionDraftTaskComposePreviewResponse,
)
async def post_definition_draft_set_preview_task_compose(
    draft_set_id: str,
    request: DefinitionDraftTaskComposePreviewRequest,
    session: DBSession,
) -> DefinitionDraftTaskComposePreviewResponse:
    try:
        return await preview_definition_draft_set_task_compose(
            session,
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
            request=request,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
