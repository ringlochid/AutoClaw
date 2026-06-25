from __future__ import annotations

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    DispatchTurnModel,
    FlowModel,
    FlowWaitStateModel,
    PendingHumanRequestModel,
)
from autoclaw.runtime.capabilities import (
    capability_rejection_for_human_request,
    resolve_effective_capabilities,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    HumanRequestItem,
    HumanRequestItemResponse,
    HumanRequestListResponse,
    HumanRequestOpenRequest,
    HumanRequestOpenResponse,
    HumanRequestRead,
    HumanRequestResolution,
    HumanRequestResolutionKind,
    HumanRequestResolveRequest,
    HumanRequestResolveResponse,
    HumanRequestStatus,
    HumanRequestTimeout,
    OperationFailureCode,
    PendingHumanRequest,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from autoclaw.runtime.dispatch.control import fence_foreground_dispatch
from autoclaw.runtime.errors import (
    RuntimeOperationError,
    illegal_state_error,
    invalid_request_shape_error,
)
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.ids import human_request_id
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState
from autoclaw.runtime.task_events import append_task_event

_CONTROL_API_ACTOR_REF = "control_api"
_HUMAN_REQUEST_CONFLICT_NEXT_STEP = (
    "Reread the current human-request list for this task before retrying the resolution."
)


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
    pending_request = PendingHumanRequestModel(
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
    session.add(pending_request)
    await session.flush((pending_request,))

    session.add(
        FlowWaitStateModel(
            flow_id=state.flow.flow_id,
            task_id=task_id,
            waiting_cause=WaitingCause.WAITING_FOR_HUMAN_REQUEST.value,
            pending_human_request_id=request_id,
            created_by_dispatch_id=dispatch.dispatch_id,
            created_at=opened_at,
            updated_at=opened_at,
        )
    )
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
        items=tuple(_human_request_read_from_model(row) for row in rows),
    )


async def resolve_human_request(
    session: AsyncSession,
    *,
    task_id: str,
    request_id: str,
    request: HumanRequestResolveRequest,
) -> HumanRequestResolveResponse:
    flow = await require_flow_for_task(session, task_id)
    pending_request = await _human_request_for_task(
        session,
        task_id=task_id,
        request_id=request_id,
    )
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    _ensure_request_can_be_resolved(
        flow=flow,
        pending_request=pending_request,
        wait_state=wait_state,
        request_id=request_id,
    )
    assert pending_request is not None
    assert wait_state is not None

    _validate_answered_item_responses(pending_request, request.item_responses)
    resolved_at = utc_now()
    item_responses_json = [response.model_dump(mode="json") for response in request.item_responses]

    pending_request.status = HumanRequestStatus.RESOLVED.value
    pending_request.resolution_kind = HumanRequestResolutionKind.ANSWERED.value
    pending_request.item_responses_json = item_responses_json
    pending_request.resolved_at = resolved_at
    pending_request.resolved_by_actor_ref = _CONTROL_API_ACTOR_REF
    pending_request.updated_at = resolved_at

    await session.delete(wait_state)
    flow.updated_at = resolved_at
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.HUMAN_REQUEST_RESOLVED,
        event_source=TaskEventSource.CONTROL_API,
        occurred_at=resolved_at,
        flow_revision_id=pending_request.flow_revision_id,
        dispatch_id=pending_request.dispatch_id,
        attempt_id=pending_request.attempt_id,
        node_key=pending_request.requester_node_key,
        actor_ref=_CONTROL_API_ACTOR_REF,
        payload={
            "request_id": request_id,
            "status": HumanRequestStatus.RESOLVED.value,
            "resolution_kind": HumanRequestResolutionKind.ANSWERED.value,
        },
    )
    await session.flush()
    resolution = _human_request_resolution_from_model(pending_request)
    assert resolution is not None
    return HumanRequestResolveResponse(task_id=task_id, resolution=resolution)


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


async def _human_request_for_task(
    session: AsyncSession,
    *,
    task_id: str,
    request_id: str,
) -> PendingHumanRequestModel | None:
    return cast(
        PendingHumanRequestModel | None,
        await session.scalar(
            select(PendingHumanRequestModel).where(
                PendingHumanRequestModel.task_id == task_id,
                PendingHumanRequestModel.request_id == request_id,
            )
        ),
    )


