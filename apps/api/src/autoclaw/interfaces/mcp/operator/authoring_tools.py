from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

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
from autoclaw.definitions.authoring.contracts import DefinitionDraftSetCreateItem
from autoclaw.definitions.contracts import DefinitionKind
from autoclaw.runtime.post_commit.operations import read_session_operation

from ..tool_teaching import (
    INSPECT_IF_UNSURE_NOTE,
    LOCAL_FILE_PATH_NOTE,
    RUNTIME_STATE_WARNING,
    mutating_tool_teaching,
    read_only_tool_teaching,
)

LIST_DEFINITION_DRAFT_SETS_TEACHING = read_only_tool_teaching(
    name="list_definition_draft_sets",
    summary="List backend-owned definition draft sets.",
    details=(
        "Use get_definition_draft_set next when you need saved YAML bodies, "
        "normalized content, or preview state.",
    ),
)
GET_DEFINITION_DRAFT_SET_TEACHING = read_only_tool_teaching(
    name="get_definition_draft_set",
    summary="Inspect one backend-owned definition draft set in detail.",
    details=(
        "This is the canonical authoring bootstrap read for saved draft bodies "
        "and normalized content.",
    ),
)
CREATE_DEFINITION_DRAFT_SET_TEACHING = mutating_tool_teaching(
    name="create_definition_draft_set",
    summary=(
        "Create one backend-owned definition draft set, optionally materializing "
        "current definitions."
    ),
    details=(RUNTIME_STATE_WARNING, INSPECT_IF_UNSURE_NOTE),
)
DELETE_DEFINITION_DRAFT_SET_TEACHING = mutating_tool_teaching(
    name="delete_definition_draft_set",
    summary="Delete one backend-owned definition draft set.",
    details=(RUNTIME_STATE_WARNING,),
)
MATERIALIZE_DEFINITION_DRAFT_SET_TEACHING = mutating_tool_teaching(
    name="materialize_definition_draft_set",
    summary="Materialize current stored definitions into an existing draft set.",
    details=(RUNTIME_STATE_WARNING, INSPECT_IF_UNSURE_NOTE),
)
WRITE_DEFINITION_DRAFT_FILE_TEACHING = mutating_tool_teaching(
    name="write_definition_draft_file",
    summary="Save YAML draft edits into one backend-owned definition draft file.",
    details=(RUNTIME_STATE_WARNING,),
)
RESET_DEFINITION_DRAFT_FILE_TEACHING = mutating_tool_teaching(
    name="reset_definition_draft_file",
    summary="Reset one draft file back to its captured baseline inside the draft set.",
    details=(RUNTIME_STATE_WARNING,),
)
REMATERIALIZE_DEFINITION_DRAFT_FILE_TEACHING = mutating_tool_teaching(
    name="rematerialize_current_definition_draft_file",
    summary="Replace one draft file with the current stored revision and refresh its baseline.",
    details=(RUNTIME_STATE_WARNING, INSPECT_IF_UNSURE_NOTE),
)
VALIDATE_DEFINITION_DRAFT_SET_TEACHING = read_only_tool_teaching(
    name="validate_definition_draft_set",
    summary=(
        "Validate one draft set against the same controller-owned legality rules "
        "used by publish and task start."
    ),
    details=("Validation reads current saved draft state; it does not publish definitions.",),
)
APPLY_DEFINITION_DRAFT_SET_TEACHING = mutating_tool_teaching(
    name="apply_definition_draft_set",
    summary="Publish one validated draft set into controller-owned definition truth.",
    details=(RUNTIME_STATE_WARNING, INSPECT_IF_UNSURE_NOTE),
)
PREVIEW_DEFINITION_DRAFT_SET_TASK_COMPOSE_TEACHING = mutating_tool_teaching(
    name="preview_definition_draft_set_task_compose",
    summary="Save and validate preview task-compose YAML against one draft set.",
    details=(RUNTIME_STATE_WARNING, LOCAL_FILE_PATH_NOTE),
)


