from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import FlowEdgeKind, WorkflowMode


class ResolvedSkillBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    key: str
    version_label: str
    skill_version_id: UUID
    source_ref: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)


class ResolvedWorkflowNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str
    role_key: str
    role_version_id: UUID
    policy_key: str
    policy_version_id: UUID
    mode: WorkflowMode
    allowed_modes: list[WorkflowMode]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolvedWorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_node: str
    to_node: str
    condition_expr: str | None = None
    edge_kind: FlowEdgeKind = FlowEdgeKind.CONTROL


class ResolvedWorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_key: str
    workflow_version_id: UUID
    description: str
    workflow_policy_key: str | None = None
    nodes: list[ResolvedWorkflowNode]
    edges: list[ResolvedWorkflowEdge]
    skill_bindings: list[ResolvedSkillBinding] = Field(default_factory=list)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)


class NormalizedCompiledPlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str
    parent_node_key: str | None = None
    role_version_id: UUID
    policy_version_id: UUID
    mode: WorkflowMode
    order_index: int
    skill_bindings: list[dict[str, Any]] = Field(default_factory=list)


class NormalizedCompiledPlanEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_node: str
    to_node: str
    edge_kind: FlowEdgeKind
    condition_expr: str | None = None
    order_index: int


class NormalizedCompiledPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_key: str
    workflow_version_id: UUID
    compiler_version: str = "v0"
    nodes: list[NormalizedCompiledPlanNode]
    edges: list[NormalizedCompiledPlanEdge]
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
