from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.core.enums import DefinitionVersionStatus
from app.core.errors import InvalidDefinitionError, NotFoundError
from app.db.models.registry import (
    PolicyDefinition,
    PolicyVersion,
    RoleDefinition,
    RoleVersion,
    SkillRegistry,
    WorkflowDefinition,
    WorkflowVersion,
)
from app.runtime.state import utcnow_naive
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
from app.services.registry_service import (
    bootstrap_registry,
    upsert_policy_seed,
    upsert_role_seed,
    upsert_workflow_seed,
)

router = APIRouter(prefix="/registry", tags=["registry"])
internal_router = APIRouter(prefix="/registry", tags=["registry"])

DefinitionInstance = RoleDefinition | PolicyDefinition | WorkflowDefinition
VersionInstance = RoleVersion | PolicyVersion | WorkflowVersion


async def _list_definition_summaries(
    session: AsyncSession,
    definition_model: type[RoleDefinition | PolicyDefinition | WorkflowDefinition],
) -> list[RegistryDefinitionSummaryRead]:
    definitions = cast(
        list[DefinitionInstance],
        (
            await session.scalars(
                select(definition_model)
                .options(selectinload(definition_model.versions))
                .order_by(definition_model.key.asc())
            )
        ).all(),
    )
    summaries: list[RegistryDefinitionSummaryRead] = []
    for definition in definitions:
        versions = cast(
            list[VersionInstance],
            sorted(definition.versions, key=lambda version: version.version, reverse=True),
        )
        latest = versions[0] if versions else None
        published = next(
            (
                version
                for version in versions
                if version.status == DefinitionVersionStatus.PUBLISHED
            ),
            None,
        )
        draft = next(
            (version for version in versions if version.status == DefinitionVersionStatus.DRAFT),
            None,
        )
        summaries.append(
            RegistryDefinitionSummaryRead(
                key=definition.key,
                description=definition.description,
                latest_version=latest.version if latest is not None else None,
                latest_status=latest.status if latest is not None else None,
                published_version=published.version if published is not None else None,
                draft_version=draft.version if draft is not None else None,
                updated_at=(latest.updated_at if latest is not None else definition.updated_at),
            )
        )
    return summaries


async def _list_definition_versions(
    session: AsyncSession,
    definition_model: type[RoleDefinition | PolicyDefinition | WorkflowDefinition],
    version_model: type[RoleVersion | PolicyVersion | WorkflowVersion],
    key: str,
) -> list[RegistryDefinitionVersionDetailRead]:
    versions = cast(
        list[VersionInstance],
        (
            await session.scalars(
                select(version_model)
                .join(definition_model)
                .where(definition_model.key == key)
                .order_by(version_model.version.desc())
            )
        ).all(),
    )
    if not versions:
        raise NotFoundError(f"No definition versions found for '{key}'")
    return [
        RegistryDefinitionVersionDetailRead(
            id=version.id,
            key=key,
            version=version.version,
            status=version.status,
            description=version.description,
            content=version.content,
            published_at=version.published_at,
            created_at=version.created_at,
            updated_at=version.updated_at,
        )
        for version in versions
    ]


