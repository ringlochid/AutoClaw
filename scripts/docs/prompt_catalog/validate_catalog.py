from __future__ import annotations

from typing import Any

from .validate_checks import run_runtime_checks
from .validate_docs import run_doc_example_checks
from .validate_families import validate_generated_outputs
from .validate_structure import validate_catalog_structure


def validate_catalog(data: dict[str, Any], *, skip_inventory_checks: bool = False) -> list[str]:
    errors: list[str] = []
    state = validate_catalog_structure(data, errors)
    if not skip_inventory_checks:
        validate_generated_outputs(state, errors)
    run_doc_example_checks(
        data,
        errors,
        skip_inventory_checks=skip_inventory_checks,
    )
    run_runtime_checks(data, errors)
    return errors
