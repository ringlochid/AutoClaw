from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Connection


def postgres_backup_schema_name(
    connection: Connection,
    base_name: str = "autoclaw_legacy",
) -> str:
    existing = {str(name) for name in inspect(connection).get_schema_names()}
    candidate = base_name
    suffix = 1
    while candidate in existing:
        candidate = f"{base_name}_{suffix}"
        suffix += 1
    return candidate


def postgres_quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def postgres_rebound_constraint_definition(definition: str, backup_schema: str) -> str:
    rebound = definition.replace(
        f"REFERENCES {backup_schema}.",
        "REFERENCES public.",
    )
    return rebound.replace(
        f'REFERENCES "{backup_schema}".',
        "REFERENCES public.",
    )


def postgres_constraint_with_not_valid(definition: str) -> str:
    if "NOT VALID" in definition:
        return definition
    return f"{definition} NOT VALID"


__all__ = [
    "postgres_backup_schema_name",
    "postgres_constraint_with_not_valid",
    "postgres_quote_identifier",
    "postgres_rebound_constraint_definition",
]
