from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.contracts.registry import (
    CapabilityDecision as AuthoredCapabilityDecision,
)
from autoclaw.definitions.contracts.registry import (
    PolicyDefinitionInput,
)
from autoclaw.persistence.models import FlowNodeModel, PolicyRevisionModel
from autoclaw.runtime.contracts import (
    CapabilityDecision,
    CapabilityExecutionScope,
    CapabilityRejectionError,
    EffectiveCapabilitySet,
    HumanRequestCapabilitySet,
    HumanRequestKind,
)
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState

HUMAN_REQUEST_DENIED_NEXT_LEGAL_ACTION = None
COMMAND_RUN_DENIED_NEXT_LEGAL_ACTION = (
    "avoid long command; for example, run focused tests one by one rather than the whole test suite"
)


async def resolve_effective_capabilities(
    session: AsyncSession,
    *,
    state: CurrentRuntimeState,
    execution_scope: CapabilityExecutionScope = "dispatch",
) -> EffectiveCapabilitySet:
    return await resolve_effective_capabilities_for_node(
        session,
        node=state.current_node,
        execution_scope=execution_scope,
    )


async def resolve_effective_capabilities_for_node(
    session: AsyncSession,
    *,
    node: FlowNodeModel,
    execution_scope: CapabilityExecutionScope = "dispatch",
) -> EffectiveCapabilitySet:
    policy_content = await _pinned_policy_content(session, node=node)
    return resolve_effective_capabilities_from_policy_content(
        policy_content,
        execution_scope=execution_scope,
    )


def resolve_effective_capabilities_from_policy_content(
    policy_content: Mapping[str, object] | PolicyDefinitionInput | None,
    *,
    execution_scope: CapabilityExecutionScope = "dispatch",
) -> EffectiveCapabilitySet:
    if policy_content is None:
        return denied_effective_capabilities(execution_scope=execution_scope)

    policy = (
        policy_content
        if isinstance(policy_content, PolicyDefinitionInput)
        else PolicyDefinitionInput.model_validate(policy_content)
    )
    human_request = _resolve_human_request_capabilities(policy)
    command_run = (
        CapabilityDecision.ALLOW
        if policy.capabilities.command_run == AuthoredCapabilityDecision.ALLOW
        else CapabilityDecision.DENY
    )
    return EffectiveCapabilitySet(
        execution_scope=execution_scope,
        human_request=human_request,
        command_run=command_run,
    )


def denied_effective_capabilities(
    *,
    execution_scope: CapabilityExecutionScope = "dispatch",
) -> EffectiveCapabilitySet:
    return EffectiveCapabilitySet(execution_scope=execution_scope)


def capability_rejection_for_human_request(
    capabilities: EffectiveCapabilitySet,
    request_kind: HumanRequestKind | str,
) -> CapabilityRejectionError | None:
    normalized_kind = _human_request_kind(request_kind)
    decision = getattr(capabilities.human_request, normalized_kind.value)
    if decision == CapabilityDecision.ALLOW:
        return None
    capability = f"human_request.{normalized_kind.value}"
    return CapabilityRejectionError(
        capability=capability,
        message=f"current node policy does not allow {capability} from this node",
        next_legal_action=HUMAN_REQUEST_DENIED_NEXT_LEGAL_ACTION,
    )


def capability_rejection_for_command_run(
    capabilities: EffectiveCapabilitySet,
) -> CapabilityRejectionError | None:
    if capabilities.command_run == CapabilityDecision.ALLOW:
        return None
    return CapabilityRejectionError(
        capability="command_run",
        message=(
            "current node policy does not allow controller-managed command_run from this node"
        ),
        next_legal_action=COMMAND_RUN_DENIED_NEXT_LEGAL_ACTION,
    )


def _resolve_human_request_capabilities(
    policy: PolicyDefinitionInput,
) -> HumanRequestCapabilitySet:
    if policy.capabilities.human_request.mode != AuthoredCapabilityDecision.ALLOW:
        return HumanRequestCapabilitySet()

    allowed_kinds = {
        HumanRequestKind(kind.value) for kind in policy.capabilities.human_request.allowed_kinds
    }
    return HumanRequestCapabilitySet(
        direction=_human_request_decision(HumanRequestKind.DIRECTION, allowed_kinds),
        approval=_human_request_decision(HumanRequestKind.APPROVAL, allowed_kinds),
        input=_human_request_decision(HumanRequestKind.INPUT, allowed_kinds),
        review=_human_request_decision(HumanRequestKind.REVIEW, allowed_kinds),
    )


def _human_request_decision(
    request_kind: HumanRequestKind,
    allowed_kinds: set[HumanRequestKind],
) -> CapabilityDecision:
    if request_kind in allowed_kinds:
        return CapabilityDecision.ALLOW
    return CapabilityDecision.DENY


def _human_request_kind(request_kind: HumanRequestKind | str) -> HumanRequestKind:
    if isinstance(request_kind, HumanRequestKind):
        return request_kind
    return HumanRequestKind(request_kind)


async def _pinned_policy_content(
    session: AsyncSession,
    *,
    node: FlowNodeModel,
) -> Mapping[str, object] | None:
    if node.policy_key is None or node.policy_revision_no is None:
        return None
    revision = await session.scalar(
        select(PolicyRevisionModel).where(
            PolicyRevisionModel.policy_key == node.policy_key,
            PolicyRevisionModel.revision_no == node.policy_revision_no,
        )
    )
    if revision is None:
        return None
    return revision.content_json


__all__ = [
    "COMMAND_RUN_DENIED_NEXT_LEGAL_ACTION",
    "HUMAN_REQUEST_DENIED_NEXT_LEGAL_ACTION",
    "capability_rejection_for_command_run",
    "capability_rejection_for_human_request",
    "denied_effective_capabilities",
    "resolve_effective_capabilities",
    "resolve_effective_capabilities_for_node",
    "resolve_effective_capabilities_from_policy_content",
]
