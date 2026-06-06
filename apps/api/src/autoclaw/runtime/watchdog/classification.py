from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from autoclaw.config import RuntimeSettings
from autoclaw.persistence.models import (
    AttemptCheckpointModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import FlowStatus

TERMINAL_PROVIDER_DELIVERY_STATUSES = frozenset({"provider_completed", "provider_failed"})
PROVIDER_PROGRESS_EVENT_KINDS = frozenset({"first_data", "output_delta"})
WATCHDOG_CLASSIFIED_STATE = "classified"


@dataclass(frozen=True)
class WatchdogContext:
    flow: FlowModel
    dispatch: DispatchTurnModel
    delivery_state: DispatchDeliveryStateModel | None
    continuity_state: DispatchContinuityStateModel | None
    watchdog_state: DispatchWatchdogStateModel
    latest_checkpoint: AttemptCheckpointModel | None
    has_provider_progress_event: bool


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
    if _delivery_path_rebound_detected(context):
        return _delivery_path_rebound_classification(context)
    if _is_terminal_provider_without_checkpoint(context):
        if _terminal_provider_without_first_callback(context):
            return _terminal_provider_without_first_callback_classification(dispatch)
        return _terminal_provider_without_checkpoint_classification(dispatch)
    if not _watchdog_may_classify_live_dispatch(context):
        return None
    if _bootstrap_timeout_reached(context, settings=settings):
        return _same_attempt_recovery_classification(
            current_watchdog_kind="bootstrap_pending_callback.bootstrap_callback_timeout",
            current_watchdog_reason=(
                "no committed provider or controller progress arrived within "
                f"{settings.watchdog_bootstrap_first_progress_timeout_seconds}s "
                "of the first-progress anchor"
            ),
            recovery_reason="the same attempt is still current and can be retried safely",
        )
    if _execution_deadline_reached(context, settings=settings):
        return _same_attempt_recovery_classification(
            current_watchdog_kind="execution_running.execution_stale",
            current_watchdog_reason=(
                "no controller-observed progress arrived within "
                f"{settings.watchdog_execution_stale_after_seconds}s of the latest progress marker"
            ),
            recovery_reason=(
                "the same attempt remains current and the dispatch slot can be retried"
            ),
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


def enforce_same_attempt_recovery_cap(
    classification: WatchdogClassification,
    *,
    same_attempt_recovery_count: int,
    settings: RuntimeSettings,
) -> WatchdogClassification:
    if classification.recovery_action != "redispatch_same_attempt":
        return classification

    limit = settings.watchdog_same_attempt_redispatch_limit
    if limit < 0 or same_attempt_recovery_count < limit:
        return classification

    return WatchdogClassification(
        watchdog_state=classification.watchdog_state,
        current_watchdog_kind=classification.current_watchdog_kind,
        current_watchdog_reason=classification.current_watchdog_reason,
        recovery_action="escalate",
        recovery_reason=(
            "controller-owned same-attempt watchdog redispatch cap "
            f"({settings.watchdog_same_attempt_redispatch_limit}) exhausted"
        ),
    )


def _terminal_provider_without_checkpoint_classification(
    dispatch: DispatchTurnModel,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="execution_running.terminal_provider_without_controller_checkpoint",
        current_watchdog_reason=(
            "provider reached terminal completion without a controller checkpoint after "
            f"dispatch {dispatch.dispatch_id} showed execution progress"
        ),
        recovery_action="escalate",
        recovery_reason="the current attempt lineage is no longer trustworthy",
    )


def _terminal_provider_without_first_callback_classification(
    dispatch: DispatchTurnModel,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="bootstrap_pending_callback.terminal_provider_without_first_callback",
        current_watchdog_reason=(
            "provider reached terminal completion before the first provider or controller "
            f"progress was recorded for dispatch {dispatch.dispatch_id}"
        ),
        recovery_action="escalate",
        recovery_reason="the current attempt lineage is no longer trustworthy",
    )


def _delivery_path_rebound_classification(
    context: WatchdogContext,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind="execution_running.delivery_path_rebound",
        current_watchdog_reason=_delivery_path_rebound_reason(context),
        recovery_action="escalate",
        recovery_reason="safe automatic recovery cannot be proven for the current delivery path",
    )


def _same_attempt_recovery_classification(
    *,
    current_watchdog_kind: str,
    current_watchdog_reason: str,
    recovery_reason: str,
) -> WatchdogClassification:
    return WatchdogClassification(
        watchdog_state=WATCHDOG_CLASSIFIED_STATE,
        current_watchdog_kind=current_watchdog_kind,
        current_watchdog_reason=current_watchdog_reason,
        recovery_action="redispatch_same_attempt",
        recovery_reason=recovery_reason,
    )


def _bootstrap_timeout_reached(
    context: WatchdogContext,
    *,
    settings: RuntimeSettings,
) -> bool:
    return (
        not _has_committed_dispatch_progress(context)
        and _seconds_since(_bootstrap_anchor(context))
        >= settings.watchdog_bootstrap_first_progress_timeout_seconds
    )


def _execution_deadline_reached(
    context: WatchdogContext,
    *,
    settings: RuntimeSettings,
) -> bool:
    return (
        _seconds_since(_progress_anchor(context)) >= settings.watchdog_execution_stale_after_seconds
    )


def _has_committed_dispatch_progress(context: WatchdogContext) -> bool:
    delivery_state = context.delivery_state
    return delivery_state is not None and (
        delivery_state.last_controller_progress_at is not None
        or delivery_state.last_provider_signal_at is not None
        or delivery_state.last_controller_terminal_at is not None
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


def _terminal_provider_without_first_callback(context: WatchdogContext) -> bool:
    return not context.has_provider_progress_event


def _delivery_path_rebound_detected(context: WatchdogContext) -> bool:
    return context.dispatch.control_state == "ambiguous"


def _delivery_path_rebound_reason(context: WatchdogContext) -> str:
    continuity_state = context.continuity_state
    if continuity_state is not None and continuity_state.invalidation_reason is not None:
        return continuity_state.invalidation_reason
    if context.dispatch.control_state_reason is not None:
        return context.dispatch.control_state_reason
    return "controller observed a rebound or ambiguous delivery path before safe recovery"


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
    if delivery_state is not None and delivery_state.last_controller_progress_at is not None:
        anchors.append(_as_utc(delivery_state.last_controller_progress_at))
    if delivery_state is not None and delivery_state.last_provider_signal_at is not None:
        anchors.append(_as_utc(delivery_state.last_provider_signal_at))
    if delivery_state is not None and delivery_state.last_controller_terminal_at is not None:
        anchors.append(_as_utc(delivery_state.last_controller_terminal_at))
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
    if row.recovery_action != "redispatch_same_attempt":
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
    "PROVIDER_PROGRESS_EVENT_KINDS",
    "TERMINAL_PROVIDER_DELIVERY_STATUSES",
    "WatchdogClassification",
    "WatchdogContext",
    "classify_watchdog",
    "enforce_same_attempt_recovery_cap",
    "recovery_execution_needed",
]
