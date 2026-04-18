from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DefinitionVersionStatus
from app.core.errors import ConflictError, NotFoundError
from app.db.models.registry import (
    PolicyDefinition,
    PolicyVersion,
    RoleDefinition,
    RoleVersion,
    WorkflowDefinition,
    WorkflowVersion,
)
from app.registry.query import get_current_definition_version
from app.runtime.state import utcnow_naive
from app.schemas.registry import PolicyDefinitionSeed, RoleDefinitionSeed, WorkflowDefinitionSeed
from app.services.compiler_service import preview_workflow_seed
from app.services.registry_service import (
    upsert_policy_seed,
    upsert_role_seed,
    upsert_workflow_seed,
)

DefinitionModel = type[RoleDefinition | PolicyDefinition | WorkflowDefinition]
VersionModel = type[RoleVersion | PolicyVersion | WorkflowVersion]
VersionInstance = RoleVersion | PolicyVersion | WorkflowVersion

NO_CURRENT_VERSION = 0


async def _lock_definition_row(
    session: AsyncSession,
    definition_model: DefinitionModel,
    key: str,
) -> RoleDefinition | PolicyDefinition | WorkflowDefinition | None:
    return cast(
        RoleDefinition | PolicyDefinition | WorkflowDefinition | None,
        await session.scalar(
            select(definition_model)
            .where(definition_model.key == key)
            .with_for_update()
        ),
    )


async def enforce_expected_version(
    session: AsyncSession,
    definition_model: DefinitionModel,
    version_model: VersionModel,
    key: str,
    *,
    status_filter: DefinitionVersionStatus,
    expected_version: int | None,
    version_label: str,
) -> None:
    if expected_version is None:
        return

    await _lock_definition_row(session, definition_model, key)
    current = await get_current_definition_version(
        session,
        definition_model,
        version_model,
        key,
        status_filter=status_filter,
    )
    current_version = current.version if current is not None else NO_CURRENT_VERSION
    if current_version != expected_version:
        raise ConflictError(
            f"Expected {version_label} version {expected_version}, found {current_version}"
        )


async def _store_draft_version(
    session: AsyncSession,
    definition_model: DefinitionModel,
    version_model: VersionModel,
    key: str,
    *,
    expected_draft_version: int | None,
    persist_version: Callable[[], Awaitable[VersionInstance]],
    validate_seed: Callable[[], Awaitable[None]] | None = None,
) -> VersionInstance:
    await enforce_expected_version(
        session,
        definition_model,
        version_model,
        key,
        status_filter=DefinitionVersionStatus.DRAFT,
        expected_version=expected_draft_version,
        version_label="draft",
    )
    if validate_seed is not None:
        await validate_seed()
    try:
        return await persist_version()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            f"Concurrent draft update detected for '{key}'. "
            "Retry with the latest expected draft version."
        ) from exc


async def put_role_draft_version(
    session: AsyncSession,
    *,
    key: str,
    seed: RoleDefinitionSeed,
    expected_draft_version: int | None,
) -> RoleVersion:
    return cast(
        RoleVersion,
        await _store_draft_version(
            session,
            RoleDefinition,
            RoleVersion,
            key,
            expected_draft_version=expected_draft_version,
            persist_version=lambda: upsert_role_seed(session, seed, publish=False),
        ),
    )


async def put_policy_draft_version(
    session: AsyncSession,
    *,
    key: str,
    seed: PolicyDefinitionSeed,
    expected_draft_version: int | None,
) -> PolicyVersion:
    return cast(
        PolicyVersion,
        await _store_draft_version(
            session,
            PolicyDefinition,
            PolicyVersion,
            key,
            expected_draft_version=expected_draft_version,
            persist_version=lambda: upsert_policy_seed(session, seed, publish=False),
        ),
    )


async def put_workflow_draft_version(
    session: AsyncSession,
    *,
    key: str,
    seed: WorkflowDefinitionSeed,
    expected_draft_version: int | None,
) -> WorkflowVersion:
    async def validate_seed() -> None:
        await preview_workflow_seed(session, seed)

    return cast(
        WorkflowVersion,
        await _store_draft_version(
            session,
            WorkflowDefinition,
            WorkflowVersion,
            key,
            expected_draft_version=expected_draft_version,
            persist_version=lambda: upsert_workflow_seed(session, seed, publish=False),
            validate_seed=validate_seed,
        ),
    )


async def _load_publishable_versions(
    session: AsyncSession,
    definition_model: DefinitionModel,
    version_model: VersionModel,
    key: str,
) -> list[VersionInstance]:
    await _lock_definition_row(session, definition_model, key)
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


async def _publish_definition_version(
    session: AsyncSession,
    definition_model: DefinitionModel,
    version_model: VersionModel,
    key: str,
    version_number: int,
    *,
    expected_published_version: int | None,
    validate_target: Callable[[VersionInstance], Awaitable[None]] | None = None,
) -> VersionInstance:
    await enforce_expected_version(
        session,
        definition_model,
        version_model,
        key,
        status_filter=DefinitionVersionStatus.PUBLISHED,
        expected_version=expected_published_version,
        version_label="published",
    )
    versions = await _load_publishable_versions(session, definition_model, version_model, key)

    target = next((version for version in versions if version.version == version_number), None)
    if target is None:
        raise NotFoundError(f"No version {version_number} found for '{key}'")

    if validate_target is not None:
        await validate_target(target)

    now = utcnow_naive()
    for version in versions:
        if version.status == DefinitionVersionStatus.PUBLISHED and version.id != target.id:
            version.status = DefinitionVersionStatus.ARCHIVED
    target.status = DefinitionVersionStatus.PUBLISHED
    target.published_at = now
    try:
        await session.flush()
        await session.refresh(target)
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            f"Concurrent publish detected for '{key}'. "
            "Retry with the latest expected published version."
        ) from exc
    return target


async def publish_role_version(
    session: AsyncSession,
    *,
    key: str,
    version_number: int,
    expected_published_version: int | None,
) -> RoleVersion:
    return cast(
        RoleVersion,
        await _publish_definition_version(
            session,
            RoleDefinition,
            RoleVersion,
            key,
            version_number,
            expected_published_version=expected_published_version,
        ),
    )


async def publish_policy_version(
    session: AsyncSession,
    *,
    key: str,
    version_number: int,
    expected_published_version: int | None,
) -> PolicyVersion:
    return cast(
        PolicyVersion,
        await _publish_definition_version(
            session,
            PolicyDefinition,
            PolicyVersion,
            key,
            version_number,
            expected_published_version=expected_published_version,
        ),
    )


async def publish_workflow_version(
    session: AsyncSession,
    *,
    key: str,
    version_number: int,
    expected_published_version: int | None,
) -> WorkflowVersion:
    async def validate_target(target: VersionInstance) -> None:
        if not isinstance(target, WorkflowVersion):
            return
        await preview_workflow_seed(session, WorkflowDefinitionSeed.model_validate(target.content))

    return cast(
        WorkflowVersion,
        await _publish_definition_version(
            session,
            WorkflowDefinition,
            WorkflowVersion,
            key,
            version_number,
            expected_published_version=expected_published_version,
            validate_target=validate_target,
        ),
    )

