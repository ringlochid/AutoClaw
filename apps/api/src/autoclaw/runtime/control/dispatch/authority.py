"""Explicit Phase 6 bridge for the legacy dispatch-authority owner."""

from __future__ import annotations

from app.runtime.control.dispatch import authority as legacy_dispatch_authority

NodeSessionAuthority = legacy_dispatch_authority.NodeSessionAuthority
validate_node_session_key = legacy_dispatch_authority.validate_node_session_key

__all__ = ["NodeSessionAuthority", "validate_node_session_key"]
