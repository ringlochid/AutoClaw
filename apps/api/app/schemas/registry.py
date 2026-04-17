from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    DefinitionVersionStatus,
    FlowEdgeKind,
    SkillBindingState,
    SkillProvider,
    WorkflowMode,
)


class SkillReferenceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SkillProvider
    key: str
    source_uri: str | None = None
    version: str | None = None
    state: SkillBindingState = SkillBindingState.ALLOWED


class RoleDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    description: str
    allowed_modes: list[WorkflowMode]
    default_policy: str
    checkpoint_schema: str
    defaults: dict[str, Any] = Field(default_factory=dict)
    skill_refs: list[SkillReferenceSeed] = Field(default_factory=list)


class PolicyDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    rules: dict[str, Any] = Field(default_factory=dict)


class WorkflowNodeSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    mode: WorkflowMode
    policy: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    skill_refs: list[SkillReferenceSeed] = Field(default_factory=list)


class WorkflowEdgeSeed(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    when: str | None = None
    kind: FlowEdgeKind = FlowEdgeKind.CONTROL


class WorkflowDefaultsSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    skill_refs: list[SkillReferenceSeed] = Field(default_factory=list)


class WorkflowDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    extends: str | None = None
    policy: str | None = None
    defaults: WorkflowDefaultsSeed = Field(default_factory=WorkflowDefaultsSeed)
    nodes: list[WorkflowNodeSeed] = Field(default_factory=list)
    edges: list[WorkflowEdgeSeed] = Field(default_factory=list)
    skill_refs: list[SkillReferenceSeed] = Field(default_factory=list)


class DefinitionFileRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    path: Path


class DefinitionVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    status: DefinitionVersionStatus
    description: str | None
    published_at: str | None = None


class RegistryDefinitionSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    description: str | None = None
    latest_version: int | None = None
    latest_status: DefinitionVersionStatus | None = None
    published_version: int | None = None
    draft_version: int | None = None
    updated_at: datetime | None = None


class RegistryDefinitionVersionDetailRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    key: str
    version: int
    status: DefinitionVersionStatus
    description: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RegistrySkillSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SkillProvider
    key: str
    source_uri: str | None = None
    description: str | None = None
    published_version: str | None = None


class WorkflowValidationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool = True
    normalized_plan: dict[str, Any] = Field(default_factory=dict)
