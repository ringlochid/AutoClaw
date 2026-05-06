from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import RuntimeBase
from app.db.models.registry import (
    PolicyRevisionModel,
    RoleRevisionModel,
    WorkflowRevisionModel,
)
from app.db.models.runtime.shared import NODE_KIND_VALUES, _sql_in, utcnow


class TaskModel(RuntimeBase):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_title", "title"),
        Index("ix_tasks_workflow_key", "workflow_key"),
    )

    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_root_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    resource_bindings: Mapped[list[TaskResourceBindingModel]] = relationship(
        back_populates="task",
        foreign_keys="TaskResourceBindingModel.task_id",
    )
    task_compose: Mapped[TaskComposeModel | None] = relationship(
        back_populates="task",
        foreign_keys="TaskComposeModel.task_id",
        uselist=False,
    )
    compiled_plan: Mapped[CompiledPlanModel | None] = relationship(
        back_populates="task",
        foreign_keys="CompiledPlanModel.task_id",
        uselist=False,
    )


class WorkspaceRootModel(RuntimeBase):
    __tablename__ = "workspace_roots"

    workspace_root_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)
    binding_mode: Mapped[str] = mapped_column(String(64))


class ContextSpaceModel(RuntimeBase):
    __tablename__ = "context_spaces"

    context_space_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)
    binding_mode: Mapped[str] = mapped_column(String(64))


class ManifestRootModel(RuntimeBase):
    __tablename__ = "manifest_roots"

    manifest_root_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)


class TaskResourceBindingModel(RuntimeBase):
    __tablename__ = "task_resource_bindings"

    task_resource_binding_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    binding_kind: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    binding_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[TaskModel] = relationship(
        back_populates="resource_bindings",
        foreign_keys=[task_id],
    )


class TaskComposeModel(RuntimeBase):
    __tablename__ = "task_composes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_key", "workflow_revision_no"],
            ["workflow_revisions.workflow_key", "workflow_revisions.revision_no"],
            name="fk_task_composes_workflow_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    task_compose_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    workflow_key: Mapped[str] = mapped_column(String(255))
    workflow_revision_no: Mapped[int] = mapped_column(Integer)
    compiled_plan_id: Mapped[str] = mapped_column(
        ForeignKey(
            "compiled_plans.compiled_plan_id",
            deferrable=True,
            initially="DEFERRED",
        )
    )
    workspace_root_path: Mapped[str] = mapped_column(Text)
    context_root_path: Mapped[str] = mapped_column(Text)
    outputs_root_path: Mapped[str] = mapped_column(Text)
    runtime_root_path: Mapped[str] = mapped_column(Text)
    compose_payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    task: Mapped[TaskModel] = relationship(
        back_populates="task_compose",
        foreign_keys=[task_id],
    )
    workflow_revision: Mapped[WorkflowRevisionModel] = relationship(
        primaryjoin=lambda: and_(
            TaskComposeModel.workflow_key == WorkflowRevisionModel.workflow_key,
            TaskComposeModel.workflow_revision_no == WorkflowRevisionModel.revision_no,
        ),
        foreign_keys=lambda: [
            TaskComposeModel.workflow_key,
            TaskComposeModel.workflow_revision_no,
        ],
        uselist=False,
        viewonly=True,
    )
    compiled_plan: Mapped[CompiledPlanModel] = relationship(
        back_populates="task_compose",
        foreign_keys=[compiled_plan_id],
        uselist=False,
    )


class CompiledPlanModel(RuntimeBase):
    __tablename__ = "compiled_plans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_key", "definition_revision_no"],
            ["workflow_revisions.workflow_key", "workflow_revisions.revision_no"],
            name="fk_compiled_plans_workflow_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    compiled_plan_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    workflow_key: Mapped[str] = mapped_column(String(255))
    definition_revision_no: Mapped[int] = mapped_column(Integer)
    compiler_version: Mapped[str] = mapped_column(String(255))
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    task: Mapped[TaskModel] = relationship(
        back_populates="compiled_plan",
        foreign_keys=[task_id],
    )
    workflow_revision: Mapped[WorkflowRevisionModel] = relationship(
        primaryjoin=lambda: and_(
            CompiledPlanModel.workflow_key == WorkflowRevisionModel.workflow_key,
            CompiledPlanModel.definition_revision_no == WorkflowRevisionModel.revision_no,
        ),
        foreign_keys=lambda: [
            CompiledPlanModel.workflow_key,
            CompiledPlanModel.definition_revision_no,
        ],
        uselist=False,
        viewonly=True,
    )
    task_compose: Mapped[TaskComposeModel | None] = relationship(
        back_populates="compiled_plan",
        foreign_keys="TaskComposeModel.compiled_plan_id",
        uselist=False,
    )
    nodes: Mapped[list[CompiledPlanNodeModel]] = relationship(
        back_populates="compiled_plan",
        foreign_keys="CompiledPlanNodeModel.compiled_plan_id",
        order_by="CompiledPlanNodeModel.order_index",
    )
    edges: Mapped[list[CompiledPlanEdgeModel]] = relationship(
        back_populates="compiled_plan",
        foreign_keys="CompiledPlanEdgeModel.compiled_plan_id",
        order_by="CompiledPlanEdgeModel.order_index",
    )


