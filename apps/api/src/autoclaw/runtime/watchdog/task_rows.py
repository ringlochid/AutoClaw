from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AttemptCheckpointModel,
    AttemptModel,
    CommandRunModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
    PendingHumanRequestModel,
    ProviderEventRecordModel,
)
from autoclaw.runtime.contracts import FlowStatus
from autoclaw.runtime.watchdog.classification import (
    PROVIDER_PROGRESS_EVENT_KINDS,
    TERMINAL_PROVIDER_DELIVERY_STATUSES,
    WatchdogContext,
)


@dataclass(frozen=True)
class WatchdogTaskRows:
    dispatches_by_id: dict[str, DispatchTurnModel]
    watchdog_states_by_id: dict[str, DispatchWatchdogStateModel]
    delivery_states_by_id: dict[str, DispatchDeliveryStateModel]
    continuity_states_by_id: dict[str, DispatchContinuityStateModel]
    latest_checkpoints_by_dispatch_id: dict[str, AttemptCheckpointModel]
    dispatch_ids_with_provider_progress_event: frozenset[str]
    dispatch_ids_with_external_wait_source: frozenset[str]


def build_watchdog_context(
    flow: FlowModel,
    dispatch_id: str,
    task_rows: WatchdogTaskRows,
) -> WatchdogContext | None:
    dispatch = task_rows.dispatches_by_id.get(dispatch_id)
    watchdog_state = task_rows.watchdog_states_by_id.get(dispatch_id)
    if dispatch is None or watchdog_state is None:
        return None
    return WatchdogContext(
        flow=flow,
        dispatch=dispatch,
        delivery_state=task_rows.delivery_states_by_id.get(dispatch_id),
        continuity_state=task_rows.continuity_states_by_id.get(dispatch_id),
        watchdog_state=watchdog_state,
        latest_checkpoint=task_rows.latest_checkpoints_by_dispatch_id.get(dispatch_id),
        has_provider_progress_event=dispatch_id
        in task_rows.dispatch_ids_with_provider_progress_event,
        has_external_wait_source=dispatch_id in task_rows.dispatch_ids_with_external_wait_source,
    )


async def load_watchdog_task_rows(
    session: AsyncSession,
    *,
    flow: FlowModel,
    candidate_dispatch_ids: tuple[str, ...],
) -> WatchdogTaskRows:
    if not candidate_dispatch_ids:
        return WatchdogTaskRows(
            dispatches_by_id={},
            watchdog_states_by_id={},
            delivery_states_by_id={},
            continuity_states_by_id={},
            latest_checkpoints_by_dispatch_id={},
            dispatch_ids_with_provider_progress_event=frozenset(),
            dispatch_ids_with_external_wait_source=frozenset(),
        )

    dispatches_by_id = await _load_dispatch_rows_by_id(session, candidate_dispatch_ids)
    watchdog_states_by_id = await _load_watchdog_rows_by_id(session, candidate_dispatch_ids)

    live_delivery_dispatch_ids = tuple(
        dispatch_id
        for dispatch_id, dispatch in dispatches_by_id.items()
        if _needs_live_delivery_state(flow, dispatch)
    )
    delivery_states_by_id = await _load_delivery_state_rows_by_id(
        session,
        live_delivery_dispatch_ids,
    )

    ambiguous_dispatch_ids = tuple(
        dispatch_id
        for dispatch_id, dispatch in dispatches_by_id.items()
        if dispatch.control_state == "ambiguous"
    )
    continuity_states_by_id = await _load_continuity_state_rows_by_id(
        session,
        ambiguous_dispatch_ids,
    )

    latest_checkpoints_by_dispatch_id = await _load_latest_checkpoints_by_dispatch_id(
        session,
        flow=flow,
        dispatches_by_id=dispatches_by_id,
    )
    dispatch_ids_with_provider_progress_event = await _load_provider_progress_dispatch_ids(
        session,
        flow=flow,
        dispatches_by_id=dispatches_by_id,
        latest_checkpoints_by_dispatch_id=latest_checkpoints_by_dispatch_id,
    )
    dispatch_ids_with_external_wait_source = await _load_external_wait_source_dispatch_ids(
        session,
        candidate_dispatch_ids,
    )

    return WatchdogTaskRows(
        dispatches_by_id=dispatches_by_id,
        watchdog_states_by_id=watchdog_states_by_id,
        delivery_states_by_id=delivery_states_by_id,
        continuity_states_by_id=continuity_states_by_id,
        latest_checkpoints_by_dispatch_id=latest_checkpoints_by_dispatch_id,
        dispatch_ids_with_provider_progress_event=dispatch_ids_with_provider_progress_event,
        dispatch_ids_with_external_wait_source=dispatch_ids_with_external_wait_source,
    )


