from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.api.presenters.registry import (
    present_definition_summaries,
    present_definition_version,
    present_definition_versions,
    present_skill_registry,
)
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.db.models.registry import (
    PolicyDefinition,
    PolicyVersion,
    RoleDefinition,
    RoleVersion,
    WorkflowDefinition,
    WorkflowVersion,
)
from app.registry.publish import (
    publish_policy_version as publish_policy_definition_version,
)
from app.registry.publish import (
    publish_role_version as publish_role_definition_version,
)
from app.registry.publish import (
    publish_workflow_version as publish_workflow_definition_version,
)
from app.registry.publish import (
    put_policy_draft_version,
    put_role_draft_version,
    put_workflow_draft_version,
)
from app.registry.query import (
    list_definition_records,
    list_definition_versions,
    list_skill_records,
)
from app.schemas.registry import (
    PolicyDefinitionSeed,
    RegistryDefinitionSummaryRead,
    RegistryDefinitionVersionDetailRead,
    RegistrySkillSummaryRead,
    RegistrySnapshotRead,
    RoleDefinitionSeed,
    WorkflowDefinitionSeed,
    WorkflowValidationRead,
)
from app.services.compiler_service import preview_workflow_seed
from app.services.registry_service import bootstrap_registry

router = APIRouter(prefix="/registry", tags=["registry"])
internal_router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/roles", response_model=list[RegistryDefinitionSummaryRead])
async def list_role_definitions(session: DbSession) -> list[RegistryDefinitionSummaryRead]:
    return present_definition_summaries(await list_definition_records(session, RoleDefinition))


@router.get("/policies", response_model=list[RegistryDefinitionSummaryRead])
async def list_policy_definitions(session: DbSession) -> list[RegistryDefinitionSummaryRead]:
    return present_definition_summaries(await list_definition_records(session, PolicyDefinition))


@router.get("/workflows", response_model=list[RegistryDefinitionSummaryRead])
async def list_workflow_definitions(session: DbSession) -> list[RegistryDefinitionSummaryRead]:
    return present_definition_summaries(await list_definition_records(session, WorkflowDefinition))


@router.get("/skills", response_model=list[RegistrySkillSummaryRead])
async def list_skill_registry(session: DbSession) -> list[RegistrySkillSummaryRead]:
    return present_skill_registry(await list_skill_records(session))


@router.get(
    "/roles/{key}/versions",
    response_model=list[RegistryDefinitionVersionDetailRead],
)
async def list_role_versions(
    key: str,
    session: DbSession,
) -> list[RegistryDefinitionVersionDetailRead]:
    try:
        versions = await list_definition_versions(session, RoleDefinition, RoleVersion, key)
        return present_definition_versions(key=key, versions=versions)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/policies/{key}/versions", response_model=list[RegistryDefinitionVersionDetailRead])
async def list_policy_versions(
    key: str,
    session: DbSession,
) -> list[RegistryDefinitionVersionDetailRead]:
    try:
        versions = await list_definition_versions(session, PolicyDefinition, PolicyVersion, key)
        return present_definition_versions(key=key, versions=versions)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/workflows/{key}/versions", response_model=list[RegistryDefinitionVersionDetailRead])
