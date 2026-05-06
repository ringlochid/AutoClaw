from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

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
from app.db.models.runtime.shared import (
    FLOW_EDGE_KIND_VALUES,
    FLOW_STATUS_VALUES,
    NODE_KIND_VALUES,
    NODE_STATE_VALUES,
    STRUCTURAL_REVISION_CAUSE_VALUES,
    _sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from app.db.models.runtime.assignment import AssignmentModel
    from app.db.models.runtime.dispatch import DispatchTurnModel


class FlowModel(RuntimeBase):
    __tablename__ = "flows"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_sql_in(FLOW_STATUS_VALUES)})",
            name="ck_flows_status",
        ),
        ForeignKeyConstraint(
            ["flow_id", "active_flow_revision_id"],
            ["flow_revisions.flow_id", "flow_revisions.flow_revision_id"],
            name="fk_flows_active_flow_revision_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["flow_id", "current_open_dispatch_id"],
            ["dispatch_turns.flow_id", "dispatch_turns.dispatch_id"],
            name="fk_flows_current_open_dispatch_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_flows_status_updated_at", "status", "updated_at"),
        Index("ix_flows_current_node_key", "current_node_key"),
    )

    flow_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    compiled_plan_id: Mapped[str] = mapped_column(ForeignKey("compiled_plans.compiled_plan_id"))
    status: Mapped[str] = mapped_column(String(64), index=True)
    active_flow_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "flow_revisions.flow_revision_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    current_open_dispatch_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "dispatch_turns.dispatch_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    current_node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    flow_revisions: Mapped[list[FlowRevisionModel]] = relationship(
        back_populates="flow",
        foreign_keys="FlowRevisionModel.flow_id",
        lazy="selectin",
        order_by="FlowRevisionModel.revision_index",
    )
    active_flow_revision: Mapped[FlowRevisionModel | None] = relationship(
        primaryjoin=lambda: and_(
            FlowModel.active_flow_revision_id == FlowRevisionModel.flow_revision_id,
            FlowModel.flow_id == FlowRevisionModel.flow_id,
        ),
        foreign_keys=lambda: [FlowModel.active_flow_revision_id, FlowModel.flow_id],
        lazy="selectin",
        viewonly=True,
    )
    dispatch_turns: Mapped[list[DispatchTurnModel]] = relationship(
        "DispatchTurnModel",
        back_populates="flow",
        foreign_keys="DispatchTurnModel.flow_id",
        lazy="selectin",
        order_by="DispatchTurnModel.rendered_at",
    )
    current_open_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        primaryjoin=(
            "and_("
            "FlowModel.current_open_dispatch_id == DispatchTurnModel.dispatch_id, "
            "FlowModel.flow_id == DispatchTurnModel.flow_id"
            ")"
        ),
        foreign_keys="FlowModel.current_open_dispatch_id, FlowModel.flow_id",
        lazy="selectin",
        viewonly=True,
    )


