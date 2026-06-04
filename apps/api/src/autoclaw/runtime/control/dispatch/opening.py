"""Explicit Phase 6 bridge for the legacy dispatch-opening owner."""

from __future__ import annotations

from app.runtime.control.dispatch import opening as legacy_dispatch_opening

activate_dispatch_turn = legacy_dispatch_opening.activate_dispatch_turn
link_previous_dispatch_opening = legacy_dispatch_opening.link_previous_dispatch_opening
prepare_dispatch_turn = legacy_dispatch_opening.prepare_dispatch_turn

__all__ = [
    "activate_dispatch_turn",
    "link_previous_dispatch_opening",
    "prepare_dispatch_turn",
]
