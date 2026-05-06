from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.compiler import (
    MappingRolePolicyLookup,
    NormalizedCompiledPlan,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from app.db.models import (
    PolicyDefinitionModel,
    PolicyRevisionModel,
    RoleDefinitionModel,
    RoleRevisionModel,
    WorkflowDefinitionModel,
    WorkflowRevisionModel,
)
from app.registry.support import (
    RegistryWorkflowDefinition,
    load_current_definition_revision,
    load_current_definition_revision_rows,
    load_definition_revision_by_no,
    model_from_attrs,
)
from app.schemas.definitions.registry import PolicyDefinitionInput, RoleDefinitionInput
from app.schemas.definitions.workflow import WorkflowDefinitionInput


@dataclass(frozen=True)
class CompiledWorkflowLaunchSnapshot:
    workflow: RegistryWorkflowDefinition
    compiled_plan: NormalizedCompiledPlan
    role_policy_lookup: MappingRolePolicyLookup


async def load_current_role(session: AsyncSession, role_key: str) -> RoleRevisionDefinition:
    revision = await load_current_definition_revision(
        session,
        RoleDefinitionModel,
        RoleRevisionModel,
        key_column=RoleRevisionModel.role_key,
        key_field="role",
        key=role_key,
    )
    return model_from_attrs(
        RoleRevisionDefinition,
        definition=RoleDefinitionInput.model_validate(revision.content_json),
        revision_no=revision.revision_no,
    )


async def load_role_revision(
    session: AsyncSession,
    role_key: str,
    revision_no: int,
) -> RoleRevisionDefinition:
    revision = await load_definition_revision_by_no(
        session,
        RoleRevisionModel,
        key_column=RoleRevisionModel.role_key,
        key_field="role",
        key=role_key,
        revision_no=revision_no,
    )
    return model_from_attrs(
        RoleRevisionDefinition,
        definition=RoleDefinitionInput.model_validate(revision.content_json),
        revision_no=revision.revision_no,
    )


async def load_current_policy(session: AsyncSession, policy_key: str) -> PolicyRevisionDefinition:
    revision = await load_current_definition_revision(
        session,
        PolicyDefinitionModel,
        PolicyRevisionModel,
        key_column=PolicyRevisionModel.policy_key,
        key_field="policy",
        key=policy_key,
    )
    return model_from_attrs(
        PolicyRevisionDefinition,
        definition=PolicyDefinitionInput.model_validate(revision.content_json),
        revision_no=revision.revision_no,
    )


async def load_policy_revision(
    session: AsyncSession,
    policy_key: str,
    revision_no: int,
) -> PolicyRevisionDefinition:
    revision = await load_definition_revision_by_no(
        session,
        PolicyRevisionModel,
        key_column=PolicyRevisionModel.policy_key,
        key_field="policy",
        key=policy_key,
        revision_no=revision_no,
    )
    return model_from_attrs(
        PolicyRevisionDefinition,
        definition=PolicyDefinitionInput.model_validate(revision.content_json),
        revision_no=revision.revision_no,
    )


async def load_current_workflow(
    session: AsyncSession,
    workflow_key: str,
) -> RegistryWorkflowDefinition:
    revision = await load_current_definition_revision(
        session,
        WorkflowDefinitionModel,
        WorkflowRevisionModel,
        key_column=WorkflowRevisionModel.workflow_key,
        key_field="workflow",
        key=workflow_key,
    )
    return model_from_attrs(
        RegistryWorkflowDefinition,
        definition=WorkflowDefinitionInput.model_validate(revision.content_json),
        revision_no=revision.revision_no,
    )


async def build_role_policy_lookup(session: AsyncSession) -> MappingRolePolicyLookup:
    role_rows = await load_current_definition_revision_rows(
        session,
        RoleDefinitionModel,
        RoleRevisionModel,
        definition_key=RoleDefinitionModel.role_key,
        revision_key=RoleRevisionModel.role_key,
        current_revision_no=RoleDefinitionModel.current_revision_no,
    )
    roles = {}
    for role_definition, role_revision in role_rows:
        roles[role_definition.role_key] = model_from_attrs(
            RoleRevisionDefinition,
            definition=RoleDefinitionInput.model_validate(role_revision.content_json),
            revision_no=role_revision.revision_no,
        )

    policy_rows = await load_current_definition_revision_rows(
        session,
        PolicyDefinitionModel,
        PolicyRevisionModel,
        definition_key=PolicyDefinitionModel.policy_key,
        revision_key=PolicyRevisionModel.policy_key,
        current_revision_no=PolicyDefinitionModel.current_revision_no,
    )
    policies = {}
    for policy_definition, policy_revision in policy_rows:
        policies[policy_definition.policy_key] = model_from_attrs(
            PolicyRevisionDefinition,
            definition=PolicyDefinitionInput.model_validate(policy_revision.content_json),
            revision_no=policy_revision.revision_no,
        )
    return MappingRolePolicyLookup(roles=roles, policies=policies)


async def compile_current_workflow(
    session: AsyncSession,
    *,
    workflow_key: str,
    compiler_version: str,
) -> tuple[RegistryWorkflowDefinition, NormalizedCompiledPlan]:
    snapshot = await compile_current_workflow_launch_snapshot(
        session,
        workflow_key=workflow_key,
        compiler_version=compiler_version,
    )
    return snapshot.workflow, snapshot.compiled_plan


async def compile_current_workflow_launch_snapshot(
    session: AsyncSession,
    *,
    workflow_key: str,
    compiler_version: str,
) -> CompiledWorkflowLaunchSnapshot:
    workflow = await load_current_workflow(session, workflow_key)
    lookup = await build_role_policy_lookup(session)
    compiled_plan = compile_workflow(
        workflow=workflow.definition,
        workflow_revision=model_from_attrs(
            WorkflowRevisionMetadata,
            workflow_key=workflow.definition.id,
            definition_revision_no=workflow.revision_no,
        ),
        compiler_version=compiler_version,
        lookup=lookup,
    )
    return CompiledWorkflowLaunchSnapshot(
        workflow=workflow,
        compiled_plan=compiled_plan,
        role_policy_lookup=lookup,
    )
