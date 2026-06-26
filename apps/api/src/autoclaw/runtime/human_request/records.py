from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from jsonschema import (  # type: ignore[import-untyped]
    Draft202012Validator,
    SchemaError,
)
from jsonschema import (
    ValidationError as JsonSchemaValidationError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import FlowModel, FlowWaitStateModel, PendingHumanRequestModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    HumanRequestItem,
    HumanRequestItemResponse,
    HumanRequestKind,
    HumanRequestRead,
    HumanRequestResolution,
    HumanRequestResolutionKind,
    HumanRequestResolutionSurface,
    HumanRequestStatus,
    HumanRequestTimeout,
    OperationFailureCode,
    PendingHumanRequest,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from autoclaw.runtime.errors import (
    RuntimeOperationError,
    illegal_state_error,
    invalid_request_shape_error,
)
from autoclaw.runtime.task_events import append_task_event

_CONTROLLER_ACTOR_REF = "controller"
_HUMAN_REQUEST_CONFLICT_NEXT_STEP = (
    "Reread the current human-request list for this task before retrying the resolution."
)
_HUMAN_REQUEST_STATUS_BY_RESOLUTION = {
    HumanRequestResolutionKind.ANSWERED: HumanRequestStatus.RESOLVED,
    HumanRequestResolutionKind.TIMED_OUT: HumanRequestStatus.TIMED_OUT,
    HumanRequestResolutionKind.CANCELLED: HumanRequestStatus.CANCELLED,
}
_HUMAN_REQUEST_EVENT_TYPE_BY_RESOLUTION = {
    HumanRequestResolutionKind.ANSWERED: TaskEventType.HUMAN_REQUEST_RESOLVED,
    HumanRequestResolutionKind.TIMED_OUT: TaskEventType.HUMAN_REQUEST_TIMED_OUT,
    HumanRequestResolutionKind.CANCELLED: TaskEventType.HUMAN_REQUEST_CANCELLED,
}


async def reconcile_timed_out_human_request_wait(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> bool:
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    if (
        wait_state is None
        or wait_state.waiting_cause != WaitingCause.WAITING_FOR_HUMAN_REQUEST.value
        or wait_state.pending_human_request_id is None
    ):
        return False

    pending_request = await _human_request_for_task(
        session,
        task_id=task_id,
        request_id=wait_state.pending_human_request_id,
    )
    if pending_request is None or pending_request.status != HumanRequestStatus.OPEN.value:
        return False

    timeout = HumanRequestTimeout.model_validate(pending_request.timeout_json)
    if timeout.due_at is None:
        return False

    due_at = _coerce_datetime_to_utc(timeout.due_at)
    terminal_commit_at = utc_now()
    if due_at > terminal_commit_at:
        return False

    await record_human_request_terminal_result(
        session,
        task_id=task_id,
        request_id=pending_request.request_id,
        resolution_kind=HumanRequestResolutionKind.TIMED_OUT,
        event_source=TaskEventSource.CONTROLLER,
        actor_ref=_CONTROLLER_ACTOR_REF,
        resolved_by_actor_ref=_CONTROLLER_ACTOR_REF,
        resolved_by_surface=HumanRequestResolutionSurface.CONTROLLER,
        policy_basis="human_request_timeout_default_behavior",
        note="human request timed out before a human answered",
        resolved_at=terminal_commit_at,
    )
    return True


async def record_human_request_terminal_result(
    session: AsyncSession,
    *,
    task_id: str,
    request_id: str,
    resolution_kind: HumanRequestResolutionKind,
    item_responses: tuple[HumanRequestItemResponse, ...] = (),
    event_source: TaskEventSource,
    actor_ref: str | None = None,
    resolved_by_actor_ref: str | None = None,
    resolved_by_surface: HumanRequestResolutionSurface,
    policy_basis: str,
    note: str | None = None,
    resolved_at: datetime | None = None,
) -> HumanRequestResolution:
    from autoclaw.runtime.flow.queries import require_flow_for_task

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

    resolved_status = _HUMAN_REQUEST_STATUS_BY_RESOLUTION[resolution_kind]
    event_type = _HUMAN_REQUEST_EVENT_TYPE_BY_RESOLUTION[resolution_kind]
    if resolution_kind == HumanRequestResolutionKind.ANSWERED:
        _validate_answered_item_responses(pending_request, item_responses)
    elif item_responses:
        raise invalid_request_shape_error("terminal non-answer human-request outcomes omit items")

    terminal_at = resolved_at or utc_now()
    item_responses_json = (
        [response.model_dump(mode="json") for response in item_responses]
        if resolution_kind == HumanRequestResolutionKind.ANSWERED
        else None
    )
    terminal_actor_ref = resolved_by_actor_ref if resolved_by_actor_ref is not None else actor_ref

    pending_request.status = resolved_status.value
    pending_request.resolution_kind = resolution_kind.value
    pending_request.item_responses_json = item_responses_json
    pending_request.resolved_at = terminal_at
    pending_request.resolved_by_actor_ref = terminal_actor_ref
    pending_request.resolved_by_surface = resolved_by_surface.value
    pending_request.resolution_policy_basis = policy_basis
    pending_request.resolution_note = note
    pending_request.updated_at = terminal_at

    await session.delete(wait_state)
    flow.updated_at = terminal_at
    await append_task_event(
        session,
        task_id=task_id,
        event_type=event_type,
        event_source=event_source,
        occurred_at=terminal_at,
        flow_revision_id=pending_request.flow_revision_id,
        dispatch_id=pending_request.dispatch_id,
        attempt_id=pending_request.attempt_id,
        node_key=pending_request.requester_node_key,
        actor_ref=actor_ref,
        payload=_human_request_terminal_event_payload(
            request_id=request_id,
            status=resolved_status,
            resolution_kind=resolution_kind,
            resolved_by_actor_ref=terminal_actor_ref,
        ),
    )
    await session.flush()
    resolution = human_request_resolution_from_model(pending_request)
    assert resolution is not None
    return resolution


def human_request_read_from_model(row: PendingHumanRequestModel) -> HumanRequestRead:
    return HumanRequestRead(
        request=pending_human_request_from_model(row),
        resolution=human_request_resolution_from_model(row),
    )


def pending_human_request_from_model(row: PendingHumanRequestModel) -> PendingHumanRequest:
    return PendingHumanRequest(
        request_id=row.request_id,
        task_id=row.task_id,
        title=row.title,
        summary=row.summary,
        kind=HumanRequestKind(row.kind),
        requester_node=row.requester_node_key,
        items=tuple(HumanRequestItem.model_validate(item) for item in row.items_json),
        timeout=HumanRequestTimeout.model_validate(row.timeout_json),
        suggested_human_instruction=row.suggested_human_instruction,
        opened_at=_coerce_datetime_to_utc(row.opened_at),
        status=HumanRequestStatus(row.status),
    )


def human_request_resolution_from_model(
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
        resolution_kind=HumanRequestResolutionKind(row.resolution_kind),
        item_responses=tuple(
            HumanRequestItemResponse.model_validate(response)
            for response in (row.item_responses_json or [])
        ),
        resolved_at=_coerce_datetime_to_utc(row.resolved_at),
        resolved_by_actor_ref=row.resolved_by_actor_ref,
    )


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
    if item_response.response_payload is not None:
        _validate_response_payload_matches_schema(request_item, item_response.response_payload)


def _validate_response_payload_matches_schema(
    request_item: HumanRequestItem,
    response_payload: dict[str, object],
) -> None:
    input_payload_schema = request_item.input_payload_schema
    if input_payload_schema is None:
        raise invalid_request_shape_error(
            f"response_payload is invalid for human request item '{request_item.item_id}'"
        )
    try:
        Draft202012Validator.check_schema(input_payload_schema)
        Draft202012Validator(input_payload_schema).validate(response_payload)
    except SchemaError as exc:
        raise invalid_request_shape_error(
            f"input_payload_schema is invalid for human request item '{request_item.item_id}'"
        ) from exc
    except JsonSchemaValidationError as exc:
        raise invalid_request_shape_error(
            "response_payload does not match input_payload_schema for human request "
            f"item '{request_item.item_id}'"
        ) from exc


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


def _human_request_terminal_event_payload(
    *,
    request_id: str,
    status: HumanRequestStatus,
    resolution_kind: HumanRequestResolutionKind,
    resolved_by_actor_ref: str | None,
) -> dict[str, str]:
    payload = {
        "request_id": request_id,
        "status": status.value,
        "resolution_kind": resolution_kind.value,
    }
    if resolved_by_actor_ref is not None:
        payload["resolved_by_actor_ref"] = resolved_by_actor_ref
    return payload


def _coerce_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "human_request_read_from_model",
    "human_request_resolution_from_model",
    "pending_human_request_from_model",
    "reconcile_timed_out_human_request_wait",
    "record_human_request_terminal_result",
]
