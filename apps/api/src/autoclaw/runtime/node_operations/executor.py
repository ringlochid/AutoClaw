from __future__ import annotations

import logging
from collections.abc import Mapping

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.session import get_session_factory
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.dispatch.authority import (
    NodeOperationAuthority,
    claim_exact_node_operation_transition,
    read_node_operation_authority,
    refresh_node_activity,
)
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.node_operations.activity import (
    NodeActivitySignal,
    NodeActivitySignalPublisher,
)
from autoclaw.runtime.node_operations.catalog import (
    get_node_operation_descriptor,
    list_node_operation_descriptors_for_kind,
)
from autoclaw.runtime.node_operations.contracts import (
    NodeOperationCapability,
    NodeOperationDescriptor,
    NodeOperationName,
    NodeOperationScope,
    OpenHumanRequestRequest,
)
from autoclaw.runtime.node_operations.core_handlers import execute_core_node_operation
from autoclaw.runtime.node_operations.state_legality import (
    node_operation_requires_transition_claim,
    read_node_operation_state_token,
    require_state_legal_node_operation,
)

logger = logging.getLogger(__name__)


class NodeOperationExecutor:
    def __init__(
        self,
        *,
        publish_activity_signal: NodeActivitySignalPublisher | None = None,
    ) -> None:
        self._publish_activity_signal = publish_activity_signal

    async def list_operations(
        self,
        scope: NodeOperationScope,
    ) -> tuple[NodeOperationDescriptor, ...]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            authority = await read_node_operation_authority(session, scope)
            return tuple(
                descriptor
                for descriptor in list_node_operation_descriptors_for_kind(authority.node_kind)
                if _capability_allows(descriptor, authority, None)
            )

    async def execute(
        self,
        *,
        scope: NodeOperationScope,
        operation_name: str | NodeOperationName,
        arguments: Mapping[str, object],
    ) -> BaseModel:
        descriptor, request = _resolve_node_operation_request(operation_name, arguments)
        occurred_at = utc_now()
        session_factory = get_session_factory()
        async with session_factory() as admission_session:
            authority = await read_node_operation_authority(admission_session, scope)
            _authorize(descriptor, authority, request)
            activity = await refresh_node_activity(
                admission_session,
                authority,
                occurred_at=occurred_at,
            )
            await admission_session.commit()

        await self._publish_activity(
            NodeActivitySignal(
                task_id=scope.task_id,
                dispatch_id=scope.dispatch_id,
                activity_revision=activity.activity_revision,
                occurred_at=activity.occurred_at,
            )
        )

        async with session_factory() as operation_session:
            authority = await read_node_operation_authority(operation_session, scope)
            _authorize(descriptor, authority, request)
            authority = await _claim_unchanged_node_operation_state(
                operation_session,
                scope=scope,
                descriptor=descriptor,
                request=request,
                authority=authority,
            )
            await require_state_legal_node_operation(
                operation_session,
                authority,
                descriptor.name,
            )
            result = await execute_core_node_operation(
                operation_session,
                authority,
                descriptor.name,
                request,
            )
            if result is None:
                from autoclaw.runtime.node_operations.domain_handlers import (
                    execute_controller_node_operation,
                )

                result = await execute_controller_node_operation(
                    operation_session,
                    authority,
                    descriptor.name,
                    request,
                )
            if not isinstance(result, descriptor.success_model):
                result = descriptor.success_model.model_validate(result)
            return result

    async def _publish_activity(self, signal: NodeActivitySignal) -> None:
        if self._publish_activity_signal is None:
            return
        try:
            await self._publish_activity_signal(signal)
        except Exception:
            logger.exception(
                "failed to publish Node activity scheduling hint",
                extra={
                    "task_id": signal.task_id,
                    "dispatch_id": signal.dispatch_id,
                    "activity_revision": signal.activity_revision,
                },
            )


def _resolve_node_operation_request(
    operation_name: str | NodeOperationName,
    arguments: Mapping[str, object],
) -> tuple[NodeOperationDescriptor, BaseModel]:
    try:
        descriptor = get_node_operation_descriptor(operation_name)
    except (KeyError, ValueError) as exc:
        raise RuntimeOperationError(
            code=OperationFailureCode.INVALID_REQUEST_SHAPE,
            summary=f"unknown Node operation '{operation_name}'",
            is_retryable=False,
        ) from exc
    return descriptor, descriptor.request_model.model_validate(dict(arguments))


async def _claim_unchanged_node_operation_state(
    session: AsyncSession,
    *,
    scope: NodeOperationScope,
    descriptor: NodeOperationDescriptor,
    request: BaseModel,
    authority: NodeOperationAuthority,
) -> NodeOperationAuthority:
    if not node_operation_requires_transition_claim(descriptor.name):
        return authority

    state_token = await read_node_operation_state_token(session, authority)
    await claim_exact_node_operation_transition(session, authority)
    current_state_token = await read_node_operation_state_token(session, authority)
    if current_state_token != state_token:
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICT,
            summary="another Node operation changed exact dispatch state",
            is_retryable=False,
        )
    current_authority = await read_node_operation_authority(session, scope)
    _authorize(descriptor, current_authority, request)
    return current_authority


def _authorize(
    descriptor: NodeOperationDescriptor,
    authority: NodeOperationAuthority,
    request: BaseModel,
) -> None:
    if authority.node_kind not in descriptor.allowed_node_kinds:
        raise RuntimeOperationError(
            code=OperationFailureCode.ILLEGAL_CALLER,
            summary=f"{authority.node_kind.value} cannot call {descriptor.name.value}",
            is_retryable=False,
        )
    if not _capability_allows(descriptor, authority, request):
        raise RuntimeOperationError(
            code=OperationFailureCode.CAPABILITY_REJECTED,
            summary=f"current capability denies {descriptor.name.value}",
            is_retryable=False,
        )


def _capability_allows(
    descriptor: NodeOperationDescriptor,
    authority: NodeOperationAuthority,
    request: BaseModel | None,
) -> bool:
    if descriptor.required_capability == NodeOperationCapability.COMMAND_RUN:
        return authority.capabilities.command_run == "allow"
    if descriptor.required_capability != NodeOperationCapability.HUMAN_REQUEST:
        return True
    if request is None:
        return any(
            decision == "allow"
            for decision in (
                authority.capabilities.human_direction,
                authority.capabilities.human_approval,
                authority.capabilities.human_input,
                authority.capabilities.human_review,
            )
        )
    assert isinstance(request, OpenHumanRequestRequest)
    decisions = {
        "direction": authority.capabilities.human_direction,
        "approval": authority.capabilities.human_approval,
        "input": authority.capabilities.human_input,
        "review": authority.capabilities.human_review,
    }
    return decisions[request.request.kind.value] == "allow"


__all__ = ["NodeOperationExecutor"]
