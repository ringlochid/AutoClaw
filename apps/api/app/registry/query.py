from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import DefinitionVersionStatus
from app.core.errors import NotFoundError
from app.db.models.registry import (
    PolicyDefinition,
    PolicyVersion,
    RoleDefinition,
    RoleVersion,
    SkillRegistry,
    WorkflowDefinition,
    WorkflowVersion,
)

DefinitionInstance = RoleDefinition | PolicyDefinition | WorkflowDefinition
VersionInstance = RoleVersion | PolicyVersion | WorkflowVersion


async def list_definition_records(
    session: AsyncSession,
    definition_model: type[RoleDefinition | PolicyDefinition | WorkflowDefinition],
) -> list[RoleDefinition | PolicyDefinition | WorkflowDefinition]:
    return cast(
        list[DefinitionInstance],
        (
            await session.scalars(
                select(definition_model)
                .options(selectinload(definition_model.versions))
                .order_by(definition_model.key.asc())
            )
        ).all(),
    )


async def list_definition_versions(
    session: AsyncSession,
    definition_model: type[RoleDefinition | PolicyDefinition | WorkflowDefinition],
    version_model: type[RoleVersion | PolicyVersion | WorkflowVersion],
    key: str,
) -> list[RoleVersion | PolicyVersion | WorkflowVersion]:
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
    return versions


async def get_current_definition_version(
    session: AsyncSession,
    definition_model: type[RoleDefinition | PolicyDefinition | WorkflowDefinition],
    version_model: type[RoleVersion | PolicyVersion | WorkflowVersion],
    key: str,
    *,
    status_filter: DefinitionVersionStatus,
) -> RoleVersion | PolicyVersion | WorkflowVersion | None:
    return cast(
        VersionInstance | None,
        await session.scalar(
            select(version_model)
            .join(definition_model)
            .where(
                definition_model.key == key,
                version_model.status == status_filter,
            )
            .order_by(version_model.version.desc())
        ),
    )


async def list_skill_records(session: AsyncSession) -> list[SkillRegistry]:
    return list(
        (
            await session.scalars(
                select(SkillRegistry)
                .options(selectinload(SkillRegistry.versions))
                .order_by(SkillRegistry.provider.asc(), SkillRegistry.key.asc())
            )
        ).all()
    )
