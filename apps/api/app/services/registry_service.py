from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import DefinitionVersionStatus, SkillProvider
from app.core.errors import NotFoundError
from app.core.ids import next_version_number
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
    PolicyDefinitionSeed,
    RoleDefinitionSeed,
    SkillReferenceSeed,
    WorkflowDefinitionSeed,
)

DEFINITIONS_ROOT = Path(__file__).resolve().parents[4] / "definitions"
EXTERNAL_CURRENT_VERSION = "external-current"

DefinitionT = TypeVar("DefinitionT", RoleDefinition, PolicyDefinition, WorkflowDefinition)
VersionT = TypeVar("VersionT", RoleVersion, PolicyVersion, WorkflowVersion)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in definition file: {path}")
    return data


def iter_definition_files(kind: str) -> list[Path]:
    directory = DEFINITIONS_ROOT / kind
    return sorted(path for path in directory.glob("*.yaml") if path.is_file())


def load_role_seed(path: Path) -> RoleDefinitionSeed:
    return RoleDefinitionSeed.model_validate(_load_yaml_file(path))


def load_policy_seed(path: Path) -> PolicyDefinitionSeed:
    return PolicyDefinitionSeed.model_validate(_load_yaml_file(path))


def load_workflow_seed(path: Path) -> WorkflowDefinitionSeed:
    return WorkflowDefinitionSeed.model_validate(_load_yaml_file(path))


async def _get_latest_version(
    session: AsyncSession,
    version_model: type[VersionT],
    foreign_key_name: str,
    definition_id: object,
) -> VersionT | None:
    return cast(
        VersionT | None,
        await session.scalar(
            select(version_model)
            .where(getattr(version_model, foreign_key_name) == definition_id)
            .order_by(version_model.version.desc())
            .limit(1)
        ),
    )


async def _archive_published_versions(
    session: AsyncSession,
    version_model: type[VersionT],
    foreign_key_name: str,
    definition_id: object,
) -> None:
    published_versions = await session.scalars(
        select(version_model).where(
            getattr(version_model, foreign_key_name) == definition_id,
            version_model.status == DefinitionVersionStatus.PUBLISHED,
        )
    )
    for version in published_versions:
        version.status = DefinitionVersionStatus.ARCHIVED


async def _upsert_definition(
    session: AsyncSession,
    definition_model: type[DefinitionT],
    *,
    key: str,
    description: str | None,
) -> DefinitionT:
    definition = cast(
        DefinitionT | None,
        await session.scalar(select(definition_model).where(definition_model.key == key)),
    )
    if definition is None:
        definition = definition_model(key=key, description=description)
        session.add(definition)
        await session.flush()
        return definition

    definition.description = description
    await session.flush()
    return definition


async def _upsert_version(
    session: AsyncSession,
    *,
    definition: DefinitionT,
    version_model: type[VersionT],
    foreign_key_name: str,
    description: str,
    content: dict[str, Any],
    publish: bool,
) -> VersionT:
    latest_version = await _get_latest_version(
        session,
        version_model=version_model,
        foreign_key_name=foreign_key_name,
        definition_id=definition.id,
    )
    now = _utcnow_naive()

    if latest_version is not None and latest_version.content == content:
        if publish and latest_version.status != DefinitionVersionStatus.PUBLISHED:
            await _archive_published_versions(
                session,
                version_model=version_model,
                foreign_key_name=foreign_key_name,
                definition_id=definition.id,
            )
            latest_version.status = DefinitionVersionStatus.PUBLISHED
            latest_version.published_at = now
        return latest_version

    if publish:
        await _archive_published_versions(
            session,
            version_model=version_model,
            foreign_key_name=foreign_key_name,
            definition_id=definition.id,
        )

    version = version_model(
        **{foreign_key_name: definition.id},
        version=next_version_number(latest_version.version if latest_version else None),
        status=(DefinitionVersionStatus.PUBLISHED if publish else DefinitionVersionStatus.DRAFT),
        description=description,
        content=content,
        published_at=now if publish else None,
    )
    session.add(version)
    await session.flush()
    return version


