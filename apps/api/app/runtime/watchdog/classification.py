from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.config import RuntimeSettings
from app.db.models import (
    AttemptCheckpointModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
)
from app.runtime.contracts import FlowStatus
from app.runtime.control.clock import utc_now

TERMINAL_PROVIDER_DELIVERY_STATUSES = frozenset({"provider_completed", "provider_failed"})
WATCHDOG_CLASSIFIED_STATE = "classified"


@dataclass(frozen=True)
class WatchdogContext:
    flow: FlowModel
    dispatch: DispatchTurnModel
    delivery_state: DispatchDeliveryStateModel | None
    watchdog_state: DispatchWatchdogStateModel
    latest_checkpoint: AttemptCheckpointModel | None


@dataclass(frozen=True)
class WatchdogClassification:
    watchdog_state: str
    current_watchdog_kind: str
    current_watchdog_reason: str
    recovery_action: str
    recovery_reason: str


def classify_watchdog(
    context: WatchdogContext,
    *,
    settings: RuntimeSettings,
) -> WatchdogClassification | None:
    dispatch = context.dispatch
    if dispatch.superseded_by_dispatch_id is not None:
        return None
    if (existing_recovery := _preserve_existing_recovery_classification(context)) is not None:
        return existing_recovery
    if _watchdog_must_skip_foreground_owned_slot(context):
        return None
    if dispatch.control_state == "ambiguous":
        return _ambiguous_dispatch_classification(dispatch)
    if _is_terminal_provider_without_checkpoint(context):
        return _terminal_provider_without_checkpoint_classification(dispatch)
    if not _watchdog_may_classify_live_dispatch(context):
        return None
    if _bootstrap_timeout_reached(context, settings=settings):
        return _bootstrap_timeout_classification(
            dispatch=dispatch,
            bootstrap_deadline=settings.watchdog_bootstrap_ack_timeout_seconds,
        )
    if _execution_deadline_reached(context, settings=settings):
        return _execution_stale_classification(
            execution_deadline=settings.watchdog_execution_stale_after_seconds
        )
    return None


def recovery_execution_needed(
    context: WatchdogContext,
    classification: WatchdogClassification,
) -> bool:
    if classification.recovery_action == "escalate":
        return False
    if context.watchdog_state.recovery_dispatch_id is not None:
        return False
    return context.dispatch.superseded_by_dispatch_id is None


def _ambiguous_dispatch_classification(
    dispatch: DispatchTurnModel,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="ambiguity.escalation_required",
        current_watchdog_reason=(
            dispatch.control_state_reason or "dispatch became ambiguous before inactivity proof"
        ),
        recovery_action="escalate",
        recovery_reason="safe automatic recovery cannot be proven for an ambiguous dispatch",
    )


def _terminal_provider_without_checkpoint_classification(
    dispatch: DispatchTurnModel,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="execution_running.terminal_provider_without_controller_checkpoint",
        current_watchdog_reason=(
            "provider reported terminal completion without a checkpoint recorded after "
            f"dispatch {dispatch.dispatch_id} opened"
        ),
        recovery_action="create_new_attempt",
        recovery_reason="the current attempt lineage is no longer trustworthy",
    )


def _bootstrap_timeout_classification(
    *,
    dispatch: DispatchTurnModel,
    bootstrap_deadline: int,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="bootstrap_pending_callback.bootstrap_callback_timeout",
        current_watchdog_reason=(
            f"no checkpoint was recorded within {bootstrap_deadline}s of dispatch acceptance"
        ),
        recovery_action="redispatch_same_attempt",
        recovery_reason="the same attempt is still current and can be retried safely",
    )


def _execution_stale_classification(
    *,
    execution_deadline: int,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="execution_running.execution_stale",
        current_watchdog_reason=(
            "no controller-observed progress arrived within "
            f"{execution_deadline}s of the latest progress marker"
        ),
        recovery_action="redispatch_same_attempt",
        recovery_reason="the same attempt remains current and the dispatch slot can be retried",
    )


def _bootstrap_timeout_reached(
    context: WatchdogContext,
    *,
    settings: RuntimeSettings,
) -> bool:
    return (
        not _has_dispatch_progress_since_open(context)
        and _checkpoint_since_dispatch(context) is None
        and _seconds_since(_bootstrap_anchor(context))
        >= settings.watchdog_bootstrap_ack_timeout_seconds
    )


def _execution_deadline_reached(
    context: WatchdogContext,
    *,
    settings: RuntimeSettings,
) -> bool:
    return (
        _seconds_since(_progress_anchor(context)) >= settings.watchdog_execution_stale_after_seconds
    )


