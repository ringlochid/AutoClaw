"""Explicit Phase 6 bridge for the legacy provider-events owner."""

from __future__ import annotations

from app.runtime.control.dispatch import provider_events as legacy_provider_events

append_provider_event = legacy_provider_events.append_provider_event

__all__ = ["append_provider_event"]