async def upsert_role_seed(
    session: AsyncSession,
    seed: RoleDefinitionSeed,
    *,
    publish: bool = True,
) -> RoleVersion:
    definition = await _upsert_definition(
        session,
        RoleDefinition,
        key=seed.id,
        description=seed.description,
    )
    return cast(
        RoleVersion,
        await _upsert_version(
            session,
            definition=definition,
            version_model=RoleVersion,
            foreign_key_name="role_definition_id",
            description=seed.description,
            content=seed.model_dump(mode="json", by_alias=True),
            publish=publish,
        ),
    )


async def upsert_policy_seed(
    session: AsyncSession,
    seed: PolicyDefinitionSeed,
    *,
    publish: bool = True,
) -> PolicyVersion:
    definition = await _upsert_definition(
        session,
        PolicyDefinition,
        key=seed.id,
        description=seed.description,
    )
    return cast(
        PolicyVersion,
        await _upsert_version(
            session,
            definition=definition,
            version_model=PolicyVersion,
            foreign_key_name="policy_definition_id",
            description=seed.description,
            content=seed.model_dump(mode="json", by_alias=True),
            publish=publish,
        ),
    )


async def upsert_workflow_seed(
    session: AsyncSession,
    seed: WorkflowDefinitionSeed,
    *,
    publish: bool = True,
) -> WorkflowVersion:
    definition = await _upsert_definition(
        session,
        WorkflowDefinition,
        key=seed.id,
        description=seed.description,
    )
    return cast(
        WorkflowVersion,
        await _upsert_version(
            session,
            definition=definition,
            version_model=WorkflowVersion,
            foreign_key_name="workflow_definition_id",
            description=seed.description,
            content=seed.model_dump(mode="json", by_alias=True),
            publish=publish,
        ),
    )


async def upsert_skill_reference(
    session: AsyncSession,
    skill_ref: SkillReferenceSeed,
    *,
    publish: bool = True,
) -> SkillVersion:
    skill = cast(
        SkillRegistry | None,
        await session.scalar(
            select(SkillRegistry).where(
                SkillRegistry.key == skill_ref.key,
                SkillRegistry.provider == skill_ref.provider,
            )
        ),
    )
    if skill is None:
        skill = SkillRegistry(
            key=skill_ref.key,
            provider=skill_ref.provider,
            source_uri=skill_ref.source_uri,
            description=f"External skill reference for {skill_ref.provider.value}:{skill_ref.key}",
        )
        session.add(skill)
        await session.flush()
    else:
        skill.source_uri = skill_ref.source_uri or skill.source_uri

    version_label = skill_ref.version or EXTERNAL_CURRENT_VERSION
    manifest = skill_ref.model_dump(mode="json")
    version = cast(
        SkillVersion | None,
        await session.scalar(
            select(SkillVersion).where(
                SkillVersion.skill_registry_id == skill.id,
                SkillVersion.version_label == version_label,
            )
        ),
    )
    now = _utcnow_naive()
    if version is not None:
        if publish and version.status != DefinitionVersionStatus.PUBLISHED:
            version.status = DefinitionVersionStatus.PUBLISHED
            version.published_at = now
        version.manifest = manifest
        version.source_ref = skill_ref.source_uri or version.source_ref
        await session.flush()
        return version

    version = SkillVersion(
        skill_registry_id=skill.id,
        version_label=version_label,
        status=(DefinitionVersionStatus.PUBLISHED if publish else DefinitionVersionStatus.DRAFT),
        source_ref=skill_ref.source_uri or f"{skill_ref.provider.value}:{skill_ref.key}",
        manifest=manifest,
        published_at=now if publish else None,
    )
    session.add(version)
    await session.flush()
    return version


