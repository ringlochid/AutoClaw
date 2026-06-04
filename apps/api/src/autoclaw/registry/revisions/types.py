"""Temporary Phase 6 shim for the legacy registry revision-types owner."""

from __future__ import annotations

from app.registry.revisions.types import (
    CurrentDefinitionModel,
    CurrentDefinitionRevisionRow,
    CurrentRevisionModel,
    DefinitionInput,
    DefinitionModelT,
    DefinitionModelType,
    PreparedDefinitionRevisionUpsert,
    RegistryWorkflowDefinition,
    RevisionModelT,
    RevisionModelType,
    SchemaModelT,
    model_from_attrs,
)

__all__ = [
    "CurrentDefinitionModel",
    "CurrentDefinitionRevisionRow",
    "CurrentRevisionModel",
    "DefinitionInput",
    "DefinitionModelT",
    "DefinitionModelType",
    "PreparedDefinitionRevisionUpsert",
    "RegistryWorkflowDefinition",
    "RevisionModelT",
    "RevisionModelType",
    "SchemaModelT",
    "model_from_attrs",
]
