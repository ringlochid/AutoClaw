from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import RuntimeSettings, get_settings
from app.db.models import (
    AttemptCheckpointModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
    ProviderEventRecordModel,
)
from app.runtime.control.clock import utc_now
from app.runtime.effects import commit_runtime_session
from app.runtime.effects.cases import stage_dispatch_open_outputs
from app.runtime.watchdog.classification import (
    TERMINAL_PROVIDER_DELIVERY_STATUSES,
    WatchdogClassification,
    WatchdogContext,
    classify_watchdog,
    recovery_execution_needed,
)
from app.runtime.watchdog.recovery import execute_watchdog_recovery


async def reconcile_watchdog_truth(
    session_factory: async_sessionmaker[AsyncSession],
) -> bool:
    settings = get_settings().runtime
    task_ids = await _candidate_task_ids(session_factory, settings=settings)
    changed = False
    remaining_auto_recoveries = (
        settings.watchdog_max_auto_recoveries_per_tick if settings.watchdog_auto_recover else 0
    )
    for task_id in task_ids:
        task_changed, remaining_auto_recoveries = await _reconcile_task_watchdog(
            session_factory,
            task_id=task_id,
            settings=settings,
            remaining_auto_recoveries=remaining_auto_recoveries,
        )
        changed = task_changed or changed
    return changed


async def _candidate_task_ids(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    settings: RuntimeSettings,
) -> tuple[str, ...]:
    async with session_factory() as session:
        flow_task_ids = set(
            await session.scalars(
                select(FlowModel.task_id).where(FlowModel.current_open_dispatch_id.is_not(None))
            )
        )
        dispatch_task_ids = set(
            await session.scalars(
                select(DispatchTurnModel.task_id).where(
                    DispatchTurnModel.superseded_by_dispatch_id.is_(None),
                    or_(
                        DispatchTurnModel.control_state == "ambiguous",
                        DispatchTurnModel.delivery_status.in_(
                            tuple(TERMINAL_PROVIDER_DELIVERY_STATUSES)
                        ),
                    ),
                )
            )
        )
    return tuple(sorted(flow_task_ids | dispatch_task_ids)[: settings.watchdog_max_flows_per_tick])


async def _reconcile_task_watchdog(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    settings: RuntimeSettings,
    remaining_auto_recoveries: int,
) -> tuple[bool, int]:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None:
            return False, remaining_auto_recoveries
        candidate_dispatch_ids = await _candidate_dispatch_ids(session, flow=flow)
        changed, recoveries_to_run, remaining_auto_recoveries = await _classify_task_dispatches(
            session,
            flow=flow,
            candidate_dispatch_ids=candidate_dispatch_ids,
            settings=settings,
            remaining_auto_recoveries=remaining_auto_recoveries,
        )
        if changed:
            await commit_runtime_session(session)
    if not changed and not recoveries_to_run:
        return False, remaining_auto_recoveries
    recovery_changed = await _execute_watchdog_recoveries(
        session_factory,
        task_id=task_id,
        recoveries_to_run=recoveries_to_run,
    )
    return changed or recovery_changed, remaining_auto_recoveries


async def _classify_task_dispatches(
    session: AsyncSession,
    *,
    flow: FlowModel,
    candidate_dispatch_ids: tuple[str, ...],
    settings: RuntimeSettings,
    remaining_auto_recoveries: int,
) -> tuple[bool, list[str], int]:
    changed = False
    recoveries_to_run: list[str] = []
    for dispatch_id in candidate_dispatch_ids:
        context = await _load_watchdog_context(session, flow=flow, dispatch_id=dispatch_id)
        if context is None:
            continue
        classification = classify_watchdog(context, settings=settings)
        changed = (
            await _apply_watchdog_classification(
                session,
                flow=flow,
                context=context,
                classification=classification,
            )
            or changed
        )
        if (
            classification is not None
            and remaining_auto_recoveries > 0
            and recovery_execution_needed(context, classification)
        ):
            recoveries_to_run.append(dispatch_id)
            remaining_auto_recoveries -= 1
    return changed, recoveries_to_run, remaining_auto_recoveries


async def _execute_watchdog_recoveries(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    recoveries_to_run: list[str],
) -> bool:
    changed = False
    for dispatch_id in recoveries_to_run:
        changed = (
            await execute_watchdog_recovery(
                session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
            )
            or changed
        )
    return changed


