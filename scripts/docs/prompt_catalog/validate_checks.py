from __future__ import annotations

from typing import Any

from .load import runtime_import_blocker_message, runtime_import_failed
from .validate_runtime_mapping import run_runtime_mapping_checks
from .validate_runtime_render import run_runtime_render_checks


def run_runtime_checks(data: dict[str, Any], errors: list[str]) -> None:
    if runtime_import_failed():
        errors.append(runtime_import_blocker_message())
        return
    run_runtime_mapping_checks(data, errors)
    run_runtime_render_checks(errors)
