"""Temporary Phase 6 shims for the legacy runtime projection owners."""

from __future__ import annotations

from app.runtime.projection import (
    CurrentRuntimeState,
    build_dispatch_prompt,
    build_manifest_projection,
    current_runtime_state,
    load_task_root_paths,
    materialize_artifact_current_pointer,
    materialize_attempt_files,
    materialize_dispatch_files,
    materialize_manifest,
    render_dispatch_prompt,
)

__all__ = [
    "CurrentRuntimeState",
    "build_dispatch_prompt",
    "build_manifest_projection",
    "current_runtime_state",
    "load_task_root_paths",
    "materialize_artifact_current_pointer",
    "materialize_attempt_files",
    "materialize_dispatch_files",
    "materialize_manifest",
    "render_dispatch_prompt",
]