async def list_workflow_versions(
    key: str,
    session: DbSession,
) -> list[RegistryDefinitionVersionDetailRead]:
    try:
        versions = await list_definition_versions(session, WorkflowDefinition, WorkflowVersion, key)
        return present_definition_versions(key=key, versions=versions)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put(
    "/roles/{key}/draft",
    response_model=RegistryDefinitionVersionDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def put_role_draft(
    key: str,
    seed: RoleDefinitionSeed,
    session: DbSession,
    expected_draft_version: int | None = Query(default=None, ge=0),
) -> RegistryDefinitionVersionDetailRead:
    if seed.id != key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Role key must match the path key",
        )
    try:
        version = await put_role_draft_version(
            session,
            key=key,
            seed=seed,
            expected_draft_version=expected_draft_version,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return present_definition_version(key=key, version=version)


@router.put(
    "/policies/{key}/draft",
    response_model=RegistryDefinitionVersionDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def put_policy_draft(
    key: str,
    seed: PolicyDefinitionSeed,
    session: DbSession,
    expected_draft_version: int | None = Query(default=None, ge=0),
) -> RegistryDefinitionVersionDetailRead:
    if seed.id != key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Policy key must match the path key",
        )
    try:
        version = await put_policy_draft_version(
            session,
            key=key,
            seed=seed,
            expected_draft_version=expected_draft_version,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return present_definition_version(key=key, version=version)


@router.post("/workflows/validate", response_model=WorkflowValidationRead)
async def validate_workflow_definition(
    seed: WorkflowDefinitionSeed,
    session: DbSession,
) -> WorkflowValidationRead:
    try:
        normalized_plan = await preview_workflow_seed(session, seed)
    except (InvalidDefinitionError, NotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return WorkflowValidationRead(
        valid=True,
        normalized_plan=normalized_plan.model_dump(mode="json"),
    )


@router.put(
    "/workflows/{key}/draft",
    response_model=RegistryDefinitionVersionDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def put_workflow_draft(
    key: str,
    seed: WorkflowDefinitionSeed,
    session: DbSession,
    expected_draft_version: int | None = Query(default=None, ge=0),
) -> RegistryDefinitionVersionDetailRead:
    if seed.id != key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Workflow key must match the path key",
        )
    try:
        version = await put_workflow_draft_version(
            session,
            key=key,
            seed=seed,
            expected_draft_version=expected_draft_version,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (InvalidDefinitionError, NotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    await session.commit()
    return present_definition_version(key=key, version=version)


@router.post(
    "/roles/{key}/versions/{version_number}/publish",
    response_model=RegistryDefinitionVersionDetailRead,
)
async def publish_role_version(
    key: str,
    version_number: int,
    session: DbSession,
    expected_published_version: int | None = Query(default=None, ge=0),
) -> RegistryDefinitionVersionDetailRead:
    try:
        published = await publish_role_definition_version(
            session,
            key=key,
            version_number=version_number,
            expected_published_version=expected_published_version,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return present_definition_version(key=key, version=published)


@router.post(
    "/policies/{key}/versions/{version_number}/publish",
    response_model=RegistryDefinitionVersionDetailRead,
)
async def publish_policy_version(
    key: str,
    version_number: int,
    session: DbSession,
    expected_published_version: int | None = Query(default=None, ge=0),
) -> RegistryDefinitionVersionDetailRead:
    try:
        published = await publish_policy_definition_version(
            session,
            key=key,
            version_number=version_number,
            expected_published_version=expected_published_version,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return present_definition_version(key=key, version=published)


@router.post(
    "/workflows/{key}/versions/{version_number}/publish",
    response_model=RegistryDefinitionVersionDetailRead,
)
async def publish_workflow_version(
    key: str,
    version_number: int,
    session: DbSession,
    expected_published_version: int | None = Query(default=None, ge=0),
) -> RegistryDefinitionVersionDetailRead:
    try:
        published = await publish_workflow_definition_version(
            session,
            key=key,
            version_number=version_number,
            expected_published_version=expected_published_version,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidDefinitionError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    await session.commit()
    return present_definition_version(key=key, version=published)


@internal_router.get("/snapshot", response_model=RegistrySnapshotRead, include_in_schema=False)
async def registry_snapshot(session: DbSession) -> RegistrySnapshotRead:
    return RegistrySnapshotRead(
        roles=present_definition_summaries(await list_definition_records(session, RoleDefinition)),
        policies=present_definition_summaries(
            await list_definition_records(session, PolicyDefinition)
        ),
        workflows=present_definition_summaries(
            await list_definition_records(session, WorkflowDefinition)
        ),
        skills=present_skill_registry(await list_skill_records(session)),
    )


@internal_router.post("/bootstrap", include_in_schema=False)
async def bootstrap(
    session: DbSession,
    publish: bool = Query(default=True),
) -> dict[str, int]:
    result = await bootstrap_registry(session, publish=publish)
    await session.commit()
    return result