def _needs_live_delivery_state(
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> bool:
    return (
        flow.status == FlowStatus.RUNNING.value
        and flow.current_open_dispatch_id == dispatch.dispatch_id
        and dispatch.control_state == "live"
        and dispatch.accepted_boundary is None
    )


def _needs_terminal_provider_context(
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> bool:
    return (
        flow.status == FlowStatus.RUNNING.value
        and dispatch.delivery_status in TERMINAL_PROVIDER_DELIVERY_STATUSES
        and dispatch.superseded_by_dispatch_id is None
        and dispatch.accepted_boundary is None
    )


async def _load_dispatch_rows_by_id(
    session: AsyncSession,
    dispatch_ids: tuple[str, ...],
) -> dict[str, DispatchTurnModel]:
    if not dispatch_ids:
        return {}
    dispatches = await session.scalars(
        select(DispatchTurnModel).where(DispatchTurnModel.dispatch_id.in_(dispatch_ids))
    )
    return {dispatch.dispatch_id: dispatch for dispatch in dispatches}


async def _load_watchdog_rows_by_id(
    session: AsyncSession,
    dispatch_ids: tuple[str, ...],
) -> dict[str, DispatchWatchdogStateModel]:
    if not dispatch_ids:
        return {}
    watchdog_rows = await session.scalars(
        select(DispatchWatchdogStateModel).where(
            DispatchWatchdogStateModel.dispatch_id.in_(dispatch_ids)
        )
    )
    return {row.dispatch_id: row for row in watchdog_rows}


async def _load_delivery_state_rows_by_id(
    session: AsyncSession,
    dispatch_ids: tuple[str, ...],
) -> dict[str, DispatchDeliveryStateModel]:
    if not dispatch_ids:
        return {}
    delivery_states = await session.scalars(
        select(DispatchDeliveryStateModel).where(
            DispatchDeliveryStateModel.dispatch_id.in_(dispatch_ids)
        )
    )
    return {row.dispatch_id: row for row in delivery_states}


async def _load_continuity_state_rows_by_id(
    session: AsyncSession,
    dispatch_ids: tuple[str, ...],
) -> dict[str, DispatchContinuityStateModel]:
    if not dispatch_ids:
        return {}
    continuity_states = await session.scalars(
        select(DispatchContinuityStateModel).where(
            DispatchContinuityStateModel.dispatch_id.in_(dispatch_ids)
        )
    )
    return {row.dispatch_id: row for row in continuity_states}


async def _load_latest_checkpoints_by_dispatch_id(
    session: AsyncSession,
    *,
    flow: FlowModel,
    dispatches_by_id: dict[str, DispatchTurnModel],
) -> dict[str, AttemptCheckpointModel]:
    terminal_dispatches = [
        dispatch
        for dispatch in dispatches_by_id.values()
        if _needs_terminal_provider_context(flow, dispatch)
    ]
    attempt_ids = {
        dispatch.attempt_id for dispatch in terminal_dispatches if dispatch.attempt_id is not None
    }
    if not attempt_ids:
        return {}

    attempts = await session.scalars(
        select(AttemptModel).where(AttemptModel.attempt_id.in_(attempt_ids))
    )
    attempts_by_id = {attempt.attempt_id: attempt for attempt in attempts}
    checkpoint_ids = {
        attempt.latest_checkpoint_id
        for attempt in attempts_by_id.values()
        if attempt.latest_checkpoint_id is not None
    }
    checkpoints_by_id: dict[str, AttemptCheckpointModel] = {}
    if checkpoint_ids:
        checkpoints = await session.scalars(
            select(AttemptCheckpointModel).where(
                AttemptCheckpointModel.checkpoint_id.in_(checkpoint_ids)
            )
        )
        checkpoints_by_id = {checkpoint.checkpoint_id: checkpoint for checkpoint in checkpoints}

    latest_checkpoints_by_dispatch_id: dict[str, AttemptCheckpointModel] = {}
    for dispatch in terminal_dispatches:
        if dispatch.attempt_id is None:
            continue
        attempt = attempts_by_id.get(dispatch.attempt_id)
        if attempt is None or attempt.latest_checkpoint_id is None:
            continue
        checkpoint = checkpoints_by_id.get(attempt.latest_checkpoint_id)
        if checkpoint is not None:
            latest_checkpoints_by_dispatch_id[dispatch.dispatch_id] = checkpoint
    return latest_checkpoints_by_dispatch_id


async def _load_provider_progress_dispatch_ids(
    session: AsyncSession,
    *,
    flow: FlowModel,
    dispatches_by_id: dict[str, DispatchTurnModel],
    latest_checkpoints_by_dispatch_id: dict[str, AttemptCheckpointModel],
) -> frozenset[str]:
    terminal_dispatch_ids = tuple(
        dispatch_id
        for dispatch_id, dispatch in dispatches_by_id.items()
        if _needs_terminal_provider_context(flow, dispatch)
        and dispatch_id not in latest_checkpoints_by_dispatch_id
    )
    if not terminal_dispatch_ids:
        return frozenset()
    matching_dispatch_ids = await session.scalars(
        select(ProviderEventRecordModel.dispatch_id)
        .where(
            ProviderEventRecordModel.dispatch_id.in_(terminal_dispatch_ids),
            ProviderEventRecordModel.event_kind.in_(tuple(PROVIDER_PROGRESS_EVENT_KINDS)),
        )
        .distinct()
    )
    return frozenset(str(dispatch_id) for dispatch_id in matching_dispatch_ids)


async def _load_external_wait_source_dispatch_ids(
    session: AsyncSession,
    dispatch_ids: tuple[str, ...],
) -> frozenset[str]:
    if not dispatch_ids:
        return frozenset()
    human_request_dispatch_ids = set(
        str(dispatch_id)
        for dispatch_id in await session.scalars(
            select(PendingHumanRequestModel.dispatch_id)
            .where(PendingHumanRequestModel.dispatch_id.in_(dispatch_ids))
            .distinct()
        )
    )
    command_run_dispatch_ids = set(
        str(dispatch_id)
        for dispatch_id in await session.scalars(
            select(CommandRunModel.dispatch_id)
            .where(CommandRunModel.dispatch_id.in_(dispatch_ids))
            .distinct()
        )
    )
    return frozenset(human_request_dispatch_ids | command_run_dispatch_ids)
