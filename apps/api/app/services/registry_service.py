from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import load_settings
from app.core.enums import DefinitionVersionStatus, SkillProvider
from app.core.errors import InvalidDefinitionError, NotFoundError
from app.core.ids import next_version_number
from app.db.models.registry import (
    PolicyDefinition,
    PolicyVersion,
    RoleDefinition,
    RoleVersion,
    RoleVersionSkillBinding,
    SkillRegistry,
    SkillVersion,
    WorkflowDefinition,
    WorkflowNodeSkillBinding,
    WorkflowVersion,
    WorkflowVersionSkillBinding,
)
from app.compiler.nesting import flatten_workflow_nodes
from app.schemas.registry import (
    PolicyDefinitionSeed,
    RoleDefinitionSeed,
    SkillDefinitionSeed,
    SkillReferenceSeed,
    WorkflowDefinitionSeed,
)

DEFINITIONS_ROOT = Path(__file__).resolve().parents[4] / "definitions"
PACKAGED_DEFINITIONS_PACKAGE = "app.resources"
DEFINITIONS_ROOT_ENV = "AUTOCLAW_DEFINITIONS_ROOT"
EXTERNAL_CURRENT_VERSION = "external-current"

DefinitionT = TypeVar("DefinitionT", RoleDefinition, PolicyDefinition, WorkflowDefinition)
VersionT = TypeVar("VersionT", RoleVersion, PolicyVersion, WorkflowVersion)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _load_yaml_file(path: Traversable | Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in definition file: {path}")
    return data


def _packaged_definitions_directory(kind: str) -> Traversable | None:
    try:
        directory = resources.files(PACKAGED_DEFINITIONS_PACKAGE).joinpath("definitions", kind)
    except ModuleNotFoundError:
        return None
    if not directory.is_dir():
        return None
    return directory


def _configured_definitions_root() -> Path | None:
    try:
        definitions_root = load_settings().definitions_root
    except Exception:
        return None
    if definitions_root is None:
        return None
    return definitions_root if definitions_root.is_dir() else None


def _filesystem_definitions_directory(root: Path | None = None) -> Path | None:
    if root is not None:
        return root if root.is_dir() else None

    override = os.environ.get(DEFINITIONS_ROOT_ENV)
    if override:
        directory = Path(override).expanduser()
        return directory if directory.is_dir() else None

    configured = _configured_definitions_root()
    if configured is not None:
        return configured

    return None


def _iter_yaml_files(directory: Traversable | Path) -> list[Traversable | Path]:
    if isinstance(directory, Path):
        return cast(
            list[Traversable | Path],
            sorted(path for path in directory.glob("*.yaml") if path.is_file()),
        )
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.name.endswith(".yaml")),
        key=lambda path: path.name,
    )


def iter_definition_files(
    kind: str,
    *,
    definitions_root: Path | None = None,
) -> list[Traversable | Path]:
    files_by_name: dict[str, Traversable | Path] = {}

    packaged_directory = _packaged_definitions_directory(kind)
    if packaged_directory is not None:
        for path in _iter_yaml_files(packaged_directory):
            files_by_name[path.name] = path

    filesystem_directory = _filesystem_definitions_directory(definitions_root)
    if filesystem_directory is not None:
        directory = filesystem_directory / kind
        if directory.is_dir():
            for path in _iter_yaml_files(directory):
                files_by_name[path.name] = path

    if not files_by_name:
        return []

    packaged_names = set()
    packaged_directory = _packaged_definitions_directory(kind)
    if packaged_directory is not None:
        packaged_names = {path.name for path in _iter_yaml_files(packaged_directory)}

    ordered_names = sorted(
        files_by_name,
        key=lambda name: (name in packaged_names, name),
    )
    return [files_by_name[name] for name in ordered_names]


def _validate_definition_identity(path: Traversable | Path, definition_id: str) -> None:
    filename_stem = Path(path.name).stem
    if definition_id != filename_stem:
        raise InvalidDefinitionError(
            f"Definition id '{definition_id}' must match filename stem '{filename_stem}' for {path}"
        )


def load_role_seed(path: Traversable | Path) -> RoleDefinitionSeed:
    seed = RoleDefinitionSeed.model_validate(_load_yaml_file(path))
    _validate_definition_identity(path, seed.id)
    return seed


def load_policy_seed(path: Traversable | Path) -> PolicyDefinitionSeed:
    seed = PolicyDefinitionSeed.model_validate(_load_yaml_file(path))
    _validate_definition_identity(path, seed.id)
    return seed


def load_workflow_seed(path: Traversable | Path) -> WorkflowDefinitionSeed:
    seed = WorkflowDefinitionSeed.model_validate(_load_yaml_file(path))
    _validate_definition_identity(path, seed.id)
    return seed