def register_authoring_tools(server: FastMCP) -> None:
    register_draft_set_read_tools(server)
    register_draft_set_mutation_tools(server)
    register_draft_set_validation_tools(server)


def register_draft_set_read_tools(server: FastMCP) -> None:
    @server.tool(
        name="list_definition_draft_sets",
        title=LIST_DEFINITION_DRAFT_SETS_TEACHING.title,
        description=LIST_DEFINITION_DRAFT_SETS_TEACHING.description,
        annotations=LIST_DEFINITION_DRAFT_SETS_TEACHING.annotations,
    )
    async def list_definition_draft_sets_tool(
        cursor: str | None = None,
        limit: int = 50,
    ) -> DefinitionDraftSetListResponse:
        query = DefinitionDraftSetListQuery(cursor=cursor, limit=limit)
        return await read_session_operation(
            lambda session: list_definition_draft_sets(
                session,
                data_dir=get_settings().data_dir,
                query=query,
            )
        )

    @server.tool(
        name="create_definition_draft_set",
        title=CREATE_DEFINITION_DRAFT_SET_TEACHING.title,
        description=CREATE_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=CREATE_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def create_definition_draft_set_tool(
        title: str | None = None,
        materialize: list[dict[str, str]] | None = None,
        preview_task_compose: str | None = None,
    ) -> DefinitionDraftSetDetailResponse:
        request = DefinitionDraftSetCreateRequest(
            title=title,
            materialize=_draft_set_items(materialize),
            preview_task_compose=preview_task_compose,
        )
        return await read_session_operation(
            lambda session: create_definition_draft_set(
                session,
                data_dir=get_settings().data_dir,
                request=request,
            )
        )

    @server.tool(
        name="get_definition_draft_set",
        title=GET_DEFINITION_DRAFT_SET_TEACHING.title,
        description=GET_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=GET_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def get_definition_draft_set_tool(
        draft_set_id: str,
    ) -> DefinitionDraftSetDetailResponse:
        return await read_session_operation(
            lambda session: read_definition_draft_set(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
            )
        )


def register_draft_set_mutation_tools(server: FastMCP) -> None:
    register_draft_set_lifecycle_tools(server)
    register_draft_set_file_tools(server)


def register_draft_set_lifecycle_tools(server: FastMCP) -> None:
    @server.tool(
        name="delete_definition_draft_set",
        title=DELETE_DEFINITION_DRAFT_SET_TEACHING.title,
        description=DELETE_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=DELETE_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def delete_definition_draft_set_tool(draft_set_id: str) -> dict[str, str]:
        delete_definition_draft_set_by_id(
            data_dir=get_settings().data_dir,
            draft_set_id=draft_set_id,
        )
        return {"draft_set_id": draft_set_id, "status": "deleted"}

    @server.tool(
        name="materialize_definition_draft_set",
        title=MATERIALIZE_DEFINITION_DRAFT_SET_TEACHING.title,
        description=MATERIALIZE_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=MATERIALIZE_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def materialize_definition_draft_set_tool(
        draft_set_id: str,
        definitions: list[dict[str, str]],
    ) -> DefinitionDraftSetDetailResponse:
        request = DefinitionDraftMaterializeRequest(definitions=_draft_set_items(definitions))
        return await read_session_operation(
            lambda session: materialize_definition_draft_set(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
                request=request,
            )
        )


def register_draft_set_file_tools(server: FastMCP) -> None:
    @server.tool(
        name="write_definition_draft_file",
        title=WRITE_DEFINITION_DRAFT_FILE_TEACHING.title,
        description=WRITE_DEFINITION_DRAFT_FILE_TEACHING.description,
        annotations=WRITE_DEFINITION_DRAFT_FILE_TEACHING.annotations,
    )
    async def write_definition_draft_file_tool(
        draft_set_id: str,
        kind: DefinitionKind,
        key: str,
        body: str,
        body_format: Literal["yaml"] = "yaml",
    ) -> DefinitionDraftSetDetailResponse:
        request = DefinitionDraftFileWriteRequest(body=body, body_format=body_format)
        return await read_session_operation(
            lambda session: write_definition_draft_file(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
                kind=kind,
                key=key,
                request=request,
            )
        )

    @server.tool(
        name="reset_definition_draft_file",
        title=RESET_DEFINITION_DRAFT_FILE_TEACHING.title,
        description=RESET_DEFINITION_DRAFT_FILE_TEACHING.description,
        annotations=RESET_DEFINITION_DRAFT_FILE_TEACHING.annotations,
    )
    async def reset_definition_draft_file_tool(
        draft_set_id: str,
        kind: DefinitionKind,
        key: str,
    ) -> DefinitionDraftSetDetailResponse:
        request = DefinitionDraftFileResetRequest(discard_local_changes=True)
        return await read_session_operation(
            lambda session: reset_definition_draft_file(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
                kind=kind,
                key=key,
                request=request,
            )
        )

    @server.tool(
        name="rematerialize_current_definition_draft_file",
        title=REMATERIALIZE_DEFINITION_DRAFT_FILE_TEACHING.title,
        description=REMATERIALIZE_DEFINITION_DRAFT_FILE_TEACHING.description,
        annotations=REMATERIALIZE_DEFINITION_DRAFT_FILE_TEACHING.annotations,
    )
    async def rematerialize_current_definition_draft_file_tool(
        draft_set_id: str,
        kind: DefinitionKind,
        key: str,
    ) -> DefinitionDraftSetDetailResponse:
        request = DefinitionDraftFileRematerializeCurrentRequest(discard_local_changes=True)
        return await read_session_operation(
            lambda session: rematerialize_current_definition_draft_file(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
                kind=kind,
                key=key,
                request=request,
            )
        )


def register_draft_set_validation_tools(server: FastMCP) -> None:
    @server.tool(
        name="validate_definition_draft_set",
        title=VALIDATE_DEFINITION_DRAFT_SET_TEACHING.title,
        description=VALIDATE_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=VALIDATE_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def validate_definition_draft_set_tool(
        draft_set_id: str,
    ) -> DefinitionDraftValidationResponse:
        return await read_session_operation(
            lambda session: validate_definition_draft_set(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
            )
        )

    @server.tool(
        name="apply_definition_draft_set",
        title=APPLY_DEFINITION_DRAFT_SET_TEACHING.title,
        description=APPLY_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=APPLY_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def apply_definition_draft_set_tool(
        draft_set_id: str,
        should_start_task_after_apply: bool = False,
    ) -> DefinitionDraftApplyResponse:
        request = DefinitionDraftApplyRequest(
            should_start_task_after_apply=should_start_task_after_apply
        )
        return await read_session_operation(
            lambda session: publish_definition_draft_set(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
                request=request,
            )
        )

    @server.tool(
        name="preview_definition_draft_set_task_compose",
        title=PREVIEW_DEFINITION_DRAFT_SET_TASK_COMPOSE_TEACHING.title,
        description=PREVIEW_DEFINITION_DRAFT_SET_TASK_COMPOSE_TEACHING.description,
        annotations=PREVIEW_DEFINITION_DRAFT_SET_TASK_COMPOSE_TEACHING.annotations,
    )
    async def preview_definition_draft_set_task_compose_tool(
        draft_set_id: str,
        body: str,
        body_format: Literal["yaml"] = "yaml",
    ) -> DefinitionDraftTaskComposePreviewResponse:
        request = DefinitionDraftTaskComposePreviewRequest(body=body, body_format=body_format)
        return await read_session_operation(
            lambda session: preview_definition_draft_set_task_compose(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
                request=request,
            )
        )


def _draft_set_items(
    items: list[dict[str, str]] | None,
) -> tuple[DefinitionDraftSetCreateItem, ...]:
    return tuple(DefinitionDraftSetCreateItem.model_validate(item) for item in (items or ()))
