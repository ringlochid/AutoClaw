from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DefinitionVersionStatus, FlowEdgeKind, SkillProvider, WorkflowMode


class RoleDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    description: str
    allowed_modes: list[WorkflowMode]
    default_policy: str
    checkpoint_schema: str
    defaults: dict[str, Any] = Field(default_factory=dict)


class PolicyDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    rules: dict[str, Any] = Field(default_factory=dict)


class SkillReferenceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SkillProvider
    key: str
    source_uri: str | None = None
    version: str | None = None


class WorkflowNodeSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    mode: WorkflowMode
    policy: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeSeed(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    when: str | None = None
    kind: FlowEdgeKind = FlowEdgeKind.CONTROL


class WorkflowDefinitionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    extends: str | None = None
    policy: str | None = None
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
