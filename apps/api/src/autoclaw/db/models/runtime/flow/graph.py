from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship, remote

from autoclaw.db.base import RuntimeBase
from autoclaw.db.models.runtime.common import (
    FLOW_EDGE_KIND_VALUES,
    NODE_KIND_VALUES,
    NODE_STATE_VALUES,
    sql_in,
)

if TYPE_CHECKING:
    from autoclaw.db.models.runtime.assignment.execution import AssignmentModel
    from autoclaw.db.models.runtime.flow.runtime import FlowModel, FlowRevisionModel


class FlowNodeModel(RuntimeBase):
    __tablename__ = "flow_nodes"
    __table_args__ = (
        UniqueConstraint("flow_id", "flow_revision_id", "flow_node_id"),
        UniqueConstraint("flow_revision_id", "node_key"),
        CheckConstraint(
            f"node_kind IN ({sql_in(NODE_KIND_VALUES)})",
            name="ck_flow_nodes_node_kind",
        ),
        CheckConstraint(
            f"state IN ({sql_in(NODE_STATE_VALUES)})",
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
            ["flow_id", "flow_revision_id", "parent_flow_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.flow_revision_id", "flow_nodes.flow_node_id"],
            name="fk_flow_nodes_parent_owner",
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
    parent_flow_node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
        "FlowModel",
        foreign_keys=[flow_id],
        lazy="selectin",
    )
    flow_revision: Mapped[FlowRevisionModel] = relationship(
        "FlowRevisionModel",
        back_populates="nodes",
        foreign_keys=[flow_revision_id],
        lazy="selectin",
    )
    parent_node: Mapped[FlowNodeModel | None] = relationship(
        back_populates="child_nodes",
        primaryjoin=lambda: and_(
            foreign(FlowNodeModel.parent_flow_node_id) == remote(FlowNodeModel.flow_node_id),
            foreign(FlowNodeModel.flow_revision_id) == remote(FlowNodeModel.flow_revision_id),
            foreign(FlowNodeModel.flow_id) == remote(FlowNodeModel.flow_id),
        ),
        foreign_keys=lambda: [
            FlowNodeModel.parent_flow_node_id,
            FlowNodeModel.flow_revision_id,
            FlowNodeModel.flow_id,
        ],
        remote_side=lambda: [
            FlowNodeModel.flow_node_id,
            FlowNodeModel.flow_revision_id,
            FlowNodeModel.flow_id,
        ],
        lazy="selectin",
        overlaps="flow,flow_revision,nodes",
    )
    child_nodes: Mapped[list[FlowNodeModel]] = relationship(
        back_populates="parent_node",
        foreign_keys=lambda: [
            FlowNodeModel.parent_flow_node_id,
            FlowNodeModel.flow_revision_id,
            FlowNodeModel.flow_id,
        ],
        lazy="selectin",
        order_by="FlowNodeModel.order_index",
        overlaps="flow,flow_revision,nodes",
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
            f"kind IN ({sql_in(FLOW_EDGE_KIND_VALUES)})",
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
        "FlowRevisionModel",
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
        "FlowRevisionModel",
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
    "FlowNodeModel",
    "NodePlanRevisionModel",
]
