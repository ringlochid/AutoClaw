"""Temporary Phase 6 shim for the legacy definition-registry schema owner."""

from __future__ import annotations

from app.schemas.definitions.registry import (
    BudgetSpec,
    DefinitionContent,
    DefinitionHistorySort,
    DefinitionKind,
    DefinitionListQuery,
    DefinitionListSort,
    DefinitionRevisionDetailResponse,
    DefinitionRevisionHistoryEntry,
    DefinitionRevisionHistoryQuery,
    DefinitionRevisionHistoryResponse,
    DefinitionSummaryListResponse,
    DefinitionSummaryRead,
    DefinitionUploadRequest,
    PolicyDefinitionFile,
    PolicyDefinitionInput,
    RoleDefinitionFile,
    RoleDefinitionInput,
)

__all__ = [
    "BudgetSpec",
    "DefinitionContent",
    "DefinitionHistorySort",
    "DefinitionKind",
    "DefinitionListQuery",
    "DefinitionListSort",
    "DefinitionRevisionDetailResponse",
    "DefinitionRevisionHistoryEntry",
    "DefinitionRevisionHistoryQuery",
    "DefinitionRevisionHistoryResponse",
    "DefinitionSummaryListResponse",
    "DefinitionSummaryRead",
    "DefinitionUploadRequest",
    "PolicyDefinitionFile",
    "PolicyDefinitionInput",
    "RoleDefinitionFile",
    "RoleDefinitionInput",
]
