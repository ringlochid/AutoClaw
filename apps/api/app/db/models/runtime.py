from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    ApprovalStatus,
    CheckpointStatus,
    ContextItemKind,
    ContextItemScope,
    ContextItemStatus,
    ContextManifestStatus,
    FlowEdgeKind,
    FlowNodeState,
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    NodePlanRevisionStatus,
    NodeSessionStatus,
    ResourceScope,
    TaskResourceBindingMode,
    TaskResourceBindingRole,
    TaskStatus,
    WaitReason,
    WorkflowMode,
    WorkspaceRootKind,
    WorkspaceRootMode,
)
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, build_str_enum
from app.db.types import PortableJSON


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        build_str_enum(TaskStatus, name="task_status"),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )

    flows: Mapped[list[Flow]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Flow.created_at",
    )
    context_items: Mapped[list[ContextItem]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ContextItem.created_at",
    )
    manifest_roots: Mapped[list[ManifestRoot]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ManifestRoot.created_at",
    )
    resource_bindings: Mapped[list[TaskResourceBinding]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskResourceBinding.created_at",
    )
    task_compose: Mapped[TaskCompose | None] = relationship(
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )


class WorkspaceRoot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspace_roots"

    scope: Mapped[ResourceScope] = mapped_column(
        build_str_enum(ResourceScope, name="resource_scope"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    kind: Mapped[WorkspaceRootKind] = mapped_column(
        build_str_enum(WorkspaceRootKind, name="workspace_root_kind"),
        nullable=False,
    )
    mode: Mapped[WorkspaceRootMode] = mapped_column(
        build_str_enum(WorkspaceRootMode, name="workspace_root_mode"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        PortableJSON,
        default=dict,
        nullable=False,
    )

    sourced_context_spaces: Mapped[list[ContextSpace]] = relationship(
        back_populates="source_workspace_root",
        foreign_keys="ContextSpace.source_workspace_root_id",
    )
    task_bindings: Mapped[list[TaskResourceBinding]] = relationship(
        back_populates="workspace_root"
    )


class ContextSpace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "context_spaces"

    scope: Mapped[ResourceScope] = mapped_column(
        build_str_enum(ResourceScope, name="resource_scope", create_type=False),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    source_workspace_root_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspace_roots.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        PortableJSON,
        default=dict,
        nullable=False,
    )

    source_workspace_root: Mapped[WorkspaceRoot | None] = relationship(
        back_populates="sourced_context_spaces",
        foreign_keys=[source_workspace_root_id],
    )
    task_bindings: Mapped[list[TaskResourceBinding]] = relationship(back_populates="context_space")


class ManifestRoot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manifest_roots"
    __table_args__ = (UniqueConstraint("task_id", "key", name="uq_manifest_roots_task_key"),)

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        PortableJSON,
        default=dict,
        nullable=False,
    )

    task: Mapped[Task] = relationship(back_populates="manifest_roots")
    task_bindings: Mapped[list[TaskResourceBinding]] = relationship(back_populates="manifest_root")
    context_manifests: Mapped[list[ContextManifest]] = relationship(back_populates="manifest_root")


class TaskResourceBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_resource_bindings"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN workspace_root_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN context_space_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN manifest_root_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_task_resource_bindings_exactly_one_target",
        ),
        CheckConstraint(
            "(binding_role != 'manifest_root') OR (manifest_root_id IS NOT NULL)",
            name="ck_task_resource_bindings_manifest_role_target",
        ),
        Index("ix_task_resource_bindings_task_role", "task_id", "binding_role"),
        Index(
            "uq_task_resource_bindings_primary_workspace",
            "task_id",
            unique=True,
            postgresql_where=text("binding_role = 'primary_workspace'"),
            sqlite_where=text("binding_role = 'primary_workspace'"),
        ),
        Index(
            "uq_task_resource_bindings_primary_context",
            "task_id",
            unique=True,
            postgresql_where=text("binding_role = 'primary_context'"),
            sqlite_where=text("binding_role = 'primary_context'"),
        ),
        Index(
            "uq_task_resource_bindings_manifest_root",
            "task_id",
            unique=True,
            postgresql_where=text("binding_role = 'manifest_root'"),
            sqlite_where=text("binding_role = 'manifest_root'"),
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    binding_role: Mapped[TaskResourceBindingRole] = mapped_column(
        build_str_enum(TaskResourceBindingRole, name="task_resource_binding_role"),
        nullable=False,
    )
    workspace_root_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspace_roots.id"), nullable=True
    )
    context_space_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("context_spaces.id"), nullable=True
    )
    manifest_root_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("manifest_roots.id"), nullable=True
    )
    mode: Mapped[TaskResourceBindingMode] = mapped_column(
        build_str_enum(TaskResourceBindingMode, name="task_resource_binding_mode"),
        nullable=False,
    )
    read_only: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        PortableJSON,
        default=dict,
        nullable=False,
    )

    task: Mapped[Task] = relationship(back_populates="resource_bindings")
    workspace_root: Mapped[WorkspaceRoot | None] = relationship(back_populates="task_bindings")
    context_space: Mapped[ContextSpace | None] = relationship(back_populates="task_bindings")
    manifest_root: Mapped[ManifestRoot | None] = relationship(back_populates="task_bindings")