async def _candidate_dispatch_ids(
    session: AsyncSession,
    *,
    flow: FlowModel,
) -> tuple[str, ...]:
    dispatch_ids: list[str] = []
    if flow.current_open_dispatch_id is not None:
        dispatch_ids.append(flow.current_open_dispatch_id)
    dispatch_ids.extend(
        str(dispatch_id)
        for dispatch_id in await session.scalars(
            select(DispatchTurnModel.dispatch_id)
            .where(
                DispatchTurnModel.task_id == flow.task_id,
                DispatchTurnModel.superseded_by_dispatch_id.is_(None),
                or_(
                    DispatchTurnModel.control_state == "ambiguous",
                    DispatchTurnModel.delivery_status.in_(
                        tuple(TERMINAL_PROVIDER_DELIVERY_STATUSES)
                    ),
                ),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        )
    )
    return tuple(dict.fromkeys(dispatch_ids))


async def _load_watchdog_context(
    session: AsyncSession,
    *,
    flow: FlowModel,
    dispatch_id: str,
) -> WatchdogContext | None:
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
    if dispatch is None or watchdog_state is None:
        return None
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
    attempt = (
        None
        if dispatch.attempt_id is None
        else await session.get(AttemptModel, dispatch.attempt_id)
    )
    latest_checkpoint = (
        None
        if attempt is None or attempt.latest_checkpoint_id is None
        else await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)
    )
    provider_events = tuple(
        await session.scalars(
            select(ProviderEventRecordModel)
            .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
            .order_by(ProviderEventRecordModel.event_no.asc())
        )
    )
    return WatchdogContext(
        flow=flow,
        dispatch=dispatch,
        delivery_state=delivery_state,
        continuity_state=continuity_state,
        watchdog_state=watchdog_state,
        latest_checkpoint=latest_checkpoint,
        provider_events=provider_events,
    )


async def _apply_watchdog_classification(
    session: AsyncSession,
    *,
    flow: FlowModel,
    context: WatchdogContext,
    classification: WatchdogClassification | None,
) -> bool:
    row = context.watchdog_state
    if classification is None:
        return await _clear_watchdog_classification(session, flow=flow, context=context)
    if _classification_matches(row, classification):
        return False
    row.watchdog_state = classification.watchdog_state
    row.current_watchdog_kind = classification.current_watchdog_kind
    row.current_watchdog_reason = classification.current_watchdog_reason
    row.recovery_action = classification.recovery_action
    row.recovery_reason = classification.recovery_reason
    await _stage_watchdog_projection(
        session,
        task_id=flow.task_id,
        dispatch_id=context.dispatch.dispatch_id,
        row=row,
    )
    return True


async def _clear_watchdog_classification(
    session: AsyncSession,
    *,
    flow: FlowModel,
    context: WatchdogContext,
) -> bool:
    row = context.watchdog_state
    if (
        row.watchdog_state == "clear"
        and row.current_watchdog_kind is None
        and row.current_watchdog_reason is None
        and row.recovery_action is None
        and row.recovery_reason is None
    ):
        return False
    row.watchdog_state = "clear"
    row.current_watchdog_kind = None
    row.current_watchdog_reason = None
    row.recovery_action = None
    row.recovery_reason = None
    row.recovery_dispatch_id = None
    await _stage_watchdog_projection(
        session,
        task_id=flow.task_id,
        dispatch_id=context.dispatch.dispatch_id,
        row=row,
    )
    return True


async def _stage_watchdog_projection(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    row: DispatchWatchdogStateModel,
) -> None:
    classified_at = utc_now()
    row.classified_at = classified_at
    row.updated_at = classified_at
    stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch_id)
    await session.flush()


def _classification_matches(
    row: DispatchWatchdogStateModel,
    classification: WatchdogClassification,
) -> bool:
    return (
        row.watchdog_state == classification.watchdog_state
        and row.current_watchdog_kind == classification.current_watchdog_kind
        and row.current_watchdog_reason == classification.current_watchdog_reason
        and row.recovery_action == classification.recovery_action
        and row.recovery_reason == classification.recovery_reason
    )


__all__ = [
    "WatchdogClassification",
    "WatchdogContext",
    "reconcile_watchdog_truth",
]
