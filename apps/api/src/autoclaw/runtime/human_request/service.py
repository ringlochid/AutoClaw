from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    DispatchTurnModel,
    FlowWaitStateModel,
    PendingHumanRequestModel,
)
from autoclaw.runtime.capabilities import (
    capability_rejection_for_human_request,
    resolve_effective_capabilities,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    HumanRequestListResponse,
    HumanRequestOpenRequest,
    HumanRequestOpenResponse,
    HumanRequestResolutionKind,
    HumanRequestResolveRequest,
    HumanRequestResolveResponse,
    HumanRequestStatus,
    OperationFailureCode,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from autoclaw.runtime.dispatch.control import fence_foreground_dispatch
from autoclaw.runtime.errors import RuntimeOperationError, illegal_state_error
from autoclaw.runtime.human_request.records import (
    human_request_read_from_model,
    record_human_request_terminal_result,
)
from autoclaw.runtime.ids import human_request_id
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState
from autoclaw.runtime.task_events import append_task_event

_CONTROL_API_ACTOR_REF = "control_api"


async def open_human_request(
    session: AsyncSession,
    *,
    task_id: str,
    request: HumanRequestOpenRequest,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
) -> HumanRequestOpenResponse:
    capabilities = await resolve_effective_capabilities(
        session,
        state=state,
        execution_scope="human_request_open",
    )
    rejection = capability_rejection_for_human_request(capabilities, request.kind)
    if rejection is not None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CAPABILITY_REJECTED,
            summary=rejection.message,
            is_retryable=False,
            suggested_next_step=rejection.next_legal_action,
        )

    await _ensure_human_request_open_is_current(session, task_id=task_id, state=state)

    opened_at = utc_now()
    request_id = await _next_human_request_id(session, task_id=task_id)
    pending_request = _build_pending_human_request_for_open(
        task_id=task_id,
        request_id=request_id,
        request=request,
        state=state,
        dispatch=dispatch,
        opened_at=opened_at,
    )
    session.add(pending_request)
    await session.flush((pending_request,))

    session.add(
        _build_human_request_wait_state(
            task_id=task_id,
            request_id=request_id,
            state=state,
            dispatch=dispatch,
            opened_at=opened_at,
        )
    )
    await _append_human_request_opened_event(
        session,
        task_id=task_id,
        request_id=request_id,
        request=request,
        state=state,
        dispatch=dispatch,
        opened_at=opened_at,
    )
    state.flow.updated_at = opened_at
    await fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=state.flow,
        dispatch=dispatch,
        reason=f"human_request:{request_id}:opened",
    )
    await session.flush()
    return HumanRequestOpenResponse(request_id=request_id, task_id=task_id)


async def list_human_requests(
    session: AsyncSession,
    *,
    task_id: str,
) -> HumanRequestListResponse:
    from autoclaw.runtime.flow.queries import require_flow_for_task

    await require_flow_for_task(session, task_id)
    rows = list(
        await session.scalars(
            select(PendingHumanRequestModel)
            .where(PendingHumanRequestModel.task_id == task_id)
            .order_by(
                PendingHumanRequestModel.opened_at.asc(),
                PendingHumanRequestModel.request_id.asc(),
            )
        )
    )
    return HumanRequestListResponse(
        task_id=task_id,
        items=tuple(human_request_read_from_model(row) for row in rows),
    )


async def resolve_human_request(
    session: AsyncSession,
    *,
    task_id: str,
    request_id: str,
    request: HumanRequestResolveRequest,
) -> HumanRequestResolveResponse:
    resolution = await record_human_request_terminal_result(
        session,
        task_id=task_id,
        request_id=request_id,
        resolution_kind=HumanRequestResolutionKind.ANSWERED,
        item_responses=request.item_responses,
        event_source=TaskEventSource.CONTROL_API,
        actor_ref=_CONTROL_API_ACTOR_REF,
        resolved_by_actor_ref=_CONTROL_API_ACTOR_REF,
    )
    return HumanRequestResolveResponse(task_id=task_id, resolution=resolution)


def _build_pending_human_request_for_open(
    *,
    task_id: str,
    request_id: str,
    request: HumanRequestOpenRequest,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    opened_at: datetime,
) -> PendingHumanRequestModel:
    return PendingHumanRequestModel(
        request_id=request_id,
        task_id=task_id,
        flow_id=state.flow.flow_id,
        flow_revision_id=state.flow_revision.flow_revision_id,
        flow_node_id=state.current_node.flow_node_id,
        assignment_id=state.current_assignment.assignment_id,
        attempt_id=state.current_attempt.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        requester_node_key=state.current_node.node_key,
        kind=request.kind.value,
        title=request.title,
        summary=request.summary,
        items_json=[item.model_dump(mode="json") for item in request.items],
        timeout_json=request.timeout.model_dump(mode="json"),
        suggested_human_instruction=request.suggested_human_instruction,
        status=HumanRequestStatus.OPEN.value,
        opened_at=opened_at,
        updated_at=opened_at,
    )


def _build_human_request_wait_state(
    *,
    task_id: str,
    request_id: str,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    opened_at: datetime,
) -> FlowWaitStateModel:
    return FlowWaitStateModel(
        flow_id=state.flow.flow_id,
        task_id=task_id,
        waiting_cause=WaitingCause.WAITING_FOR_HUMAN_REQUEST.value,
        pending_human_request_id=request_id,
        created_by_dispatch_id=dispatch.dispatch_id,
        created_at=opened_at,
        updated_at=opened_at,
    )


async def _append_human_request_opened_event(
    session: AsyncSession,
    *,
    task_id: str,
    request_id: str,
    request: HumanRequestOpenRequest,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    opened_at: datetime,
) -> None:
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.HUMAN_REQUEST_OPENED,
        event_source=TaskEventSource.NODE,
        occurred_at=opened_at,
        flow_revision_id=state.flow_revision.flow_revision_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=state.current_attempt.attempt_id,
        node_key=state.current_node.node_key,
        payload={
            "request_id": request_id,
            "kind": request.kind.value,
            "status": HumanRequestStatus.OPEN.value,
        },
    )


async def _ensure_human_request_open_is_current(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
) -> None:
    existing_wait = await session.get(FlowWaitStateModel, state.flow.flow_id)
    if existing_wait is not None:
        raise illegal_state_error(
            f"task '{task_id}' is already waiting for {existing_wait.waiting_cause}"
        )

    existing_request = await session.scalar(
        select(PendingHumanRequestModel.request_id)
        .where(
            PendingHumanRequestModel.task_id == task_id,
            PendingHumanRequestModel.flow_id == state.flow.flow_id,
            PendingHumanRequestModel.flow_node_id == state.current_node.flow_node_id,
            PendingHumanRequestModel.assignment_id == state.current_assignment.assignment_id,
            PendingHumanRequestModel.attempt_id == state.current_attempt.attempt_id,
            PendingHumanRequestModel.status == HumanRequestStatus.OPEN.value,
        )
        .limit(1)
    )
    if existing_request is not None:
        raise illegal_state_error(
            "current node execution already owns an open pending human request"
        )


async def _next_human_request_id(session: AsyncSession, *, task_id: str) -> str:
    request_count = await session.scalar(
        select(func.count(PendingHumanRequestModel.request_id)).where(
            PendingHumanRequestModel.task_id == task_id
        )
    )
    return human_request_id(task_id, int(request_count or 0) + 1)


__all__ = ["list_human_requests", "open_human_request", "resolve_human_request"]
