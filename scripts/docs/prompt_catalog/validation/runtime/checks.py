from __future__ import annotations

from typing import Any

from scripts.docs.prompt_catalog.load import (
    runtime_import_blocker_message,
    runtime_import_failed,
)
from scripts.docs.prompt_catalog.validation.runtime.mapping import run_runtime_mapping_checks
from scripts.docs.prompt_catalog.validation.runtime.render import run_runtime_render_checks


def run_runtime_checks(data: dict[str, Any], errors: list[str]) -> None:
    if runtime_import_failed():
        errors.append(runtime_import_blocker_message())
        return
    run_runtime_mapping_checks(data, errors)
    run_runtime_render_checks(errors)