def _has_dispatch_progress_since_open(context: WatchdogContext) -> bool:
    delivery_state = context.delivery_state
    checkpoint = _checkpoint_since_dispatch(context)
    return checkpoint is not None or (
        delivery_state is not None
        and (
            delivery_state.last_controller_progress_at is not None
            or delivery_state.last_provider_signal_at is not None
        )
    )


def _watchdog_may_classify_live_dispatch(context: WatchdogContext) -> bool:
    dispatch = context.dispatch
    flow = context.flow
    if flow.status != FlowStatus.RUNNING.value:
        return False
    if flow.current_open_dispatch_id != dispatch.dispatch_id:
        return False
    if dispatch.control_state in {"launching", "abort_requested"}:
        return False
    if dispatch.control_state != "live":
        return False
    if dispatch.accepted_boundary is not None:
        return False
    return True


def _watchdog_must_skip_foreground_owned_slot(context: WatchdogContext) -> bool:
    dispatch = context.dispatch
    flow = context.flow
    if dispatch.control_state == "launching":
        return True
    if dispatch.control_state == "abort_requested":
        return not (
            flow.current_open_dispatch_id is None
            and dispatch.delivery_status in TERMINAL_PROVIDER_DELIVERY_STATUSES
        )
    return (
        flow.current_open_dispatch_id == dispatch.dispatch_id
        and dispatch.control_state == "live"
        and dispatch.accepted_boundary is not None
    )


def _is_terminal_provider_without_checkpoint(context: WatchdogContext) -> bool:
    dispatch = context.dispatch
    if context.flow.status != FlowStatus.RUNNING.value:
        return False
    if dispatch.delivery_status not in TERMINAL_PROVIDER_DELIVERY_STATUSES:
        return False
    if dispatch.superseded_by_dispatch_id is not None:
        return False
    if dispatch.accepted_boundary is not None:
        return False
    return _checkpoint_since_dispatch(context) is None


def _checkpoint_since_dispatch(context: WatchdogContext) -> AttemptCheckpointModel | None:
    checkpoint = context.latest_checkpoint
    if checkpoint is None:
        return None
    if _as_utc(checkpoint.recorded_at) < _as_utc(context.dispatch.rendered_at):
        return None
    return checkpoint


def _bootstrap_anchor(context: WatchdogContext) -> datetime:
    delivery_state = context.delivery_state
    if delivery_state is not None and delivery_state.accepted_at is not None:
        return _as_utc(delivery_state.accepted_at)
    return _as_utc(context.dispatch.rendered_at)


def _progress_anchor(context: WatchdogContext) -> datetime:
    anchors = [_bootstrap_anchor(context)]
    delivery_state = context.delivery_state
    checkpoint = _checkpoint_since_dispatch(context)
    if delivery_state is not None and delivery_state.last_controller_progress_at is not None:
        anchors.append(_as_utc(delivery_state.last_controller_progress_at))
    if checkpoint is not None:
        anchors.append(_as_utc(checkpoint.recorded_at))
    return max(anchors)


def _seconds_since(instant: datetime) -> int:
    return int((utc_now() - instant).total_seconds())


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _preserve_existing_recovery_classification(
    context: WatchdogContext,
) -> WatchdogClassification | None:
    row = context.watchdog_state
    dispatch = context.dispatch
    if dispatch.control_state == "ambiguous":
        return None
    if row.watchdog_state != WATCHDOG_CLASSIFIED_STATE:
        return None
    if row.recovery_dispatch_id is not None:
        return None
    if row.recovery_action not in {"redispatch_same_attempt", "create_new_attempt"}:
        return None
    if (
        row.current_watchdog_kind is None
        or row.current_watchdog_reason is None
        or row.recovery_reason is None
    ):
        return None
    if dispatch.control_state not in {"abort_requested", "fenced"}:
        return None
    reason = dispatch.control_state_reason or ""
    if not reason.startswith("watchdog:"):
        return None
    return WatchdogClassification(
        watchdog_state=row.watchdog_state,
        current_watchdog_kind=row.current_watchdog_kind,
        current_watchdog_reason=row.current_watchdog_reason,
        recovery_action=row.recovery_action,
        recovery_reason=row.recovery_reason,
    )


__all__ = [
    "TERMINAL_PROVIDER_DELIVERY_STATUSES",
    "WatchdogClassification",
    "WatchdogContext",
    "classify_watchdog",
    "recovery_execution_needed",
]