class TaskCompose(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_composes"
    __table_args__ = (UniqueConstraint("task_id", name="uq_task_composes_task_id"),)

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflow_versions.id"), nullable=True
    )
    compiled_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("compiled_plans.id"), nullable=True
    )
    entrypoint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="ready", nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", PortableJSON, default=dict, nullable=False
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    context_refs: Mapped[list[dict[str, Any]] | list[str]] = mapped_column(
        PortableJSON, default=list, nullable=False
    )
    skill_dependencies: Mapped[list[dict[str, Any]]] = mapped_column(
        PortableJSON, default=list, nullable=False
    )
    workspace_root_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    context_root_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manifest_root_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    materialization_root: Mapped[str] = mapped_column(String(512), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    task: Mapped[Task] = relationship(back_populates="task_compose")
    workflow_version: Mapped[WorkflowVersion | None] = relationship(
        foreign_keys=[workflow_version_id]
    )
    compiled_plan: Mapped[CompiledPlan | None] = relationship(
        foreign_keys=[compiled_plan_id]
    )


class CompiledPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compiled_plans"

    workflow_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    compiler_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v0")
    plan_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )

    workflow_version: Mapped[WorkflowVersion] = relationship(back_populates="compiled_plans")
    nodes: Mapped[list[CompiledPlanNode]] = relationship(
        back_populates="compiled_plan",
        cascade="all, delete-orphan",
        order_by="CompiledPlanNode.order_index",
    )
    edges: Mapped[list[CompiledPlanEdge]] = relationship(
        back_populates="compiled_plan",
        cascade="all, delete-orphan",
        order_by="CompiledPlanEdge.order_index",
    )
    seed_flows: Mapped[list[Flow]] = relationship(
        back_populates="seed_compiled_plan",
        foreign_keys="Flow.seed_compiled_plan_id",
    )
    flow_revisions: Mapped[list[FlowRevision]] = relationship(back_populates="compiled_plan")


class CompiledPlanNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compiled_plan_nodes"
    __table_args__ = (
        UniqueConstraint(
            "compiled_plan_id", "node_key", name="uq_compiled_plan_nodes_plan_node_key"
        ),
        Index(
            "ix_compiled_plan_nodes_plan_order",
            "compiled_plan_id",
            "order_index",
        ),
    )

    compiled_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_node_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("role_versions.id"), nullable=True
    )
    policy_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("policy_versions.id"), nullable=True
    )
    mode: Mapped[WorkflowMode] = mapped_column(
        build_str_enum(WorkflowMode, name="workflow_mode"),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skill_bindings: Mapped[list[dict[str, Any]]] = mapped_column(
        PortableJSON, default=list, nullable=False
    )
    effective_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        default=dict,
        nullable=False,
    )

    compiled_plan: Mapped[CompiledPlan] = relationship(back_populates="nodes")
    flow_nodes: Mapped[list[FlowNode]] = relationship(back_populates="source_compiled_plan_node")


class CompiledPlanEdge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compiled_plan_edges"
    __table_args__ = (
        Index(
            "ix_compiled_plan_edges_plan_order",
            "compiled_plan_id",
            "order_index",
        ),
    )

    compiled_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    to_node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    edge_kind: Mapped[FlowEdgeKind] = mapped_column(
        build_str_enum(FlowEdgeKind, name="flow_edge_kind"),
        default=FlowEdgeKind.CONTROL,
        nullable=False,
    )
    condition_expr: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    compiled_plan: Mapped[CompiledPlan] = relationship(back_populates="edges")


