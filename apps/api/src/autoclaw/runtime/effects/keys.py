from __future__ import annotations

from pathlib import Path
from typing import Literal

RuntimeEffectKind = Literal[
    "artifact_current_pointer_materialization",
    "attempt_materialization",
    "dispatch_materialization",
    "file_copy",
    "manifest_materialization",
]
type RuntimeEffectKey = tuple[str, ...]

_EFFECT_PRIORITIES: dict[RuntimeEffectKind, int] = {
    "file_copy": 10,
    "manifest_materialization": 20,
    "dispatch_materialization": 30,
    "artifact_current_pointer_materialization": 40,
    "attempt_materialization": 50,
}


def effect_priority(effect_kind: RuntimeEffectKind) -> int:
    return _EFFECT_PRIORITIES[effect_kind]


def file_copy_effect_key(destination: Path) -> RuntimeEffectKey:
    return ("copy-file", str(destination))


def attempt_materialization_effect_key(task_id: str, attempt_id: str) -> RuntimeEffectKey:
    return ("materialize-attempt", task_id, attempt_id)


def manifest_materialization_effect_key(task_id: str) -> RuntimeEffectKey:
    return ("materialize-manifest", task_id)


def dispatch_materialization_effect_key(task_id: str, dispatch_id: str) -> RuntimeEffectKey:
    return ("materialize-dispatch", task_id, dispatch_id)


def artifact_current_pointer_effect_key(
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> RuntimeEffectKey:
    return ("materialize-artifact-current", task_id, owner_node_key, slot)


__all__ = [
    "RuntimeEffectKey",
    "RuntimeEffectKind",
    "artifact_current_pointer_effect_key",
    "attempt_materialization_effect_key",
    "dispatch_materialization_effect_key",
    "effect_priority",
    "file_copy_effect_key",
    "manifest_materialization_effect_key",
]
