from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.compiler import (
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
from app.registry.lookup import (
    build_role_policy_lookup,
    compile_current_workflow,
    compile_current_workflow_launch_snapshot,
    load_current_policy,
    load_current_role,
    load_current_workflow,
    load_policy_revision,
    load_role_revision,
)
from app.registry.seeds import seed_definition_registry
from app.registry.support import (
    RegistryWorkflowDefinition,
    acquire_definition_owner_row,
    canonical_content_hash,
    load_current_definition_revision,
    load_definition_revision_by_content_hash,
    model_from_attrs,
    next_registry_revision_no,
    policy_revision_id,
    role_revision_id,
    seed_source_matches,
    workflow_revision_id,
)
from app.schemas.definitions.registry import PolicyDefinitionInput, RoleDefinitionInput
from app.schemas.definitions.workflow import WorkflowDefinitionInput

__all__ = [
    "RegistryWorkflowDefinition",
    "build_role_policy_lookup",
    "compile_current_workflow",
    "compile_current_workflow_launch_snapshot",
    "load_current_policy",
    "load_current_role",
    "load_current_workflow",
    "load_policy_revision",
    "load_role_revision",
    "seed_definition_registry",
    "upsert_policy_definition",
    "upsert_role_definition",
    "upsert_workflow_definition",
]


async def upsert_workflow_definition(
    session: AsyncSession,
    definition: WorkflowDefinitionInput,
    *,
    source_path: str | None = None,
    allow_existing_update: bool = True,
) -> RegistryWorkflowDefinition:
    content_json = definition.model_dump(mode="json", exclude={"kind"})
    content_hash = canonical_content_hash(content_json)
    current_seed_owned = False
    definition_row, created_owner = await acquire_definition_owner_row(
        session,
        WorkflowDefinitionModel,
        key_column=WorkflowDefinitionModel.workflow_key,
        key=definition.id,
        build_row=lambda: WorkflowDefinitionModel(
            workflow_key=definition.id,
            current_revision_no=None,
        ),
    )
    if not created_owner:
        current_revision = await load_current_definition_revision(
            session,
            WorkflowDefinitionModel,
            WorkflowRevisionModel,
            key_column=WorkflowRevisionModel.workflow_key,
            key_field="workflow",
            key=definition.id,
        )
        if not allow_existing_update:
            if source_path is None:
                return await load_current_workflow(session, definition.id)
            current_seed_owned = seed_source_matches(
                stored_source_path=current_revision.source_path,
                expected_source_path=source_path,
            )
            matching_revision = await load_definition_revision_by_content_hash(
                session,
                WorkflowRevisionModel,
                key_column=WorkflowRevisionModel.workflow_key,
                key=definition.id,
                content_hash=content_hash,
            )
            if matching_revision is not None:
                if (
                    current_seed_owned
                    and definition_row.current_revision_no != matching_revision.revision_no
                ):
                    definition_row.current_revision_no = matching_revision.revision_no
                    session.add(definition_row)
                    await session.flush()
                return model_from_attrs(
                    RegistryWorkflowDefinition,
                    definition=definition,
                    revision_no=matching_revision.revision_no,
                )
        elif current_revision.content_hash == content_hash:
            return model_from_attrs(
                RegistryWorkflowDefinition,
                definition=definition,
                revision_no=current_revision.revision_no,
            )
        revision_no = await next_registry_revision_no(
            session,
            WorkflowRevisionModel,
            key_column=WorkflowRevisionModel.workflow_key,
            key=definition.id,
        )
    else:
        revision_no = 1
    await _validate_candidate_workflow(
        session,
        definition=definition,
        revision_no=revision_no,
    )
    if created_owner or allow_existing_update or current_seed_owned:
        definition_row.current_revision_no = revision_no
        session.add(definition_row)
    session.add(
        WorkflowRevisionModel(
            workflow_revision_id=workflow_revision_id(definition.id, revision_no),
            workflow_key=definition.id,
            revision_no=revision_no,
            content_hash=content_hash,
            content_json=content_json,
            source_path=source_path,
        )
    )
    await session.flush()
    return model_from_attrs(
        RegistryWorkflowDefinition,
        definition=definition,
        revision_no=revision_no,
    )


async def upsert_role_definition(
    session: AsyncSession,
    definition: RoleDefinitionInput,
    *,
    source_path: str | None = None,
    allow_existing_update: bool = True,
) -> RoleRevisionDefinition:
    content_json = definition.model_dump(mode="json", exclude={"kind"})
    content_hash = canonical_content_hash(content_json)
    current_seed_owned = False
    definition_row, created_owner = await acquire_definition_owner_row(
        session,
        RoleDefinitionModel,
        key_column=RoleDefinitionModel.role_key,
        key=definition.id,
        build_row=lambda: RoleDefinitionModel(
            role_key=definition.id,
            current_revision_no=None,
        ),
    )
    if not created_owner:
        current_revision = await load_current_definition_revision(
            session,
            RoleDefinitionModel,
            RoleRevisionModel,
            key_column=RoleRevisionModel.role_key,
            key_field="role",
            key=definition.id,
        )
        if not allow_existing_update:
            if source_path is None:
                return await load_current_role(session, definition.id)
            current_seed_owned = seed_source_matches(
                stored_source_path=current_revision.source_path,
                expected_source_path=source_path,
            )
            matching_revision = await load_definition_revision_by_content_hash(
                session,
                RoleRevisionModel,
                key_column=RoleRevisionModel.role_key,
                key=definition.id,
                content_hash=content_hash,
            )
            if matching_revision is not None:
                if (
                    current_seed_owned
                    and definition_row.current_revision_no != matching_revision.revision_no
                ):
                    definition_row.current_revision_no = matching_revision.revision_no
                    session.add(definition_row)
                    await session.flush()
                return model_from_attrs(
                    RoleRevisionDefinition,
                    definition=definition,
                    revision_no=matching_revision.revision_no,
                )
        elif current_revision.content_hash == content_hash:
            return model_from_attrs(
                RoleRevisionDefinition,
                definition=definition,
                revision_no=current_revision.revision_no,
            )
        revision_no = await next_registry_revision_no(
            session,
            RoleRevisionModel,
            key_column=RoleRevisionModel.role_key,
            key=definition.id,
        )
    else:
        revision_no = 1
    if created_owner or allow_existing_update or current_seed_owned:
        definition_row.current_revision_no = revision_no
        session.add(definition_row)
    session.add(
        RoleRevisionModel(
            role_revision_id=role_revision_id(definition.id, revision_no),
            role_key=definition.id,
            revision_no=revision_no,
            content_hash=content_hash,
            content_json=content_json,
            source_path=source_path,
        )
    )
    await session.flush()
    return model_from_attrs(
        RoleRevisionDefinition,
        definition=definition,
        revision_no=revision_no,
    )


async def upsert_policy_definition(
    session: AsyncSession,
    definition: PolicyDefinitionInput,
    *,
    source_path: str | None = None,
    allow_existing_update: bool = True,
) -> PolicyRevisionDefinition:
    content_json = definition.model_dump(mode="json", exclude={"kind"})
    content_hash = canonical_content_hash(content_json)
    current_seed_owned = False
    definition_row, created_owner = await acquire_definition_owner_row(
        session,
        PolicyDefinitionModel,
        key_column=PolicyDefinitionModel.policy_key,
        key=definition.id,
        build_row=lambda: PolicyDefinitionModel(
            policy_key=definition.id,
            current_revision_no=None,
        ),
    )
    if not created_owner:
        current_revision = await load_current_definition_revision(
            session,
            PolicyDefinitionModel,
            PolicyRevisionModel,
            key_column=PolicyRevisionModel.policy_key,
            key_field="policy",
            key=definition.id,
        )
        if not allow_existing_update:
            if source_path is None:
                return await load_current_policy(session, definition.id)
            current_seed_owned = seed_source_matches(
                stored_source_path=current_revision.source_path,
                expected_source_path=source_path,
            )
            matching_revision = await load_definition_revision_by_content_hash(
                session,
                PolicyRevisionModel,
                key_column=PolicyRevisionModel.policy_key,
                key=definition.id,
                content_hash=content_hash,
            )
            if matching_revision is not None:
                if (
                    current_seed_owned
                    and definition_row.current_revision_no != matching_revision.revision_no
                ):
                    definition_row.current_revision_no = matching_revision.revision_no
                    session.add(definition_row)
                    await session.flush()
                return model_from_attrs(
                    PolicyRevisionDefinition,
                    definition=definition,
                    revision_no=matching_revision.revision_no,
                )
        elif current_revision.content_hash == content_hash:
            return model_from_attrs(
                PolicyRevisionDefinition,
                definition=definition,
                revision_no=current_revision.revision_no,
            )
        revision_no = await next_registry_revision_no(
            session,
            PolicyRevisionModel,
            key_column=PolicyRevisionModel.policy_key,
            key=definition.id,
        )
    else:
        revision_no = 1
    if created_owner or allow_existing_update or current_seed_owned:
        definition_row.current_revision_no = revision_no
        session.add(definition_row)
    session.add(
        PolicyRevisionModel(
            policy_revision_id=policy_revision_id(definition.id, revision_no),
            policy_key=definition.id,
            revision_no=revision_no,
            content_hash=content_hash,
            content_json=content_json,
            source_path=source_path,
        )
    )
    await session.flush()
    return model_from_attrs(
        PolicyRevisionDefinition,
        definition=definition,
        revision_no=revision_no,
    )


async def _validate_candidate_workflow(
    session: AsyncSession,
    *,
    definition: WorkflowDefinitionInput,
    revision_no: int,
) -> None:
    lookup = await build_role_policy_lookup(session)
    compile_workflow(
        workflow=definition,
        workflow_revision=model_from_attrs(
            WorkflowRevisionMetadata,
            workflow_key=definition.id,
            definition_revision_no=revision_no,
        ),
        compiler_version="registry-guard",
        lookup=lookup,
    )
