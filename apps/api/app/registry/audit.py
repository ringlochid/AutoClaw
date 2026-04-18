from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DefinitionWriteAudit:
    requested_by: str | None = None
    audit: dict[str, Any] = field(default_factory=dict)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def build_definition_write_audit(
    *,
    requested_by: str | None = None,
    source_session: str | None = None,
    reason: str | None = None,
) -> DefinitionWriteAudit | None:
    actor = _normalize_optional_text(requested_by)
    normalized_source_session = _normalize_optional_text(source_session)
    normalized_reason = _normalize_optional_text(reason)

    audit: dict[str, Any] = {}
    if actor is not None:
        audit["actor"] = actor
    if normalized_source_session is not None:
        audit["source_session"] = normalized_source_session
    if normalized_reason is not None:
        audit["reason"] = normalized_reason

    if actor is None and not audit:
        return None

    return DefinitionWriteAudit(requested_by=actor, audit=audit)