class Flow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flows"
    __table_args__ = (
        Index("ix_flows_task_status", "task_id", "status"),
        Index("ix_flows_active_flow_revision_id", "active_flow_revision_id"),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    seed_compiled_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plans.id"),
        nullable=False,
    )
    active_flow_revision_id: Mapped[UUID | None] = mapped_column(nullable=True)
    status: Mapped[FlowStatus] = mapped_column(
        build_str_enum(FlowStatus, name="flow_status"),
        default=FlowStatus.PENDING,
        nullable=False,
    )
    execution_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    task: Mapped[Task] = relationship(back_populates="flows")
    seed_compiled_plan: Mapped[CompiledPlan] = relationship(
        back_populates="seed_flows",
        foreign_keys=[seed_compiled_plan_id],
    )
    active_flow_revision: Mapped[FlowRevision | None] = relationship(
        primaryjoin="Flow.active_flow_revision_id == FlowRevision.id",
        foreign_keys=[active_flow_revision_id],
        post_update=True,
    )
    flow_revisions: Mapped[list[FlowRevision]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        foreign_keys="FlowRevision.flow_id",
        order_by="FlowRevision.revision_no",
    )
    node_attempts: Mapped[list[NodeAttempt]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="NodeAttempt.created_at",
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="Approval.created_at",
    )
    context_items: Mapped[list[ContextItem]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="ContextItem.created_at",
    )
    context_manifests: Mapped[list[ContextManifest]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="ContextManifest.manifest_no",
    )
    node_plan_revisions: Mapped[list[NodePlanRevision]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="NodePlanRevision.created_at",
    )


class FlowRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flow_revisions"
    __table_args__ = (
        UniqueConstraint("flow_id", "revision_no", name="uq_flow_revisions_flow_revision_no"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    compiled_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plans.id"),
        nullable=False,
    )
    parent_flow_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flow_revisions.id"), nullable=True
    )
    status: Mapped[FlowRevisionStatus] = mapped_column(
        build_str_enum(FlowRevisionStatus, name="flow_revision_status"),
        default=FlowRevisionStatus.CANDIDATE,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_patch_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    adopted_from_node_plan_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_plan_revisions.id"), nullable=True
    )
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    flow: Mapped[Flow] = relationship(
        back_populates="flow_revisions",
        foreign_keys=[flow_id],
    )
    compiled_plan: Mapped[CompiledPlan] = relationship(back_populates="flow_revisions")
    parent_flow_revision: Mapped[FlowRevision | None] = relationship(remote_side="FlowRevision.id")
    nodes: Mapped[list[FlowNode]] = relationship(
        back_populates="flow_revision",
        cascade="all, delete-orphan",
        order_by="FlowNode.order_index",
    )
    edges: Mapped[list[FlowEdge]] = relationship(
        back_populates="flow_revision",
        cascade="all, delete-orphan",
        order_by="FlowEdge.created_at",
    )
    adopted_from_node_plan_revision: Mapped[NodePlanRevision | None] = relationship(
        foreign_keys=[adopted_from_node_plan_revision_id],
        post_update=True,
    )


class FlowNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flow_nodes"
    __table_args__ = (
        UniqueConstraint("flow_revision_id", "node_key", name="uq_flow_nodes_revision_node_key"),
        Index("ix_flow_nodes_flow_revision_order", "flow_id", "flow_revision_id", "order_index"),
        Index("ix_flow_nodes_flow_logical_node", "flow_id", "logical_node_key"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_compiled_plan_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("compiled_plan_nodes.id"), nullable=True
    )
    parent_flow_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flow_nodes.id"), nullable=True
    )
    supersedes_flow_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flow_nodes.id"), nullable=True
    )
    logical_node_key: Mapped[str] = mapped_column(String(256), nullable=False)
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    node_path: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[FlowNodeState] = mapped_column(
        build_str_enum(FlowNodeState, name="flow_node_state"),
        default=FlowNodeState.READY,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )

    flow: Mapped[Flow] = relationship()
    flow_revision: Mapped[FlowRevision] = relationship(back_populates="nodes")
    source_compiled_plan_node: Mapped[CompiledPlanNode | None] = relationship(
        back_populates="flow_nodes"
    )
    parent_flow_node: Mapped[FlowNode | None] = relationship(
        foreign_keys=[parent_flow_node_id],
        remote_side="FlowNode.id",
    )
    supersedes_flow_node: Mapped[FlowNode | None] = relationship(
        foreign_keys=[supersedes_flow_node_id],
        remote_side="FlowNode.id",
    )
    attempts: Mapped[list[NodeAttempt]] = relationship(
        back_populates="flow_node",
        cascade="all, delete-orphan",
        order_by="NodeAttempt.number",
    )
    checkpoints: Mapped[list[NodeCheckpoint]] = relationship(
        back_populates="flow_node",
        cascade="all, delete-orphan",
        order_by="NodeCheckpoint.sequence_no",
    )
    approvals: Mapped[list[Approval]] = relationship(back_populates="flow_node")
    node_session: Mapped[NodeSession | None] = relationship(
        back_populates="flow_node",
        uselist=False,
        cascade="all, delete-orphan",
    )
    context_items: Mapped[list[ContextItem]] = relationship(back_populates="flow_node")
    context_manifests: Mapped[list[ContextManifest]] = relationship(
        back_populates="flow_node",
        cascade="all, delete-orphan",
        order_by="ContextManifest.manifest_no",
    )
    outgoing_edges: Mapped[list[FlowEdge]] = relationship(
        back_populates="from_flow_node",
        foreign_keys="FlowEdge.from_flow_node_id",
    )
    incoming_edges: Mapped[list[FlowEdge]] = relationship(
        back_populates="to_flow_node",
        foreign_keys="FlowEdge.to_flow_node_id",
    )
    requested_plan_revisions: Mapped[list[NodePlanRevision]] = relationship(
        back_populates="requesting_flow_node",
        foreign_keys="NodePlanRevision.requesting_flow_node_id",
    )