def _ensure_request_can_be_resolved(
    *,
    flow: FlowModel,
    pending_request: PendingHumanRequestModel | None,
    wait_state: FlowWaitStateModel | None,
    request_id: str,
) -> None:
    if pending_request is None:
        raise _human_request_conflict(f"human request '{request_id}' is not current")
    if pending_request.status != HumanRequestStatus.OPEN.value:
        raise _human_request_conflict(f"human request '{request_id}' is already terminal")
    if (
        wait_state is None
        or wait_state.flow_id != flow.flow_id
        or wait_state.waiting_cause != WaitingCause.WAITING_FOR_HUMAN_REQUEST.value
        or wait_state.pending_human_request_id != pending_request.request_id
    ):
        raise _human_request_conflict(
            f"human request '{request_id}' no longer owns the active human wait"
        )


def _human_request_conflict(summary: str) -> RuntimeOperationError:
    return RuntimeOperationError(
        code=OperationFailureCode.ILLEGAL_STATE,
        summary=summary,
        is_retryable=False,
        suggested_next_step=_HUMAN_REQUEST_CONFLICT_NEXT_STEP,
        status_code_override=409,
    )


def _validate_answered_item_responses(
    pending_request: PendingHumanRequestModel,
    item_responses: tuple[HumanRequestItemResponse, ...],
) -> None:
    request_items = tuple(
        HumanRequestItem.model_validate(item) for item in pending_request.items_json
    )
    request_item_ids = {item.item_id for item in request_items}
    response_item_ids = [response.item_id for response in item_responses]
    if len(response_item_ids) != len(set(response_item_ids)):
        raise invalid_request_shape_error("human request resolution item responses must be unique")
    if set(response_item_ids) != request_item_ids:
        raise invalid_request_shape_error(
            "human request resolution must answer every request item exactly once"
        )

    request_items_by_id = {item.item_id: item for item in request_items}
    for item_response in item_responses:
        _validate_answered_item_response(
            request_items_by_id[item_response.item_id],
            item_response,
        )


def _validate_answered_item_response(
    request_item: HumanRequestItem,
    item_response: HumanRequestItemResponse,
) -> None:
    if request_item.options:
        _validate_option_item_response(request_item, item_response)
        return
    if item_response.selected_option is not None:
        raise invalid_request_shape_error(
            f"selected_option is invalid for human request item '{request_item.item_id}'"
        )
    if item_response.freeform_answer is None and item_response.response_payload is None:
        raise invalid_request_shape_error(
            f"human request item '{request_item.item_id}' requires an answer"
        )


def _validate_option_item_response(
    request_item: HumanRequestItem,
    item_response: HumanRequestItemResponse,
) -> None:
    has_selected_option = item_response.selected_option is not None
    has_freeform_answer = item_response.freeform_answer is not None
    if has_selected_option == has_freeform_answer:
        raise invalid_request_shape_error(
            f"human request item '{request_item.item_id}' requires one answer"
        )
    if item_response.response_payload is not None:
        raise invalid_request_shape_error(
            f"response_payload is invalid for human request item '{request_item.item_id}'"
        )
    if item_response.selected_option is None:
        return
    option_ids = {option.id for option in request_item.options}
    if item_response.selected_option not in option_ids:
        raise invalid_request_shape_error(
            f"selected_option is not valid for human request item '{request_item.item_id}'"
        )


def _human_request_read_from_model(row: PendingHumanRequestModel) -> HumanRequestRead:
    return HumanRequestRead(
        request=_pending_human_request_from_model(row),
        resolution=_human_request_resolution_from_model(row),
    )


def _pending_human_request_from_model(row: PendingHumanRequestModel) -> PendingHumanRequest:
    return PendingHumanRequest(
        request_id=row.request_id,
        task_id=row.task_id,
        title=row.title,
        summary=row.summary,
        kind=row.kind,
        requester_node=row.requester_node_key,
        items=tuple(HumanRequestItem.model_validate(item) for item in row.items_json),
        timeout=HumanRequestTimeout.model_validate(row.timeout_json),
        suggested_human_instruction=row.suggested_human_instruction,
        opened_at=coerce_datetime_to_utc(row.opened_at),
        status=row.status,
    )


def _human_request_resolution_from_model(
    row: PendingHumanRequestModel,
) -> HumanRequestResolution | None:
    if row.status == HumanRequestStatus.OPEN.value:
        return None
    if row.resolution_kind is None or row.resolved_at is None:
        raise illegal_state_error(
            f"terminal human request '{row.request_id}' is missing resolution"
        )
    return HumanRequestResolution(
        request_id=row.request_id,
        task_id=row.task_id,
        resolution_kind=row.resolution_kind,
        item_responses=tuple(
            HumanRequestItemResponse.model_validate(response)
            for response in (row.item_responses_json or [])
        ),
        resolved_at=coerce_datetime_to_utc(row.resolved_at),
        resolved_by_actor_ref=row.resolved_by_actor_ref,
    )


__all__ = ["list_human_requests", "open_human_request", "resolve_human_request"]