async def bootstrap_registry(
    session: AsyncSession,
    *,
    publish: bool = True,
) -> dict[str, int]:
    role_paths = iter_definition_files("roles")
    policy_paths = iter_definition_files("policies")
    workflow_paths = iter_definition_files("workflows")

    workflow_seeds = [load_workflow_seed(path) for path in workflow_paths]
    skill_refs = _collect_skill_refs(workflow_seeds)

    for path in role_paths:
        await upsert_role_seed(session, load_role_seed(path), publish=publish)

    for path in policy_paths:
        await upsert_policy_seed(session, load_policy_seed(path), publish=publish)

    for skill_ref in skill_refs:
        await upsert_skill_reference(session, skill_ref, publish=publish)

    for workflow_seed in workflow_seeds:
        await upsert_workflow_seed(session, workflow_seed, publish=publish)

    await session.flush()
    return {
        "roles": len(role_paths),
        "policies": len(policy_paths),
        "workflows": len(workflow_paths),
        "skills": len(skill_refs),
    }


def _collect_skill_refs(
    workflow_seeds: Sequence[WorkflowDefinitionSeed],
) -> list[SkillReferenceSeed]:
    unique_refs: dict[tuple[str, str, str | None], SkillReferenceSeed] = {}
    for workflow_seed in workflow_seeds:
        for skill_ref in workflow_seed.skill_refs:
            unique_refs[(skill_ref.provider.value, skill_ref.key, skill_ref.version)] = skill_ref
    return list(unique_refs.values())


async def get_published_role_version(session: AsyncSession, key: str) -> RoleVersion:
    version = cast(
        RoleVersion | None,
        await session.scalar(
            select(RoleVersion)
            .join(RoleDefinition)
            .where(
                RoleDefinition.key == key,
                RoleVersion.status == DefinitionVersionStatus.PUBLISHED,
            )
            .order_by(RoleVersion.version.desc())
            .limit(1)
        ),
    )
    if version is None:
        raise NotFoundError(f"No published role version found for '{key}'")
    return version


async def get_published_policy_version(session: AsyncSession, key: str) -> PolicyVersion:
    version = cast(
        PolicyVersion | None,
        await session.scalar(
            select(PolicyVersion)
            .join(PolicyDefinition)
            .where(
                PolicyDefinition.key == key,
                PolicyVersion.status == DefinitionVersionStatus.PUBLISHED,
            )
            .order_by(PolicyVersion.version.desc())
            .limit(1)
        ),
    )
    if version is None:
        raise NotFoundError(f"No published policy version found for '{key}'")
    return version


async def get_published_workflow_version(session: AsyncSession, key: str) -> WorkflowVersion:
    version = cast(
        WorkflowVersion | None,
        await session.scalar(
            select(WorkflowVersion)
            .options(selectinload(WorkflowVersion.definition))
            .join(WorkflowDefinition)
            .where(
                WorkflowDefinition.key == key,
                WorkflowVersion.status == DefinitionVersionStatus.PUBLISHED,
            )
            .order_by(WorkflowVersion.version.desc())
            .limit(1)
        ),
    )
    if version is None:
        raise NotFoundError(f"No published workflow version found for '{key}'")
    return version


async def get_published_skill_version(
    session: AsyncSession,
    *,
    provider: SkillProvider,
    key: str,
    version_label: str | None = None,
) -> SkillVersion:
    stmt = (
        select(SkillVersion)
        .join(SkillRegistry)
        .where(
            SkillRegistry.key == key,
            SkillRegistry.provider == provider,
            SkillVersion.status == DefinitionVersionStatus.PUBLISHED,
        )
        .order_by(SkillVersion.published_at.desc().nullslast(), SkillVersion.created_at.desc())
    )
    if version_label is not None:
        stmt = stmt.where(SkillVersion.version_label == version_label)

    version = cast(SkillVersion | None, await session.scalar(stmt.limit(1)))
    if version is None:
        raise NotFoundError(f"No published skill version found for '{provider.value}:{key}'")
    return version
