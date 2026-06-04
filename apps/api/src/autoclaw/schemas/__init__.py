from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autoclaw.schemas import definitions, runtime
    from autoclaw.schemas.operation_failure import OperationFailure, OperationFailureCode

_LAZY_SUBMODULE_EXPORTS: dict[str, str] = {
    "definitions": "autoclaw.schemas.definitions",
    "runtime": "autoclaw.schemas.runtime",
}
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "OperationFailure": ("autoclaw.schemas.operation_failure", "OperationFailure"),
    "OperationFailureCode": (
        "autoclaw.schemas.operation_failure",
        "OperationFailureCode",
    ),
}


def __getattr__(name: str) -> Any:
    submodule_name = _LAZY_SUBMODULE_EXPORTS.get(name)
    if submodule_name is not None:
        value = import_module(submodule_name)
        globals()[name] = value
        return value

    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "OperationFailure",
    "OperationFailureCode",
    "definitions",
    "runtime",
]
