"""Explicit Phase 6 bridge for the legacy dispatch-control module owner."""

from __future__ import annotations

from app.runtime.control.dispatch import control as legacy_dispatch_control

INACTIVITY_PROVEN_DELIVERY_STATUSES = legacy_dispatch_control.INACTIVITY_PROVEN_DELIVERY_STATUSES
REPLACEMENT_BLOCKING_CONTROL_STATES = legacy_dispatch_control.REPLACEMENT_BLOCKING_CONTROL_STATES
WAITING_INACTIVITY_CONTROL_STATES = legacy_dispatch_control.WAITING_INACTIVITY_CONTROL_STATES
dispatch_deadline_expired = legacy_dispatch_control.dispatch_deadline_expired
dispatch_inactivity_proven = legacy_dispatch_control.dispatch_inactivity_proven
dispatch_waiting_for_inactivity = legacy_dispatch_control.dispatch_waiting_for_inactivity
fence_foreground_dispatch = legacy_dispatch_control.fence_foreground_dispatch
mark_dispatch_ambiguous = legacy_dispatch_control.mark_dispatch_ambiguous
mark_dispatch_fenced = legacy_dispatch_control.mark_dispatch_fenced
open_dispatch_for_attempt = legacy_dispatch_control.open_dispatch_for_attempt
resolve_foreground_dispatch_gate = legacy_dispatch_control.resolve_foreground_dispatch_gate
stage_previous_dispatch_outputs = legacy_dispatch_control.stage_previous_dispatch_outputs

__all__ = [
    "INACTIVITY_PROVEN_DELIVERY_STATUSES",
    "REPLACEMENT_BLOCKING_CONTROL_STATES",
    "WAITING_INACTIVITY_CONTROL_STATES",
    "dispatch_deadline_expired",
    "dispatch_inactivity_proven",
    "dispatch_waiting_for_inactivity",
    "fence_foreground_dispatch",
    "mark_dispatch_ambiguous",
    "mark_dispatch_fenced",
    "open_dispatch_for_attempt",
    "resolve_foreground_dispatch_gate",
    "stage_previous_dispatch_outputs",
]
