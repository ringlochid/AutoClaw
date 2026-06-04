"""Temporary Phase 6 shims for the legacy runtime manifest projection owners."""

from __future__ import annotations

from app.runtime.projection.manifest import (
    build_current_structural_edit_palette,
    build_dispatch_manifest_projection,
    build_manifest_projection,
    build_manifest_projection_for_state,
    materialize_artifact_current_pointer,
    materialize_manifest,
    write_manifest_projection_files,
)

__all__ = [
    "build_current_structural_edit_palette",
    "build_dispatch_manifest_projection",
    "build_manifest_projection",
    "build_manifest_projection_for_state",
    "materialize_artifact_current_pointer",
    "materialize_manifest",
    "write_manifest_projection_files",
]
