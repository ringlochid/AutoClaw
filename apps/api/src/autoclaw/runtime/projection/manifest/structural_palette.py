from __future__ import annotations

from collections.abc import Iterable

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.compiler import MappingRolePolicyLookup
from autoclaw.definitions.contracts.registry import PolicyDefinitionInput, RoleDefinitionInput
from autoclaw.definitions.registry.revisions.reads import load_current_definition_revision_rows
from autoclaw.persistence.models import (
    PolicyDefinitionModel,
    PolicyRevisionModel,
    RoleDefinitionModel,
    RoleRevisionModel,
)
from autoclaw.runtime.contracts import (
    NodeKind,
    StructuralEditPaletteProjection,
    StructuralEditPolicyProjection,
    StructuralEditRoleProjection,
)

_STRUCTURAL_EDIT_NODE_KINDS = (NodeKind.PARENT, NodeKind.WORKER)


def structural_edit_palette_from_lookup(
    lookup: MappingRolePolicyLookup,
) -> StructuralEditPaletteProjection:
    return StructuralEditPaletteProjection(
        roles=tuple(
            sorted(
                _structural_edit_roles_from_definitions(lookup.roles.values()),
                key=lambda role: role.role,
            )
        ),
        policies=tuple(
            sorted(
                _structural_edit_policies_from_definitions(lookup.policies.values()),
                key=lambda policy: policy.policy,
            )
        ),
    )


async def build_current_structural_edit_palette(
    session: AsyncSession,
) -> StructuralEditPaletteProjection:
    role_rows = await load_current_definition_revision_rows(
        session,
        RoleDefinitionModel,
        RoleRevisionModel,
        definition_key=RoleDefinitionModel.role_key,
        revision_key=RoleRevisionModel.role_key,
        current_revision_no=RoleDefinitionModel.current_revision_no,
    )
    policy_rows = await load_current_definition_revision_rows(
        session,
        PolicyDefinitionModel,
        PolicyRevisionModel,
        definition_key=PolicyDefinitionModel.policy_key,
        revision_key=PolicyRevisionModel.policy_key,
        current_revision_no=PolicyDefinitionModel.current_revision_no,
    )
    return StructuralEditPaletteProjection(
        roles=tuple(
            sorted(
                _structural_edit_roles_from_rows(role_rows),
                key=lambda role: role.role,
            )
        ),
        policies=tuple(
            sorted(
                _structural_edit_policies_from_rows(policy_rows),
                key=lambda policy: policy.policy,
            )
        ),
    )


def _structural_edit_roles_from_definitions(
    definitions: Iterable[object],
) -> list[StructuralEditRoleProjection]:
    roles: list[StructuralEditRoleProjection] = []
    for definition_row in definitions:
        definition = getattr(definition_row, "definition", None)
        if not isinstance(definition, RoleDefinitionInput):
            continue
        allowed_node_kinds = tuple(
            node_kind
            for node_kind in definition.allowed_node_kinds
            if node_kind in _STRUCTURAL_EDIT_NODE_KINDS
        )
        if not allowed_node_kinds:
            continue
        roles.append(
            StructuralEditRoleProjection(
                role=definition.id,
                allowed_node_kinds=allowed_node_kinds,
                description=definition.description,
            )
        )
    return roles


def _structural_edit_policies_from_definitions(
    definitions: Iterable[object],
) -> list[StructuralEditPolicyProjection]:
    policies: list[StructuralEditPolicyProjection] = []
    for definition_row in definitions:
        definition = getattr(definition_row, "definition", None)
        if not isinstance(definition, PolicyDefinitionInput):
            continue
        applies_to = tuple(
            node_kind
            for node_kind in definition.applies_to
            if node_kind in _STRUCTURAL_EDIT_NODE_KINDS
        )
        if not applies_to:
            continue
        policies.append(
            StructuralEditPolicyProjection(
                policy=definition.id,
                applies_to=applies_to,
                description=definition.description,
            )
        )
    return policies


def _structural_edit_roles_from_rows(
    rows: Iterable[tuple[RoleDefinitionModel, RoleRevisionModel]],
) -> list[StructuralEditRoleProjection]:
    roles: list[StructuralEditRoleProjection] = []
    for role_definition, role_revision in rows:
        try:
            definition = RoleDefinitionInput.model_validate(role_revision.content_json)
        except ValidationError:
            continue
        allowed_node_kinds = tuple(
            node_kind
            for node_kind in definition.allowed_node_kinds
            if node_kind in _STRUCTURAL_EDIT_NODE_KINDS
        )
        if not allowed_node_kinds:
            continue
        roles.append(
            StructuralEditRoleProjection(
                role=role_definition.role_key,
                allowed_node_kinds=allowed_node_kinds,
                description=definition.description,
            )
        )
    return roles


def _structural_edit_policies_from_rows(
    rows: Iterable[tuple[PolicyDefinitionModel, PolicyRevisionModel]],
) -> list[StructuralEditPolicyProjection]:
    policies: list[StructuralEditPolicyProjection] = []
    for policy_definition, policy_revision in rows:
        try:
            definition = PolicyDefinitionInput.model_validate(policy_revision.content_json)
        except ValidationError:
            continue
        applies_to = tuple(
            node_kind
            for node_kind in definition.applies_to
            if node_kind in _STRUCTURAL_EDIT_NODE_KINDS
        )
        if not applies_to:
            continue
        policies.append(
            StructuralEditPolicyProjection(
                policy=policy_definition.policy_key,
                applies_to=applies_to,
                description=definition.description,
            )
        )
    return policies