async def _publish_definition_version(
    session: AsyncSession,
    definition_model: type[RoleDefinition | PolicyDefinition | WorkflowDefinition],
    version_model: type[RoleVersion | PolicyVersion | WorkflowVersion],
    key: str,
    version_number: int,
) -> RegistryDefinitionVersionDetailRead:
    versions = cast(
        list[VersionInstance],
        (
            await session.scalars(
                select(version_model)
                .options(selectinload(version_model.definition))
                .join(definition_model)
                .where(definition_model.key == key)
                .order_by(version_model.version.desc())
            )
        ).all(),
    )
    if not versions:
        raise NotFoundError(f"No definition versions found for '{key}'")

    target = next((version for version in versions if version.version == version_number), None)
    if target is None:
        raise NotFoundError(f"No version {version_number} found for '{key}'")

    if isinstance(target, WorkflowVersion):
        await preview_workflow_seed(session, WorkflowDefinitionSeed.model_validate(target.content))

    now = utcnow_naive()
    for version in versions:
        if version.status == DefinitionVersionStatus.PUBLISHED and version.id != target.id:
            version.status = DefinitionVersionStatus.ARCHIVED
    target.status = DefinitionVersionStatus.PUBLISHED
    target.published_at = now
    await session.flush()
    await session.refresh(target)
    return RegistryDefinitionVersionDetailRead(
        id=target.id,
        key=key,
        version=target.version,
        status=target.status,
        description=target.description,
        content=target.content,
        published_at=target.published_at,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


async def _list_skills(session: AsyncSession) -> list[RegistrySkillSummaryRead]:
    skills = list(
        (
            await session.scalars(
                select(SkillRegistry)
                .options(selectinload(SkillRegistry.versions))
                .order_by(SkillRegistry.provider.asc(), SkillRegistry.key.asc())
            )
        ).all()
    )
    payload: list[RegistrySkillSummaryRead] = []
    for skill in skills:
        published = next(
            (
                version
                for version in sorted(
                    skill.versions,
                    key=lambda version: version.published_at or version.created_at,
                    reverse=True,
                )
                if version.status == DefinitionVersionStatus.PUBLISHED
            ),
            None,
        )
        payload.append(
            RegistrySkillSummaryRead(
                provider=skill.provider,
                key=skill.key,
                source_uri=skill.source_uri,
                description=skill.description,
                published_version=(published.version_label if published is not None else None),
            )
        )
    return payload


@router.get("/roles", response_model=list[RegistryDefinitionSummaryRead])
async def list_role_definitions(session: DbSession) -> list[RegistryDefinitionSummaryRead]:
    return await _list_definition_summaries(session, RoleDefinition)


@router.get("/policies", response_model=list[RegistryDefinitionSummaryRead])
async def list_policy_definitions(session: DbSession) -> list[RegistryDefinitionSummaryRead]:
    return await _list_definition_summaries(session, PolicyDefinition)


@router.get("/workflows", response_model=list[RegistryDefinitionSummaryRead])
async def list_workflow_definitions(session: DbSession) -> list[RegistryDefinitionSummaryRead]:
    return await _list_definition_summaries(session, WorkflowDefinition)


@router.get("/skills", response_model=list[RegistrySkillSummaryRead])
async def list_skill_registry(session: DbSession) -> list[RegistrySkillSummaryRead]:
    return await _list_skills(session)


@router.get(
    "/roles/{key}/versions",
    response_model=list[RegistryDefinitionVersionDetailRead],
)
async def list_role_versions(
    key: str,
    session: DbSession,
) -> list[RegistryDefinitionVersionDetailRead]:
    try:
        return await _list_definition_versions(session, RoleDefinition, RoleVersion, key)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/policies/{key}/versions", response_model=list[RegistryDefinitionVersionDetailRead])
async def list_policy_versions(
    key: str,
    session: DbSession,
) -> list[RegistryDefinitionVersionDetailRead]:
    try:
        return await _list_definition_versions(session, PolicyDefinition, PolicyVersion, key)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/workflows/{key}/versions", response_model=list[RegistryDefinitionVersionDetailRead])
async def list_workflow_versions(
    key: str,
    session: DbSession,
) -> list[RegistryDefinitionVersionDetailRead]:
    try:
        return await _list_definition_versions(session, WorkflowDefinition, WorkflowVersion, key)
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
) -> RegistryDefinitionVersionDetailRead:
    if seed.id != key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Role key must match the path key",
        )
    version = await upsert_role_seed(session, seed, publish=False)
    await session.commit()
    return RegistryDefinitionVersionDetailRead(
        id=version.id,
        key=key,
        version=version.version,
        status=version.status,
        description=version.description,
        content=version.content,
        published_at=version.published_at,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.put(
    "/policies/{key}/draft",
    response_model=RegistryDefinitionVersionDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def put_policy_draft(
    key: str,
    seed: PolicyDefinitionSeed,
    session: DbSession,
) -> RegistryDefinitionVersionDetailRead:
    if seed.id != key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Policy key must match the path key",
        )
    version = await upsert_policy_seed(session, seed, publish=False)
    await session.commit()
    return RegistryDefinitionVersionDetailRead(
        id=version.id,
        key=key,
        version=version.version,
        status=version.status,
        description=version.description,
        content=version.content,
        published_at=version.published_at,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


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
) -> RegistryDefinitionVersionDetailRead:
    if seed.id != key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Workflow key must match the path key",
        )
    try:
        await preview_workflow_seed(session, seed)
    except (InvalidDefinitionError, NotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    version = await upsert_workflow_seed(session, seed, publish=False)
    await session.commit()
    return RegistryDefinitionVersionDetailRead(
        id=version.id,
        key=key,
        version=version.version,
        status=version.status,
        description=version.description,
        content=version.content,
        published_at=version.published_at,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.post(
    "/roles/{key}/versions/{version_number}/publish",
    response_model=RegistryDefinitionVersionDetailRead,
)
async def publish_role_version(
    key: str,
    version_number: int,
    session: DbSession,
) -> RegistryDefinitionVersionDetailRead:
    try:
        published = await _publish_definition_version(
            session,
            RoleDefinition,
            RoleVersion,
            key,
            version_number,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return published


@router.post(
    "/policies/{key}/versions/{version_number}/publish",
    response_model=RegistryDefinitionVersionDetailRead,
)
async def publish_policy_version(
    key: str,
    version_number: int,
    session: DbSession,
) -> RegistryDefinitionVersionDetailRead:
    try:
        published = await _publish_definition_version(
            session,
            PolicyDefinition,
            PolicyVersion,
            key,
            version_number,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return published


@router.post(
    "/workflows/{key}/versions/{version_number}/publish",
    response_model=RegistryDefinitionVersionDetailRead,
)
async def publish_workflow_version(
    key: str,
    version_number: int,
    session: DbSession,
) -> RegistryDefinitionVersionDetailRead:
    try:
        published = await _publish_definition_version(
            session,
            WorkflowDefinition,
            WorkflowVersion,
            key,
            version_number,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidDefinitionError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    await session.commit()
    return published


@internal_router.get("/snapshot", response_model=RegistrySnapshotRead, include_in_schema=False)
async def registry_snapshot(session: DbSession) -> RegistrySnapshotRead:
    return RegistrySnapshotRead(
        roles=await _list_definition_summaries(session, RoleDefinition),
        policies=await _list_definition_summaries(session, PolicyDefinition),
        workflows=await _list_definition_summaries(session, WorkflowDefinition),
        skills=await _list_skills(session),
    )


@internal_router.post("/bootstrap", include_in_schema=False)
async def bootstrap(
    session: DbSession,
    publish: bool = Query(default=True),
) -> dict[str, int]:
    result = await bootstrap_registry(session, publish=publish)
    await session.commit()
    return result