class CompiledPlanNodeModel(RuntimeBase):
    __tablename__ = "compiled_plan_nodes"
    __table_args__ = (
        UniqueConstraint("compiled_plan_id", "node_key"),
        CheckConstraint(
            f"structural_kind IN ({_sql_in(NODE_KIND_VALUES)})",
            name="ck_compiled_plan_nodes_structural_kind",
        ),
        ForeignKeyConstraint(
            ["role_key", "role_revision_no"],
            ["role_revisions.role_key", "role_revisions.revision_no"],
            name="fk_compiled_plan_nodes_role_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["policy_key", "policy_revision_no"],
            ["policy_revisions.policy_key", "policy_revisions.revision_no"],
            name="fk_compiled_plan_nodes_policy_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["compiled_plan_id", "parent_node_key"],
            ["compiled_plan_nodes.compiled_plan_id", "compiled_plan_nodes.node_key"],
            name="fk_compiled_plan_nodes_parent",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    compiled_plan_node_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    compiled_plan_id: Mapped[str] = mapped_column(ForeignKey("compiled_plans.compiled_plan_id"))
    node_key: Mapped[str] = mapped_column(String(255))
    parent_compiled_plan_node_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "compiled_plan_nodes.compiled_plan_node_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    parent_node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    structural_kind: Mapped[str] = mapped_column(String(64))
    role_key: Mapped[str] = mapped_column(String(255))
    role_revision_no: Mapped[int] = mapped_column(Integer)
    role_description: Mapped[str] = mapped_column(Text)
    role_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_revision_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    child_node_keys_json: Mapped[list[str]] = mapped_column(JSON)
    consumes_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    produces_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    criteria_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    child_defaults_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer)
    compiled_plan: Mapped[CompiledPlanModel] = relationship(
        back_populates="nodes",
        foreign_keys=[compiled_plan_id],
    )
    parent: Mapped[CompiledPlanNodeModel | None] = relationship(
        back_populates="children",
        foreign_keys=[parent_compiled_plan_node_id],
        remote_side=lambda: [CompiledPlanNodeModel.compiled_plan_node_id],
        uselist=False,
    )
    children: Mapped[list[CompiledPlanNodeModel]] = relationship(
        back_populates="parent",
        foreign_keys="CompiledPlanNodeModel.parent_compiled_plan_node_id",
        order_by="CompiledPlanNodeModel.order_index",
    )
    role_revision: Mapped[RoleRevisionModel] = relationship(
        primaryjoin=lambda: and_(
            CompiledPlanNodeModel.role_key == RoleRevisionModel.role_key,
            CompiledPlanNodeModel.role_revision_no == RoleRevisionModel.revision_no,
        ),
        foreign_keys=lambda: [
            CompiledPlanNodeModel.role_key,
            CompiledPlanNodeModel.role_revision_no,
        ],
        uselist=False,
        viewonly=True,
    )
    policy_revision: Mapped[PolicyRevisionModel | None] = relationship(
        primaryjoin=lambda: and_(
            CompiledPlanNodeModel.policy_key == PolicyRevisionModel.policy_key,
            CompiledPlanNodeModel.policy_revision_no == PolicyRevisionModel.revision_no,
        ),
        foreign_keys=lambda: [
            CompiledPlanNodeModel.policy_key,
            CompiledPlanNodeModel.policy_revision_no,
        ],
        uselist=False,
        viewonly=True,
    )
    outgoing_edges: Mapped[list[CompiledPlanEdgeModel]] = relationship(
        back_populates="provider_node",
        foreign_keys="CompiledPlanEdgeModel.provider_compiled_plan_node_id",
        order_by="CompiledPlanEdgeModel.order_index",
    )
    incoming_edges: Mapped[list[CompiledPlanEdgeModel]] = relationship(
        back_populates="consumer_node",
        foreign_keys="CompiledPlanEdgeModel.consumer_compiled_plan_node_id",
        order_by="CompiledPlanEdgeModel.order_index",
    )


class CompiledPlanEdgeModel(RuntimeBase):
    __tablename__ = "compiled_plan_edges"
    __table_args__ = (
        UniqueConstraint("compiled_plan_id", "consumer_node_key", "kind", "slot"),
        ForeignKeyConstraint(
            ["compiled_plan_id", "provider_node_key"],
            ["compiled_plan_nodes.compiled_plan_id", "compiled_plan_nodes.node_key"],
            name="fk_compiled_plan_edges_provider_node",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["compiled_plan_id", "consumer_node_key"],
            ["compiled_plan_nodes.compiled_plan_id", "compiled_plan_nodes.node_key"],
            name="fk_compiled_plan_edges_consumer_node",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    compiled_plan_edge_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    compiled_plan_id: Mapped[str] = mapped_column(ForeignKey("compiled_plans.compiled_plan_id"))
    provider_compiled_plan_node_id: Mapped[str] = mapped_column(
        ForeignKey(
            "compiled_plan_nodes.compiled_plan_node_id",
            deferrable=True,
            initially="DEFERRED",
        )
    )
    consumer_compiled_plan_node_id: Mapped[str] = mapped_column(
        ForeignKey(
            "compiled_plan_nodes.compiled_plan_node_id",
            deferrable=True,
            initially="DEFERRED",
        )
    )
    provider_node_key: Mapped[str] = mapped_column(String(255))
    consumer_node_key: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(64))
    slot: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)
    compiled_plan: Mapped[CompiledPlanModel] = relationship(
        back_populates="edges",
        foreign_keys=[compiled_plan_id],
    )
    provider_node: Mapped[CompiledPlanNodeModel] = relationship(
        back_populates="outgoing_edges",
        foreign_keys=[provider_compiled_plan_node_id],
    )
    consumer_node: Mapped[CompiledPlanNodeModel] = relationship(
        back_populates="incoming_edges",
        foreign_keys=[consumer_compiled_plan_node_id],
    )


__all__ = [
    "CompiledPlanEdgeModel",
    "CompiledPlanModel",
    "CompiledPlanNodeModel",
    "ContextSpaceModel",
    "ManifestRootModel",
    "TaskComposeModel",
    "TaskModel",
    "TaskResourceBindingModel",
    "WorkspaceRootModel",
]
