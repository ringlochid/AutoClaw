from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DefinitionVersionStatus
from app.core.errors import InvalidDefinitionError
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
from app.services.registry_service import bootstrap_registry


async def test_bootstrap_registry_persists_published_definitions(
    db_session: AsyncSession,
) -> None:
    result = await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    role_definition_count = await db_session.scalar(select(func.count(RoleDefinition.id)))
    policy_definition_count = await db_session.scalar(select(func.count(PolicyDefinition.id)))
    workflow_definition_count = await db_session.scalar(select(func.count(WorkflowDefinition.id)))
    skill_registry_count = await db_session.scalar(select(func.count(SkillRegistry.id)))
    published_role_versions = await db_session.scalar(
        select(func.count(RoleVersion.id)).where(
            RoleVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    published_policy_versions = await db_session.scalar(
        select(func.count(PolicyVersion.id)).where(
            PolicyVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    published_workflow_versions = await db_session.scalar(
        select(func.count(WorkflowVersion.id)).where(
            WorkflowVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    published_skill_versions = await db_session.scalar(
        select(func.count(SkillVersion.id)).where(
            SkillVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    role_keys = list(
        (
            await db_session.scalars(select(RoleDefinition.key).order_by(RoleDefinition.key.asc()))
        ).all()
    )
    policy_keys = list(
        (
            await db_session.scalars(
                select(PolicyDefinition.key).order_by(PolicyDefinition.key.asc())
            )
        ).all()
    )
    workflow_keys = list(
        (
            await db_session.scalars(
                select(WorkflowDefinition.key).order_by(WorkflowDefinition.key.asc())
            )
        ).all()
    )
    skill_keys = list(
        (
            await db_session.scalars(select(SkillRegistry.key).order_by(SkillRegistry.key.asc()))
        ).all()
    )

    assert result["roles"] == role_definition_count == published_role_versions
    assert result["policies"] == policy_definition_count == published_policy_versions
    assert result["workflows"] == workflow_definition_count == published_workflow_versions
    assert result["skills"] == skill_registry_count == published_skill_versions
    assert role_definition_count == 4
    assert policy_definition_count == 3
    assert workflow_definition_count == 4
    assert skill_registry_count == 1
    assert set(role_keys) >= {"main-loop-worker", "planner-supervisor", "reviewer", "syncer"}
    assert set(policy_keys) >= {"approval-heavy", "cautious", "default"}
    assert set(workflow_keys) >= {
        "approval-change",
        "default-bugfix",
        "max-complexity-review",
        "research-report",
    }
    assert set(skill_keys) >= {"contract-checker"}


async def test_bootstrap_registry_is_idempotent_for_current_packaged_definitions(
    db_session: AsyncSession,
) -> None:
    first_result = await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    second_result = await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    published_role_versions = await db_session.scalar(
        select(func.count(RoleVersion.id)).where(
            RoleVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    published_policy_versions = await db_session.scalar(
        select(func.count(PolicyVersion.id)).where(
            PolicyVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    published_workflow_versions = await db_session.scalar(
        select(func.count(WorkflowVersion.id)).where(
            WorkflowVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )
    published_skill_versions = await db_session.scalar(
        select(func.count(SkillVersion.id)).where(
            SkillVersion.status == DefinitionVersionStatus.PUBLISHED
        )
    )

    assert second_result == first_result
    assert published_role_versions == first_result["roles"]
    assert published_policy_versions == first_result["policies"]
    assert published_workflow_versions == first_result["workflows"]
    assert published_skill_versions == first_result["skills"]


async def test_bootstrap_registry_rejects_filename_id_mismatch(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    definitions_root = tmp_path / "defs"
    for kind in ("roles", "policies", "workflows"):
        (definitions_root / kind).mkdir(parents=True, exist_ok=True)

    (definitions_root / "roles" / "wrong-name.yaml").write_text(
        """
id: planner-supervisor
kind: supervisor
description: mismatch
allowed_modes:
  - plan
default_policy: default
checkpoint_schema: supervisor_status_v1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    try:
        await bootstrap_registry(db_session, publish=True, definitions_root=definitions_root)
    except InvalidDefinitionError as exc:
        assert "filename stem" in str(exc)
    else:
        raise AssertionError("Expected filename/id mismatch to fail bootstrap")
