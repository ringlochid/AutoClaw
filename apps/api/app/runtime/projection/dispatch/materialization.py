from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    ProviderEventRecordModel,
)
from app.runtime.contracts import PersistedPromptRecord, TaskRootPaths
from app.runtime.control.failures import missing_resource_error
from app.runtime.projection.dispatch.prompt import build_dispatch_prompt
from app.runtime.task_root import (
    continuity_state_json_path,
    delivery_state_json_path,
    load_task_root_paths,
    provider_events_ndjson_path,
    watchdog_state_json_path,
    write_json_file,
    write_ndjson_file,
    write_prompt_artifact,
)


def _project_provider_event(row: ProviderEventRecordModel) -> dict[str, object | None]:
    return {
        "event_no": row.event_no,
        "dispatch_id": row.dispatch_id,
        "attempt_id": row.attempt_id,
        "event_source": row.event_source,
        "event_kind": row.event_kind,
        "provider_event_name": row.provider_event_name,
        "summary": row.summary,
        "observed_at": row.occurred_at.isoformat(),
        "provider_occurred_at": (
            row.provider_occurred_at.isoformat() if row.provider_occurred_at is not None else None
        ),
        "detail": row.detail,
    }


def _delivery_state_payload(
    delivery_state: DispatchDeliveryStateModel,
) -> dict[str, object]:
    return {
        "dispatch_id": delivery_state.dispatch_id,
        "attempt_id": delivery_state.attempt_id,
        "assignment_key": delivery_state.assignment_key,
        "node_key": delivery_state.node_key,
        "transport_family": delivery_state.transport_family,
        "transport_state": delivery_state.transport_state,
        "controller_observation_state": delivery_state.controller_observation_state,
        "last_provider_event_kind": delivery_state.last_provider_event_kind,
        "provider_final_status": delivery_state.provider_final_status,
        "provider_error": delivery_state.provider_error,
        "send_mode": delivery_state.send_mode,
        "previous_dispatch_id": delivery_state.previous_dispatch_id,
        "superseded_by_dispatch_id": delivery_state.superseded_by_dispatch_id,
        "prepared_at": delivery_state.prepared_at.isoformat(),
        "accepted_at": (
            delivery_state.accepted_at.isoformat()
            if delivery_state.accepted_at is not None
            else None
        ),
        "last_provider_signal_at": (
            delivery_state.last_provider_signal_at.isoformat()
            if delivery_state.last_provider_signal_at is not None
            else None
        ),
        "last_controller_progress_at": (
            delivery_state.last_controller_progress_at.isoformat()
            if delivery_state.last_controller_progress_at is not None
            else None
        ),
        "last_controller_terminal_at": (
            delivery_state.last_controller_terminal_at.isoformat()
            if delivery_state.last_controller_terminal_at is not None
            else None
        ),
        "updated_at": delivery_state.updated_at.isoformat(),
    }


def _continuity_state_payload(
    continuity_state: DispatchContinuityStateModel,
) -> dict[str, object]:
    return {
        "dispatch_id": continuity_state.dispatch_id,
        "attempt_id": continuity_state.attempt_id,
        "assignment_key": continuity_state.assignment_key,
        "node_key": continuity_state.node_key,
        "continuity_state": continuity_state.continuity_state,
        "previous_response_id": continuity_state.previous_response_id,
        "session_key_present": continuity_state.session_key_present,
        "invalidation_reason": continuity_state.invalidation_reason,
        "updated_at": continuity_state.updated_at.isoformat(),
    }


def _watchdog_state_payload(
    watchdog_state: DispatchWatchdogStateModel,
) -> dict[str, object]:
    return {
        "dispatch_id": watchdog_state.dispatch_id,
        "attempt_id": watchdog_state.attempt_id,
        "assignment_key": watchdog_state.assignment_key,
        "node_key": watchdog_state.node_key,
        "watchdog_state": watchdog_state.watchdog_state,
        "current_watchdog_kind": watchdog_state.current_watchdog_kind,
        "current_watchdog_reason": watchdog_state.current_watchdog_reason,
        "recovery_action": watchdog_state.recovery_action,
        "recovery_reason": watchdog_state.recovery_reason,
        "recovery_dispatch_id": watchdog_state.recovery_dispatch_id,
        "previous_dispatch_id": watchdog_state.previous_dispatch_id,
        "superseded_by_dispatch_id": watchdog_state.superseded_by_dispatch_id,
        "classified_at": watchdog_state.classified_at.isoformat(),
        "updated_at": watchdog_state.updated_at.isoformat(),
    }


def write_dispatch_projection_files(
    *,
    paths: TaskRootPaths,
    prompt_record: PersistedPromptRecord,
    full_markdown: str,
    delivery_state_payload: dict[str, object] | None = None,
    continuity_state_payload: dict[str, object] | None = None,
    watchdog_state_payload: dict[str, object] | None = None,
    provider_events: list[dict[str, object | None]] | None = None,
) -> None:
    write_prompt_artifact(
        paths=paths,
        prompt_record=prompt_record,
        full_markdown=full_markdown,
    )
    if delivery_state_payload is not None:
        write_json_file(
            delivery_state_json_path(paths=paths, dispatch_id=str(prompt_record.dispatch_id)),
            delivery_state_payload,
        )
    if continuity_state_payload is not None:
        write_json_file(
            continuity_state_json_path(paths=paths, dispatch_id=str(prompt_record.dispatch_id)),
            continuity_state_payload,
        )
    if watchdog_state_payload is not None:
        write_json_file(
            watchdog_state_json_path(paths=paths, dispatch_id=str(prompt_record.dispatch_id)),
            watchdog_state_payload,
        )
    write_ndjson_file(
        provider_events_ndjson_path(paths=paths, dispatch_id=str(prompt_record.dispatch_id)),
        provider_events or [],
    )


async def materialize_dispatch_files(session: AsyncSession, task_id: str, dispatch_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    if dispatch is None:
        raise missing_resource_error(f"missing dispatch '{dispatch_id}'")
    bundle, prompt_record = await build_dispatch_prompt(session, task_id, dispatch)
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
    watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
    provider_events = list(
        await session.scalars(
            select(ProviderEventRecordModel)
            .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
            .order_by(
                ProviderEventRecordModel.event_no.asc(),
                ProviderEventRecordModel.occurred_at.asc(),
            )
        )
    )
    write_dispatch_projection_files(
        paths=paths,
        prompt_record=prompt_record,
        full_markdown=bundle.full_markdown,
        delivery_state_payload=(
            _delivery_state_payload(delivery_state) if delivery_state is not None else None
        ),
        continuity_state_payload=(
            _continuity_state_payload(continuity_state) if continuity_state is not None else None
        ),
        watchdog_state_payload=(
            _watchdog_state_payload(watchdog_state) if watchdog_state is not None else None
        ),
        provider_events=[_project_provider_event(row) for row in provider_events],
    )
