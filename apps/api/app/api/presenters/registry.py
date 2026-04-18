from __future__ import annotations

from typing import cast

from app.core.enums import DefinitionVersionStatus
from app.db.models.registry import (
    PolicyDefinition,
    PolicyVersion,
    RoleDefinition,
    RoleVersion,
    SkillRegistry,
    SkillVersion,
    WorkflowDefinition,
    WorkflowVersion,
)
from app.schemas.registry import (
    RegistryDefinitionSummaryRead,
    RegistryDefinitionVersionDetailRead,
    RegistrySkillSummaryRead,
)

DefinitionInstance = RoleDefinition | PolicyDefinition | WorkflowDefinition
VersionInstance = RoleVersion | PolicyVersion | WorkflowVersion


def present_definition_summaries(
    definitions: list[RoleDefinition | PolicyDefinition | WorkflowDefinition],
) -> list[RegistryDefinitionSummaryRead]:
    summaries: list[RegistryDefinitionSummaryRead] = []
    for definition in cast(list[DefinitionInstance], definitions):
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


def present_definition_versions(
    *,
    key: str,
    versions: list[RoleVersion | PolicyVersion | WorkflowVersion],
) -> list[RegistryDefinitionVersionDetailRead]:
    return [present_definition_version(key=key, version=version) for version in versions]


def present_definition_version(
    *,
    key: str,
    version: RoleVersion | PolicyVersion | WorkflowVersion,
) -> RegistryDefinitionVersionDetailRead:
    return RegistryDefinitionVersionDetailRead(
        id=version.id,
        key=key,
        version=version.version,
        status=version.status,
        description=version.description,
        content=version.content,
        requested_by=version.requested_by,
        audit=version.audit,
        published_at=version.published_at,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def present_skill_registry(skills: list[SkillRegistry]) -> list[RegistrySkillSummaryRead]:
    payload: list[RegistrySkillSummaryRead] = []
    for skill in skills:
        published = next(
            (
                version
                for version in cast(
                    list[SkillVersion],
                    sorted(
                        skill.versions,
                        key=lambda version: version.published_at or version.created_at,
                        reverse=True,
                    ),
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
