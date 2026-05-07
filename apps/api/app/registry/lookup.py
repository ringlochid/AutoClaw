from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
from app.schemas.definitions.validation import flatten_workflow
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


def collect_workflow_role_policy_keys(
    workflow: WorkflowDefinitionInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    role_keys: list[str] = []
    policy_keys: list[str] = []
    seen_roles: set[str] = set()
    seen_policies: set[str] = set()

    for flattened_node in flatten_workflow(workflow.root):
        if flattened_node.role not in seen_roles:
            seen_roles.add(flattened_node.role)
            role_keys.append(flattened_node.role)
        if flattened_node.policy is None or flattened_node.policy in seen_policies:
            continue
        seen_policies.add(flattened_node.policy)
        policy_keys.append(flattened_node.policy)

    return tuple(role_keys), tuple(policy_keys)


async def _load_requested_role(
    session: AsyncSession,
    role_key: str,
) -> RoleRevisionDefinition | None:
    role_definition = await session.scalar(
        select(RoleDefinitionModel)
        .options(joinedload(RoleDefinitionModel.current_revision))
        .where(RoleDefinitionModel.role_key == role_key)
    )
    if role_definition is None or role_definition.current_revision_no is None:
        return None

    role_revision = role_definition.current_revision
    if role_revision is None:
        raise ValueError(
            f"missing current revision for role '{role_key}' at revision "
            f"{role_definition.current_revision_no}"
        )
    return model_from_attrs(
        RoleRevisionDefinition,
        definition=RoleDefinitionInput.model_validate(role_revision.content_json),
        revision_no=role_revision.revision_no,
    )


async def _load_requested_policy(
    session: AsyncSession,
    policy_key: str,
) -> PolicyRevisionDefinition | None:
    policy_definition = await session.scalar(
        select(PolicyDefinitionModel)
        .options(joinedload(PolicyDefinitionModel.current_revision))
        .where(PolicyDefinitionModel.policy_key == policy_key)
    )
    if policy_definition is None or policy_definition.current_revision_no is None:
        return None

    policy_revision = policy_definition.current_revision
    if policy_revision is None:
        raise ValueError(
            f"missing current revision for policy '{policy_key}' at revision "
            f"{policy_definition.current_revision_no}"
        )
    return model_from_attrs(
        PolicyRevisionDefinition,
        definition=PolicyDefinitionInput.model_validate(policy_revision.content_json),
        revision_no=policy_revision.revision_no,
    )


async def build_role_policy_lookup(
    session: AsyncSession,
    *,
    role_keys: Sequence[str] | None = None,
    policy_keys: Sequence[str] | None = None,
) -> MappingRolePolicyLookup:
    if role_keys is None:
        role_rows = await load_current_definition_revision_rows(
            session,
            RoleDefinitionModel,
            RoleRevisionModel,
            definition_key=RoleDefinitionModel.role_key,
            revision_key=RoleRevisionModel.role_key,
            current_revision_no=RoleDefinitionModel.current_revision_no,
        )
        roles = {
            role_definition.role_key: model_from_attrs(
                RoleRevisionDefinition,
                definition=RoleDefinitionInput.model_validate(role_revision.content_json),
                revision_no=role_revision.revision_no,
            )
            for role_definition, role_revision in role_rows
        }
    else:
        roles = {}
        for role_key in dict.fromkeys(role_keys):
            role = await _load_requested_role(session, role_key)
            if role is not None:
                roles[role_key] = role

    if policy_keys is None:
        policy_rows = await load_current_definition_revision_rows(
            session,
            PolicyDefinitionModel,
            PolicyRevisionModel,
            definition_key=PolicyDefinitionModel.policy_key,
            revision_key=PolicyRevisionModel.policy_key,
            current_revision_no=PolicyDefinitionModel.current_revision_no,
        )
        policies = {
            policy_definition.policy_key: model_from_attrs(
                PolicyRevisionDefinition,
                definition=PolicyDefinitionInput.model_validate(policy_revision.content_json),
                revision_no=policy_revision.revision_no,
            )
            for policy_definition, policy_revision in policy_rows
        }
    else:
        policies = {}
        for policy_key in dict.fromkeys(policy_keys):
            policy = await _load_requested_policy(session, policy_key)
            if policy is not None:
                policies[policy_key] = policy

    return MappingRolePolicyLookup(roles=roles, policies=policies)


async def build_workflow_role_policy_lookup(
    session: AsyncSession,
    workflow: WorkflowDefinitionInput,
) -> MappingRolePolicyLookup:
    role_keys, policy_keys = collect_workflow_role_policy_keys(workflow)
    return await build_role_policy_lookup(
        session,
        role_keys=role_keys,
        policy_keys=policy_keys,
    )


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
    lookup = await build_workflow_role_policy_lookup(session, workflow.definition)
    compiled_plan = compile_workflow(
        workflow=workflow.definition,
        workflow_revision=model_from_attrs(
            WorkflowRevisionMetadata,
            workflow_key=workflow_key,
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