class FlowRevisionModel(RuntimeBase):
    __tablename__ = "flow_revisions"
    __table_args__ = (
        UniqueConstraint("flow_id", "revision_no"),
        UniqueConstraint("flow_id", "flow_revision_id"),
        CheckConstraint(
            f"cause IS NULL OR cause IN ({_sql_in(STRUCTURAL_REVISION_CAUSE_VALUES)})",
            name="ck_flow_revisions_cause",
        ),
    )

    flow_revision_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    revision_index: Mapped[int] = mapped_column("revision_no", Integer)
    parent_flow_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "flow_revisions.flow_revision_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    source_compiled_plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("compiled_plans.compiled_plan_id"),
        nullable=True,
    )
    cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_dispatch_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "dispatch_turns.dispatch_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON)
    adopted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    flow: Mapped[FlowModel] = relationship(
        back_populates="flow_revisions",
        foreign_keys=[flow_id],
        lazy="selectin",
    )
    parent_revision: Mapped[FlowRevisionModel | None] = relationship(
        back_populates="child_revisions",
        foreign_keys=[parent_flow_revision_id],
        remote_side=lambda: [FlowRevisionModel.flow_revision_id],
        lazy="selectin",
    )
    child_revisions: Mapped[list[FlowRevisionModel]] = relationship(
        back_populates="parent_revision",
        foreign_keys="FlowRevisionModel.parent_flow_revision_id",
        lazy="selectin",
        order_by="FlowRevisionModel.revision_index",
    )
    created_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        back_populates="created_flow_revisions",
        foreign_keys=[created_by_dispatch_id],
        lazy="selectin",
    )
    nodes: Mapped[list[FlowNodeModel]] = relationship(
        back_populates="flow_revision",
        foreign_keys="FlowNodeModel.flow_revision_id",
        lazy="selectin",
        order_by="FlowNodeModel.order_index",
    )
    edges: Mapped[list[FlowEdgeModel]] = relationship(
        back_populates="flow_revision",
        foreign_keys="FlowEdgeModel.flow_revision_id",
        lazy="selectin",
        order_by="FlowEdgeModel.order_index",
    )
    node_plan_revisions: Mapped[list[NodePlanRevisionModel]] = relationship(
        back_populates="flow_revision",
        foreign_keys="NodePlanRevisionModel.flow_revision_id",
        lazy="selectin",
        order_by="NodePlanRevisionModel.node_plan_revision_id",
    )


