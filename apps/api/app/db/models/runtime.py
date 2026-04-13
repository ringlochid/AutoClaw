from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    ApprovalStatus,
    AttemptStatus,
    CheckpointStatus,
    FlowEdgeKind,
    FlowNodeState,
    FlowStatus,
    RunStatus,
    TaskStatus,
    WorkflowMode,
)
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, build_str_enum


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        build_str_enum(TaskStatus, name="task_status"),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    runs: Mapped[list[Run]] = relationship(back_populates="task", cascade="all, delete-orphan")


class CompiledPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compiled_plans"

    workflow_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    compiler_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v0")
    plan_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

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
    runs: Mapped[list[Run]] = relationship(back_populates="compiled_plan")
    flows: Mapped[list[Flow]] = relationship(back_populates="compiled_plan")


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
        JSONB, default=list, nullable=False
    )

    compiled_plan: Mapped[CompiledPlan] = relationship(back_populates="nodes")
    flow_nodes: Mapped[list[FlowNode]] = relationship(back_populates="compiled_plan_node")


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


class Run(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runs"

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_versions.id"),
        nullable=False,
    )
    compiled_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plans.id"),
        nullable=False,
    )
    status: Mapped[RunStatus] = mapped_column(
        build_str_enum(RunStatus, name="run_status"),
        default=RunStatus.PENDING,
        nullable=False,
    )
    current_attempt_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    task: Mapped[Task] = relationship(back_populates="runs")
    compiled_plan: Mapped[CompiledPlan] = relationship(back_populates="runs")
    attempts: Mapped[list[Attempt]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Attempt.number",
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Approval.created_at",
    )


class Attempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("run_id", "number", name="uq_attempts_run_number"),)

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        build_str_enum(AttemptStatus, name="attempt_status"),
        default=AttemptStatus.PENDING,
        nullable=False,
    )
    retry_of_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("attempts.id"), nullable=True
    )

    run: Mapped[Run] = relationship(back_populates="attempts")
    retry_of_attempt: Mapped[Attempt | None] = relationship(remote_side="Attempt.id")
    flows: Mapped[list[Flow]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="Flow.created_at",
    )
    approvals: Mapped[list[Approval]] = relationship(back_populates="attempt")


class Flow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flows"
    __table_args__ = (Index("ix_flows_attempt_id", "attempt_id"),)

    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    compiled_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plans.id"),
        nullable=False,
    )
    status: Mapped[FlowStatus] = mapped_column(
        build_str_enum(FlowStatus, name="flow_status"),
        default=FlowStatus.PENDING,
        nullable=False,
    )

    attempt: Mapped[Attempt] = relationship(back_populates="flows")
    compiled_plan: Mapped[CompiledPlan] = relationship(back_populates="flows")
    nodes: Mapped[list[FlowNode]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="FlowNode.iteration_index",
    )
    checkpoints: Mapped[list[NodeCheckpoint]] = relationship(
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="NodeCheckpoint.sequence_no",
    )


class FlowNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flow_nodes"
    __table_args__ = (
        UniqueConstraint("flow_id", "node_key", name="uq_flow_nodes_flow_node_key"),
        Index("ix_flow_nodes_flow_iteration", "flow_id", "iteration_index"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    compiled_plan_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("compiled_plan_nodes.id"),
        nullable=False,
    )
    parent_flow_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("flow_nodes.id"), nullable=True
    )
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[FlowNodeState] = mapped_column(
        build_str_enum(FlowNodeState, name="flow_node_state"),
        default=FlowNodeState.READY,
        nullable=False,
    )
    iteration_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    flow: Mapped[Flow] = relationship(back_populates="nodes")
    compiled_plan_node: Mapped[CompiledPlanNode] = relationship(back_populates="flow_nodes")
    parent_flow_node: Mapped[FlowNode | None] = relationship(remote_side="FlowNode.id")
    checkpoints: Mapped[list[NodeCheckpoint]] = relationship(
        back_populates="flow_node",
        cascade="all, delete-orphan",
    )
    approvals: Mapped[list[Approval]] = relationship(back_populates="flow_node")


class NodeCheckpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "node_checkpoints"
    __table_args__ = (
        UniqueConstraint("flow_node_id", "sequence_no", name="uq_node_checkpoints_node_sequence"),
        Index("ix_node_checkpoints_flow_id", "flow_id"),
    )

    flow_id: Mapped[UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CheckpointStatus] = mapped_column(
        build_str_enum(CheckpointStatus, name="checkpoint_status"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    failure_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    recommended_next_action: Mapped[str | None] = mapped_column(String(128), nullable=True)

    flow: Mapped[Flow] = relationship(back_populates="checkpoints")
    flow_node: Mapped[FlowNode] = relationship(back_populates="checkpoints")


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approvals_run_id", "run_id"),)

    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    attempt_id: Mapped[UUID | None] = mapped_column(ForeignKey("attempts.id"), nullable=True)
    flow_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("flow_nodes.id"), nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        build_str_enum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    resolution_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    run: Mapped[Run] = relationship(back_populates="approvals")
    attempt: Mapped[Attempt | None] = relationship(back_populates="approvals")
    flow_node: Mapped[FlowNode | None] = relationship(back_populates="approvals")


from app.db.models.registry import WorkflowVersion  # noqa: E402  # isort: skip
