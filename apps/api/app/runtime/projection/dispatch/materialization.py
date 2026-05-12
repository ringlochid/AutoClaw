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
from app.runtime.contracts import TaskRootPaths
from app.runtime.projection.dispatch.prompt import build_dispatch_prompt
from app.runtime.task_root import (
    continuity_state_json_path,
    delivery_state_json_path,
    load_task_root_paths,
    prompt_markdown_path,
    prompt_request_json_path,
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


async def _persist_prompt_artifact_if_missing(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    paths = await load_task_root_paths(session, task_id)
    prompt_path = prompt_markdown_path(paths=paths, dispatch_id=dispatch.dispatch_id)
    prompt_request_path = prompt_request_json_path(paths=paths, dispatch_id=dispatch.dispatch_id)
    if prompt_path.exists() and prompt_request_path.exists():
        return
    bundle, prompt_record = await build_dispatch_prompt(session, task_id, dispatch)
    write_prompt_artifact(
        paths=paths,
        prompt_record=prompt_record,
        full_markdown=bundle.full_markdown,
    )


def _write_delivery_state_file(
    *,
    paths: TaskRootPaths,
    delivery_state: DispatchDeliveryStateModel,
) -> None:
    write_json_file(
        delivery_state_json_path(paths=paths, dispatch_id=delivery_state.dispatch_id),
        {
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
        },
    )


def _write_continuity_state_file(
    *,
    paths: TaskRootPaths,
    continuity_state: DispatchContinuityStateModel,
) -> None:
    write_json_file(
        continuity_state_json_path(paths=paths, dispatch_id=continuity_state.dispatch_id),
        {
            "dispatch_id": continuity_state.dispatch_id,
            "attempt_id": continuity_state.attempt_id,
            "assignment_key": continuity_state.assignment_key,
            "node_key": continuity_state.node_key,
            "continuity_state": continuity_state.continuity_state,
            "previous_response_id": continuity_state.previous_response_id,
            "session_key_present": continuity_state.session_key_present,
            "invalidation_reason": continuity_state.invalidation_reason,
            "updated_at": continuity_state.updated_at.isoformat(),
        },
    )


def _write_watchdog_state_file(
    *,
    paths: TaskRootPaths,
    watchdog_state: DispatchWatchdogStateModel,
) -> None:
    write_json_file(
        watchdog_state_json_path(paths=paths, dispatch_id=watchdog_state.dispatch_id),
        {
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
        },
    )


async def materialize_dispatch_files(session: AsyncSession, task_id: str, dispatch_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    if dispatch is None:
        raise ValueError(f"missing dispatch '{dispatch_id}'")
    await _persist_prompt_artifact_if_missing(session, task_id=task_id, dispatch=dispatch)
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
    if delivery_state is not None:
        _write_delivery_state_file(paths=paths, delivery_state=delivery_state)
    if continuity_state is not None:
        _write_continuity_state_file(paths=paths, continuity_state=continuity_state)
    if watchdog_state is not None:
        _write_watchdog_state_file(paths=paths, watchdog_state=watchdog_state)
    write_ndjson_file(
        provider_events_ndjson_path(paths=paths, dispatch_id=dispatch_id),
        [_project_provider_event(row) for row in provider_events],
    )
