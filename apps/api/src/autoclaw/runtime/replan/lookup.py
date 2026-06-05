from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.contracts.registry import PolicyDefinitionInput, RoleDefinitionInput
from autoclaw.definitions.contracts.workflow import NodeKind
from autoclaw.definitions.registry import load_current_policy, load_current_role
from autoclaw.runtime.errors import illegal_state_error


class ResolvedRole(NamedTuple):
    definition: RoleDefinitionInput
    revision_no: int


class ResolvedPolicy(NamedTuple):
    definition: PolicyDefinitionInput
    revision_no: int


async def resolve_role(
    session: AsyncSession,
    role_key: str,
    *,
    node_kind: NodeKind,
    node_key: str,
) -> ResolvedRole:
    try:
        resolved_role = await load_current_role(session, role_key)
    except ValueError as exc:
        raise illegal_state_error(str(exc)) from exc
    if node_kind not in resolved_role.definition.allowed_node_kinds:
        raise illegal_state_error(
            f"role '{role_key}' is incompatible with node kind '{node_kind}' for node '{node_key}'"
        )
    return ResolvedRole(resolved_role.definition, resolved_role.revision_no)


async def resolve_policy(
    session: AsyncSession,
    policy_key: str,
    *,
    node_kind: NodeKind,
    node_key: str,
) -> ResolvedPolicy:
    try:
        resolved_policy = await load_current_policy(session, policy_key)
    except ValueError as exc:
        raise illegal_state_error(str(exc)) from exc
    if node_kind not in resolved_policy.definition.applies_to:
        raise illegal_state_error(
            f"policy '{policy_key}' is incompatible with node kind '{node_kind}' for node "
            f"'{node_key}'"
        )
    return ResolvedPolicy(resolved_policy.definition, resolved_policy.revision_no)
