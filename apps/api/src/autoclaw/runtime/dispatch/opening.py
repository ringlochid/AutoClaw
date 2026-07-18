from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    DispatchCapabilitySetModel,
    DispatchPromptRefsModel,
    DispatchTurnModel,
)
from autoclaw.runtime.contracts.provider_resolution import (
    ClaudeProviderRoute,
    CodexProviderRoute,
    OpenClawProviderRoute,
)
from autoclaw.runtime.dispatch.preparation import PreparedDispatchRequest


@dataclass(frozen=True, slots=True)
class StartingDispatchBasis:
    task_id: str
    flow_id: str
    assignment_id: str
    attempt_id: str
    node_key: str
    opened_reason: str
    predecessor_dispatch_id: str | None
    flow_start_source_flow_id: str | None


def stage_starting_dispatch(
    session: AsyncSession,
    *,
    basis: StartingDispatchBasis,
    prepared: PreparedDispatchRequest,
) -> None:
    route = prepared.provider.route
    model_override: str | None = None
    effort_override: str | None = None
    gateway_profile: str | None = None
    match route:
        case CodexProviderRoute() | ClaudeProviderRoute():
            model_override = route.model_override
            effort_override = route.effort_override
        case OpenClawProviderRoute():
            gateway_profile = route.gateway_profile

    session.add(
        DispatchTurnModel(
            dispatch_id=prepared.dispatch_id,
            task_id=basis.task_id,
            flow_id=basis.flow_id,
            assignment_id=basis.assignment_id,
            attempt_id=basis.attempt_id,
            node_key=basis.node_key,
            flow_start_source_flow_id=basis.flow_start_source_flow_id,
            predecessor_dispatch_id=basis.predecessor_dispatch_id,
            status="starting",
            opened_reason=basis.opened_reason,
            requested_provider=prepared.provider.requested_provider.value,
            resolved_provider=prepared.provider.resolved_provider.value,
            provider_selection_basis=prepared.provider.selection_basis.value,
            provider_route_kind=route.kind.value,
            model_override=model_override,
            effort_override=effort_override,
            gateway_profile=gateway_profile,
            provider_start_revision=0,
            provider_start_attempt_count=0,
            next_provider_start_at=prepared.due_at,
            provider_start_retry_kind="initial",
            provider_start_last_error_code=None,
            created_at=prepared.due_at,
            adapter_started_at=None,
            last_node_activity_at=None,
            node_activity_revision=0,
            closed_at=None,
            closed_reason=None,
        )
    )
    session.add(
        DispatchPromptRefsModel(
            dispatch_id=prepared.dispatch_id,
            instructions_logical_path=prepared.refs.instructions_logical_path,
            input_logical_path=prepared.refs.input_logical_path,
            dynamic_input_version=1,
            created_at=prepared.due_at,
        )
    )
    capabilities = prepared.capabilities
    session.add(
        DispatchCapabilitySetModel(
            dispatch_id=prepared.dispatch_id,
            provider_native_access=capabilities.provider_native_access.effective.value,
            provider_native_access_source=capabilities.provider_native_access.source.value,
            network_access=capabilities.network_access.effective.value,
            network_access_source=capabilities.network_access.source.value,
            human_direction=capabilities.human_request.direction.value,
            human_approval=capabilities.human_request.approval.value,
            human_input=capabilities.human_request.input.value,
            human_review=capabilities.human_request.review.value,
            command_run=capabilities.command_run.value,
            created_at=prepared.due_at,
        )
    )


__all__ = ["StartingDispatchBasis", "stage_starting_dispatch"]
