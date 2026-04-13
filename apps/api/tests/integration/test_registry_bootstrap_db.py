from sqlalchemy import func, select

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
from app.services.registry_service import bootstrap_registry


async def test_bootstrap_registry_persists_published_definitions(db_session) -> None:
    result = await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    role_definition_count = await db_session.scalar(select(func.count(RoleDefinition.id)))
    policy_definition_count = await db_session.scalar(select(func.count(PolicyDefinition.id)))
    workflow_definition_count = await db_session.scalar(select(func.count(WorkflowDefinition.id)))
    skill_registry_count = await db_session.scalar(select(func.count(SkillRegistry.id)))
    published_role_versions = await db_session.scalar(
        select(func.count(RoleVersion.id)).where(RoleVersion.status == DefinitionVersionStatus.PUBLISHED)
    )
    published_policy_versions = await db_session.scalar(
        select(func.count(PolicyVersion.id)).where(PolicyVersion.status == DefinitionVersionStatus.PUBLISHED)
    )
    published_workflow_versions = await db_session.scalar(
        select(func.count(WorkflowVersion.id)).where(WorkflowVersion.status == DefinitionVersionStatus.PUBLISHED)
    )
    published_skill_versions = await db_session.scalar(
        select(func.count(SkillVersion.id)).where(SkillVersion.status == DefinitionVersionStatus.PUBLISHED)
    )

    assert result == {"roles": 4, "policies": 3, "workflows": 3, "skills": 1}
    assert role_definition_count == 4
    assert policy_definition_count == 3
    assert workflow_definition_count == 3
    assert skill_registry_count == 1
    assert published_role_versions == 4
    assert published_policy_versions == 3
    assert published_workflow_versions == 3
    assert published_skill_versions == 1