class FlowNodeModel(RuntimeBase):
    __tablename__ = "flow_nodes"
    __table_args__ = (
        UniqueConstraint("flow_revision_id", "node_key"),
        CheckConstraint(
            f"node_kind IN ({_sql_in(NODE_KIND_VALUES)})",
            name="ck_flow_nodes_node_kind",
        ),
        CheckConstraint(
            f"state IN ({_sql_in(NODE_STATE_VALUES)})",
            name="ck_flow_nodes_state",
        ),
        ForeignKeyConstraint(
            ["role_key", "role_revision_no"],
            ["role_revisions.role_key", "role_revisions.revision_no"],
            name="fk_flow_nodes_role_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["policy_key", "policy_revision_no"],
            ["policy_revisions.policy_key", "policy_revisions.revision_no"],
            name="fk_flow_nodes_policy_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["flow_revision_id", "parent_node_key"],
            ["flow_nodes.flow_revision_id", "flow_nodes.node_key"],
            name="fk_flow_nodes_parent",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["current_assignment_id", "flow_node_id"],
            ["assignments.assignment_id", "assignments.flow_node_id"],
            name="fk_flow_nodes_current_assignment_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    flow_node_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_id: Mapped[str | None] = mapped_column(
        ForeignKey("flows.flow_id"),
        nullable=True,
        index=True,
    )
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    node_key: Mapped[str] = mapped_column(String(255))
    parent_flow_node_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "flow_nodes.flow_node_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    parent_node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    structural_kind: Mapped[str] = mapped_column("node_kind", String(64))
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
    state: Mapped[str] = mapped_column(String(64), default="ready")
    current_assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "assignments.assignment_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(Integer)
    flow: Mapped[FlowModel | None] = relationship(
        foreign_keys=[flow_id],
        lazy="selectin",
    )
    flow_revision: Mapped[FlowRevisionModel] = relationship(
        back_populates="nodes",
        foreign_keys=[flow_revision_id],
        lazy="selectin",
    )
    parent_node: Mapped[FlowNodeModel | None] = relationship(
        back_populates="child_nodes",
        foreign_keys=[parent_flow_node_id],
        remote_side=lambda: [FlowNodeModel.flow_node_id],
        lazy="selectin",
    )
    child_nodes: Mapped[list[FlowNodeModel]] = relationship(
        back_populates="parent_node",
        foreign_keys="FlowNodeModel.parent_flow_node_id",
        lazy="selectin",
        order_by="FlowNodeModel.order_index",
    )
    assignments: Mapped[list[AssignmentModel]] = relationship(
        "AssignmentModel",
        back_populates="flow_node",
        foreign_keys="AssignmentModel.flow_node_id",
        lazy="selectin",
        order_by="AssignmentModel.created_at",
    )
    current_assignment: Mapped[AssignmentModel | None] = relationship(
        "AssignmentModel",
        primaryjoin=(
            "and_("
            "FlowNodeModel.current_assignment_id == AssignmentModel.assignment_id, "
            "FlowNodeModel.flow_node_id == AssignmentModel.flow_node_id"
            ")"
        ),
        foreign_keys="FlowNodeModel.current_assignment_id, FlowNodeModel.flow_node_id",
        lazy="selectin",
        viewonly=True,
    )
    provided_edges: Mapped[list[FlowEdgeModel]] = relationship(
        back_populates="provider_node",
        foreign_keys="FlowEdgeModel.provider_flow_node_id",
        lazy="selectin",
        order_by="FlowEdgeModel.order_index",
    )
    consumed_edges: Mapped[list[FlowEdgeModel]] = relationship(
        back_populates="consumer_node",
        foreign_keys="FlowEdgeModel.consumer_flow_node_id",
        lazy="selectin",
        order_by="FlowEdgeModel.order_index",
    )
    node_plan_revisions: Mapped[list[NodePlanRevisionModel]] = relationship(
        back_populates="flow_node",
        foreign_keys="NodePlanRevisionModel.flow_node_id",
        lazy="selectin",
        order_by="NodePlanRevisionModel.node_plan_revision_id",
    )


class FlowEdgeModel(RuntimeBase):
    __tablename__ = "flow_edges"
    __table_args__ = (
        UniqueConstraint("flow_revision_id", "consumer_node_key", "kind", "slot"),
        CheckConstraint(
            f"kind IN ({_sql_in(FLOW_EDGE_KIND_VALUES)})",
            name="ck_flow_edges_kind",
        ),
        ForeignKeyConstraint(
            ["flow_revision_id", "provider_node_key"],
            ["flow_nodes.flow_revision_id", "flow_nodes.node_key"],
            name="fk_flow_edges_provider_node",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["flow_revision_id", "consumer_node_key"],
            ["flow_nodes.flow_revision_id", "flow_nodes.node_key"],
            name="fk_flow_edges_consumer_node",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    flow_edge_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    provider_flow_node_id: Mapped[str] = mapped_column(
        ForeignKey(
            "flow_nodes.flow_node_id",
            deferrable=True,
            initially="DEFERRED",
        )
    )
    consumer_flow_node_id: Mapped[str] = mapped_column(
        ForeignKey(
            "flow_nodes.flow_node_id",
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
    flow_revision: Mapped[FlowRevisionModel] = relationship(
        back_populates="edges",
        foreign_keys=[flow_revision_id],
        lazy="selectin",
    )
    provider_node: Mapped[FlowNodeModel] = relationship(
        back_populates="provided_edges",
        foreign_keys=[provider_flow_node_id],
        lazy="selectin",
    )
    consumer_node: Mapped[FlowNodeModel] = relationship(
        back_populates="consumed_edges",
        foreign_keys=[consumer_flow_node_id],
        lazy="selectin",
    )


class NodePlanRevisionModel(RuntimeBase):
    __tablename__ = "node_plan_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["role_key", "role_revision_no"],
            ["role_revisions.role_key", "role_revisions.revision_no"],
            name="fk_node_plan_revisions_role_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["policy_key", "policy_revision_no"],
            ["policy_revisions.policy_key", "policy_revisions.revision_no"],
            name="fk_node_plan_revisions_policy_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    node_plan_revision_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"))
    role_key: Mapped[str] = mapped_column(String(255))
    role_revision_no: Mapped[int] = mapped_column(Integer)
    role_description: Mapped[str] = mapped_column(Text)
    role_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_revision_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    flow_revision: Mapped[FlowRevisionModel] = relationship(
        back_populates="node_plan_revisions",
        foreign_keys=[flow_revision_id],
        lazy="selectin",
    )
    flow_node: Mapped[FlowNodeModel] = relationship(
        back_populates="node_plan_revisions",
        foreign_keys=[flow_node_id],
        lazy="selectin",
    )


__all__ = [
    "FlowEdgeModel",
    "FlowModel",
    "FlowNodeModel",
    "FlowRevisionModel",
    "NodePlanRevisionModel",
]
