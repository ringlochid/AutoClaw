"""Temporary Phase 6 shim for the legacy registry seed owner."""

from __future__ import annotations

from app.registry.seeds import PACKAGED_SEED_DEFINITIONS_ROOT, seed_definition_registry

__all__ = ["PACKAGED_SEED_DEFINITIONS_ROOT", "seed_definition_registry"]
