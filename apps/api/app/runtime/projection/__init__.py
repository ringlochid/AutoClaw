from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

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

_EXPORTS: dict[str, tuple[str, str]] = {
    "CurrentRuntimeState": (
        "app.runtime.projection.runtime_state",
        "CurrentRuntimeState",
    ),
    "build_dispatch_prompt": (
        "app.runtime.projection.dispatch.prompt",
        "build_dispatch_prompt",
    ),
    "build_manifest_projection": (
        "app.runtime.projection.manifest.projection",
        "build_manifest_projection",
    ),
    "current_runtime_state": (
        "app.runtime.projection.runtime_state",
        "current_runtime_state",
    ),
    "load_task_root_paths": (
        "app.runtime.task_root.reads",
        "load_task_root_paths",
    ),
    "materialize_artifact_current_pointer": (
        "app.runtime.projection.manifest.materialization",
        "materialize_artifact_current_pointer",
    ),
    "materialize_attempt_files": (
        "app.runtime.projection.attempt_materialization",
        "materialize_attempt_files",
    ),
    "materialize_dispatch_files": (
        "app.runtime.projection.dispatch.materialization",
        "materialize_dispatch_files",
    ),
    "materialize_manifest": (
        "app.runtime.projection.manifest.materialization",
        "materialize_manifest",
    ),
    "render_dispatch_prompt": (
        "app.runtime.projection.dispatch.prompt",
        "render_dispatch_prompt",
    ),
}

if TYPE_CHECKING:
    from app.runtime.projection.attempt_materialization import materialize_attempt_files
    from app.runtime.projection.dispatch.materialization import (
        materialize_dispatch_files,
    )
    from app.runtime.projection.dispatch.prompt import (
        build_dispatch_prompt,
        render_dispatch_prompt,
    )
    from app.runtime.projection.manifest.materialization import (
        materialize_artifact_current_pointer,
        materialize_manifest,
    )
    from app.runtime.projection.manifest.projection import build_manifest_projection
    from app.runtime.projection.runtime_state import (
        CurrentRuntimeState,
        current_runtime_state,
    )
    from app.runtime.task_root.reads import load_task_root_paths


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