def load_skill_seed(path: Traversable | Path) -> SkillDefinitionSeed:
    seed = SkillDefinitionSeed.model_validate(_load_yaml_file(path))
    _validate_definition_identity(path, seed.key)
    return seed


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
        if publish:
            if latest_version.status != DefinitionVersionStatus.PUBLISHED:
                await _archive_published_versions(
                    session,
                    version_model=version_model,
                    foreign_key_name=foreign_key_name,
                    definition_id=definition.id,
                )
                latest_version.status = DefinitionVersionStatus.PUBLISHED
                latest_version.published_at = now
            return latest_version

        if latest_version.status == DefinitionVersionStatus.DRAFT:
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
    version = cast(
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
    await _sync_role_skill_bindings(session, role_version=version, skill_refs=seed.skill_refs, publish=publish)
    return version


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
    seed = seed.model_copy(update={"nodes": flatten_workflow_nodes(seed.nodes)}, deep=True)
    definition = await _upsert_definition(
        session,
        WorkflowDefinition,
        key=seed.id,
        description=seed.description,
    )
    version = cast(
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
    await _sync_workflow_skill_bindings(session, workflow_version=version, workflow_seed=seed, publish=publish)
    return version


async def upsert_skill_seed(
    session: AsyncSession,
    seed: SkillDefinitionSeed,
    *,
    publish: bool = True,
) -> SkillVersion:
    skill = await session.scalar(
        select(SkillRegistry).where(
            SkillRegistry.provider == seed.provider,
            SkillRegistry.key == seed.key,
        )
    )
    if skill is None:
        skill = SkillRegistry(
            provider=seed.provider,
            key=seed.key,
            description=seed.description,
            source_uri=seed.source_uri,
        )
        session.add(skill)
        await session.flush()
    else:
        skill.description = seed.description
        skill.source_uri = seed.source_uri

    version_label = seed.version or EXTERNAL_CURRENT_VERSION
    manifest = seed.model_dump(mode="json")
    version = await session.scalar(
        select(SkillVersion).where(
            SkillVersion.skill_registry_id == skill.id,
            SkillVersion.version_label == version_label,
        )
    )
    now = _utcnow_naive()
    status = DefinitionVersionStatus.PUBLISHED if publish else DefinitionVersionStatus.DRAFT
    source_ref = seed.artifact_uri or seed.source_uri or f"{seed.provider.value}:{seed.key}"

    if publish:
        published_versions = await session.scalars(
            select(SkillVersion).where(
                SkillVersion.skill_registry_id == skill.id,
                SkillVersion.status == DefinitionVersionStatus.PUBLISHED,
            )
        )
        for published_version in published_versions:
            if version is None or published_version.id != version.id:
                published_version.status = DefinitionVersionStatus.ARCHIVED

    if version is None:
        version = SkillVersion(
            skill_registry_id=skill.id,
            version_label=version_label,
            status=status,
            source_ref=source_ref,
            manifest=manifest,
            published_at=now if publish else None,
        )
        session.add(version)
    else:
        if publish or version.status != DefinitionVersionStatus.PUBLISHED:
            version.status = status
        version.source_ref = source_ref
        version.manifest = manifest
        if publish:
            version.published_at = now
        elif version.status != DefinitionVersionStatus.PUBLISHED:
            version.published_at = None
    await session.flush()
    return version


def _dedupe_skill_refs(skill_refs: Sequence[SkillReferenceSeed]) -> list[SkillReferenceSeed]:
    unique_refs: dict[tuple[str, str, str | None, str, str], SkillReferenceSeed] = {}
    for skill_ref in skill_refs:
        unique_refs[(
            skill_ref.provider.value,
            skill_ref.key,
            skill_ref.version,
            skill_ref.state.value,
            skill_ref.runtime_name,
        )] = skill_ref
    return list(unique_refs.values())


async def _find_skill_version_for_ref(
    session: AsyncSession,
    skill_ref: SkillReferenceSeed,
    *,
    publish: bool,
) -> SkillVersion | None:
    base = (
        select(SkillVersion)
        .join(SkillRegistry)
        .options(selectinload(SkillVersion.skill))
        .where(
            SkillRegistry.provider == skill_ref.provider,
            SkillRegistry.key == skill_ref.key,
        )
    )
    if skill_ref.version:
        return cast(
            SkillVersion | None,
            await session.scalar(
                base.where(SkillVersion.version_label == skill_ref.version).order_by(
                    SkillVersion.created_at.desc()
                )
            ),
        )
    if publish:
        published = cast(
            SkillVersion | None,
            await session.scalar(
                base.where(SkillVersion.status == DefinitionVersionStatus.PUBLISHED).order_by(
                    SkillVersion.published_at.desc(),
                    SkillVersion.created_at.desc(),
                )
            ),
        )
        if published is not None:
            return published
    return cast(
        SkillVersion | None,
        await session.scalar(base.order_by(SkillVersion.created_at.desc())),
    )


async def _resolve_skill_version_for_ref(
    session: AsyncSession,
    skill_ref: SkillReferenceSeed,
    *,
    publish: bool,
) -> SkillVersion:
    version = await _find_skill_version_for_ref(session, skill_ref, publish=publish)
    if version is None:
        return await upsert_skill_reference(session, skill_ref, publish=publish)
    if publish and version.status != DefinitionVersionStatus.PUBLISHED:
        version.status = DefinitionVersionStatus.PUBLISHED
        version.published_at = _utcnow_naive()
        await session.flush()
    return version


async def _sync_role_skill_bindings(
    session: AsyncSession,
    *,
    role_version: RoleVersion,
    skill_refs: Sequence[SkillReferenceSeed],
    publish: bool,
) -> None:
    now = _utcnow_naive()
    await session.execute(
        delete(RoleVersionSkillBinding).where(RoleVersionSkillBinding.role_version_id == role_version.id)
    )
    for skill_ref in _dedupe_skill_refs(skill_refs):
        skill_version = await _resolve_skill_version_for_ref(session, skill_ref, publish=publish)
        session.add(
            RoleVersionSkillBinding(
                role_version_id=role_version.id,
                skill_version_id=skill_version.id,
                state=skill_ref.state,
                created_at=now,
                updated_at=now,
            )
        )
    await session.flush()


async def _sync_workflow_skill_bindings(
    session: AsyncSession,
    *,
    workflow_version: WorkflowVersion,
    workflow_seed: WorkflowDefinitionSeed,
    publish: bool,
) -> None:
    workflow_seed = workflow_seed.model_copy(update={"nodes": flatten_workflow_nodes(workflow_seed.nodes)}, deep=True)
    now = _utcnow_naive()
    await session.execute(
        delete(WorkflowVersionSkillBinding).where(
            WorkflowVersionSkillBinding.workflow_version_id == workflow_version.id
        )
    )
    await session.execute(
        delete(WorkflowNodeSkillBinding).where(
            WorkflowNodeSkillBinding.workflow_version_id == workflow_version.id
        )
    )
    for skill_ref in _dedupe_skill_refs(workflow_seed.skill_refs):
        skill_version = await _resolve_skill_version_for_ref(session, skill_ref, publish=publish)
        session.add(
            WorkflowVersionSkillBinding(
                workflow_version_id=workflow_version.id,
                skill_version_id=skill_version.id,
                state=skill_ref.state,
                created_at=now,
                updated_at=now,
            )
        )
    for node in workflow_seed.nodes:
        for skill_ref in _dedupe_skill_refs(node.skill_refs):
            skill_version = await _resolve_skill_version_for_ref(session, skill_ref, publish=publish)
            session.add(
                WorkflowNodeSkillBinding(
                    workflow_version_id=workflow_version.id,
                    node_key=node.id,
                    skill_version_id=skill_version.id,
                    state=skill_ref.state,
                    created_at=now,
                    updated_at=now,
                )
            )
    await session.flush()


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
    definitions_root: Path | None = None,
) -> dict[str, int]:
    role_paths = iter_definition_files("roles", definitions_root=definitions_root)
    policy_paths = iter_definition_files("policies", definitions_root=definitions_root)
    workflow_paths = iter_definition_files("workflows", definitions_root=definitions_root)
    skill_paths = iter_definition_files("skills", definitions_root=definitions_root)

    role_seeds = [load_role_seed(path) for path in role_paths]
    workflow_seeds = [load_workflow_seed(path) for path in workflow_paths]
    skill_seeds = [load_skill_seed(path) for path in skill_paths]

    for skill_seed in skill_seeds:
        await upsert_skill_seed(session, skill_seed, publish=publish)

    for role_seed in role_seeds:
        await upsert_role_seed(session, role_seed, publish=publish)

    for path in policy_paths:
        await upsert_policy_seed(session, load_policy_seed(path), publish=publish)

    for workflow_seed in workflow_seeds:
        await upsert_workflow_seed(session, workflow_seed, publish=publish)

    await session.flush()
    skill_registry_count = await session.scalar(select(func.count(SkillRegistry.id)))
    return {
        "roles": len(role_seeds),
        "policies": len(policy_paths),
        "workflows": len(workflow_seeds),
        "skills": int(skill_registry_count or 0),
    }


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
