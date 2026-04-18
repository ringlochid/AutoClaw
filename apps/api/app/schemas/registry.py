from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    DefinitionVersionStatus,
    FlowEdgeKind,
    SkillBindingState,
    SkillProvider,
    TaskResourceBindingMode,
    WorkflowMode,
)


class SkillReferenceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SkillProvider
    key: str
    runtime_name: str = Field(min_length=1)
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


class WorkflowTaskResourceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TaskResourceBindingMode
    auto_create: bool | None = None
    ref: str | None = None
    seed_from: list[str] | None = None
    read_only: bool | None = None
    required: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowTaskDefaultsSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace: WorkflowTaskResourceSeed | None = None
    context: WorkflowTaskResourceSeed | None = None
    manifests: WorkflowTaskResourceSeed | None = None


class WorkflowWorkspaceMountSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    access: Literal["read_only", "read_write"] | None = None
    required: bool | None = None


class WorkflowContextRefSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    required: bool | None = None


class WorkflowWorkspaceResourcesSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mounts: list[WorkflowWorkspaceMountSeed] = Field(default_factory=list)


class WorkflowContextResourcesSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refs: list[WorkflowContextRefSeed] = Field(default_factory=list)


class WorkflowImageResourceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str | None = None
    kind: str | None = None
    required: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowComposeResourceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str | None = None
    services: list[str] = Field(default_factory=list)
    required: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowContainerResourceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str | None = None
    backend_kind: str | None = None
    reuse_policy: str | None = None
    required: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowNodeResourcesSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace: WorkflowWorkspaceResourcesSeed = Field(
        default_factory=WorkflowWorkspaceResourcesSeed
    )
    context: WorkflowContextResourcesSeed = Field(
        default_factory=WorkflowContextResourcesSeed
    )
    image: WorkflowImageResourceSeed | None = None
    compose: WorkflowComposeResourceSeed | None = None
    container: WorkflowContainerResourceSeed | None = None


class WorkflowNodeSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    mode: WorkflowMode
    policy: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    resources: WorkflowNodeResourcesSeed = Field(default_factory=WorkflowNodeResourcesSeed)
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
    task_defaults: WorkflowTaskDefaultsSeed = Field(default_factory=WorkflowTaskDefaultsSeed)
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
    requested_by: str | None = None
    audit: dict[str, Any] = Field(default_factory=dict)
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
    requested_by: str | None = None
    audit: dict[str, Any] = Field(default_factory=dict)
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RegistrySkillSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SkillProvider
    key: str
    runtime_name: str | None = None
    source_uri: str | None = None
    description: str | None = None
    published_version: str | None = None


class RegistrySnapshotRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[RegistryDefinitionSummaryRead] = Field(default_factory=list)
    policies: list[RegistryDefinitionSummaryRead] = Field(default_factory=list)
    workflows: list[RegistryDefinitionSummaryRead] = Field(default_factory=list)
    skills: list[RegistrySkillSummaryRead] = Field(default_factory=list)


class WorkflowValidationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool = True
    normalized_plan: dict[str, Any] = Field(default_factory=dict)