class FlowEdge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flow_edges"
    __table_args__ = (Index("ix_flow_edges_flow_revision_id", "flow_id", "flow_revision_id"),)

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_kind: Mapped[FlowEdgeKind] = mapped_column(
        build_str_enum(FlowEdgeKind, name="flow_edge_kind", create_type=False),
        default=FlowEdgeKind.CONTROL,
        nullable=False,
    )
    condition_expr: Mapped[str | None] = mapped_column(Text, nullable=True)

    flow_revision: Mapped[FlowRevision] = relationship(back_populates="edges")
    from_flow_node: Mapped[FlowNode] = relationship(
        back_populates="outgoing_edges",
        foreign_keys=[from_flow_node_id],
    )
    to_flow_node: Mapped[FlowNode] = relationship(
        back_populates="incoming_edges",
        foreign_keys=[to_flow_node_id],
    )


class NodePlanRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "node_plan_revisions"
    __table_args__ = (Index("ix_node_plan_revisions_flow_status", "flow_id", "status"),)

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    requesting_flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    requesting_node_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_attempts.id"), nullable=True
    )
    base_flow_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_flow_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flow_revisions.id"), nullable=True
    )
    patch_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NodePlanRevisionStatus] = mapped_column(
        build_str_enum(NodePlanRevisionStatus, name="node_plan_revision_status"),
        default=NodePlanRevisionStatus.PROPOSED,
        nullable=False,
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    flow: Mapped[Flow] = relationship(back_populates="node_plan_revisions")
    requesting_flow_node: Mapped[FlowNode] = relationship(
        back_populates="requested_plan_revisions",
        foreign_keys=[requesting_flow_node_id],
    )
    requesting_node_attempt: Mapped[NodeAttempt | None] = relationship(
        foreign_keys=[requesting_node_attempt_id]
    )
    base_flow_revision: Mapped[FlowRevision] = relationship(foreign_keys=[base_flow_revision_id])
    candidate_flow_revision: Mapped[FlowRevision | None] = relationship(
        foreign_keys=[candidate_flow_revision_id],
        post_update=True,
    )


class NodeAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "node_attempts"
    __table_args__ = (
        UniqueConstraint("flow_node_id", "number", name="uq_node_attempts_node_number"),
        Index("ix_node_attempts_flow_node_number", "flow_id", "flow_node_id", "number"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[NodeAttemptStatus] = mapped_column(
        build_str_enum(NodeAttemptStatus, name="node_attempt_status"),
        default=NodeAttemptStatus.PENDING,
        nullable=False,
    )
    retry_of_node_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_attempts.id"), nullable=True
    )
    failure_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    flow: Mapped[Flow] = relationship(back_populates="node_attempts")
    flow_revision: Mapped[FlowRevision] = relationship()
    flow_node: Mapped[FlowNode] = relationship(back_populates="attempts")
    retry_of_node_attempt: Mapped[NodeAttempt | None] = relationship(remote_side="NodeAttempt.id")
    checkpoints: Mapped[list[NodeCheckpoint]] = relationship(
        back_populates="node_attempt",
        cascade="all, delete-orphan",
        order_by="NodeCheckpoint.sequence_no",
    )
    approvals: Mapped[list[Approval]] = relationship(back_populates="node_attempt")
    context_items: Mapped[list[ContextItem]] = relationship(back_populates="node_attempt")
    context_manifests: Mapped[list[ContextManifest]] = relationship(
        back_populates="node_attempt",
        cascade="all, delete-orphan",
        order_by="ContextManifest.manifest_no",
    )
    requested_plan_revisions: Mapped[list[NodePlanRevision]] = relationship(
        foreign_keys="NodePlanRevision.requesting_node_attempt_id",
        overlaps="requesting_node_attempt",
    )


class NodeCheckpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "node_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "node_attempt_id", "sequence_no", name="uq_node_checkpoints_attempt_sequence"
        ),
        Index("ix_node_checkpoints_flow_attempt", "flow_id", "node_attempt_id"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("node_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CheckpointStatus] = mapped_column(
        build_str_enum(CheckpointStatus, name="checkpoint_status"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    failure_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    recommended_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    wait_reason: Mapped[WaitReason | None] = mapped_column(
        build_str_enum(WaitReason, name="wait_reason"),
        nullable=True,
    )

    flow_node: Mapped[FlowNode] = relationship(back_populates="checkpoints")
    node_attempt: Mapped[NodeAttempt] = relationship(back_populates="checkpoints")


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approvals_flow_status", "flow_id", "status"),)

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"), nullable=False
    )
    flow_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("flow_nodes.id"), nullable=True)
    node_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_attempts.id"), nullable=True
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        build_str_enum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    resolution_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )

    flow: Mapped[Flow] = relationship(back_populates="approvals")
    flow_node: Mapped[FlowNode | None] = relationship(back_populates="approvals")
    node_attempt: Mapped[NodeAttempt | None] = relationship(back_populates="approvals")


class NodeSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "node_sessions"
    __table_args__ = (UniqueConstraint("flow_node_id", name="uq_node_sessions_flow_node_id"),)

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_attempts.id"), nullable=True
    )
    provider_session_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[NodeSessionStatus] = mapped_column(
        build_str_enum(NodeSessionStatus, name="node_session_status"),
        default=NodeSessionStatus.IDLE,
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    flow_node: Mapped[FlowNode] = relationship(back_populates="node_session")
    node_attempt: Mapped[NodeAttempt | None] = relationship()
    context_manifests: Mapped[list[ContextManifest]] = relationship(back_populates="node_session")


class ContextItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "context_items"
    __table_args__ = (Index("ix_context_items_scope_status", "task_id", "scope", "status"),)

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_id: Mapped[UUID | None] = mapped_column(ForeignKey("flows.id"), nullable=True)
    flow_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flow_revisions.id"), nullable=True
    )
    flow_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("flow_nodes.id"), nullable=True)
    node_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_attempts.id"), nullable=True
    )
    scope: Mapped[ContextItemScope] = mapped_column(
        build_str_enum(ContextItemScope, name="context_item_scope"),
        nullable=False,
    )
    kind: Mapped[ContextItemKind] = mapped_column(
        build_str_enum(ContextItemKind, name="context_item_kind"),
        nullable=False,
    )
    visibility_policy: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    status: Mapped[ContextItemStatus] = mapped_column(
        build_str_enum(ContextItemStatus, name="context_item_status"),
        default=ContextItemStatus.DRAFT,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        PortableJSON,
        default=dict,
        nullable=False,
    )
    published_by: Mapped[str] = mapped_column(String(128), nullable=False)
    source_checkpoint_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_checkpoints.id"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    task: Mapped[Task] = relationship(back_populates="context_items")
    flow: Mapped[Flow | None] = relationship(back_populates="context_items")
    flow_node: Mapped[FlowNode | None] = relationship(back_populates="context_items")
    node_attempt: Mapped[NodeAttempt | None] = relationship(back_populates="context_items")


class ContextManifest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "context_manifests"
    __table_args__ = (
        UniqueConstraint(
            "node_attempt_id", "manifest_no", name="uq_context_manifests_attempt_manifest_no"
        ),
        Index("ix_context_manifests_flow_status", "flow_id", "status"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("node_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_sessions.id"), nullable=True
    )
    manifest_root_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("manifest_roots.id"), nullable=True
    )
    manifest_no: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[ContextManifestStatus] = mapped_column(
        build_str_enum(ContextManifestStatus, name="context_manifest_status"),
        default=ContextManifestStatus.PROJECTED,
        nullable=False,
    )
    projected_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ack_checkpoint_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("node_checkpoints.id"), nullable=True
    )

    flow: Mapped[Flow] = relationship(back_populates="context_manifests")
    flow_node: Mapped[FlowNode] = relationship(back_populates="context_manifests")
    node_attempt: Mapped[NodeAttempt] = relationship(back_populates="context_manifests")
    node_session: Mapped[NodeSession | None] = relationship(back_populates="context_manifests")
    manifest_root: Mapped[ManifestRoot | None] = relationship(back_populates="context_manifests")


from app.db.models.registry import WorkflowVersion  # noqa: E402  # isort: skip
