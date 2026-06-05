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
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship, remote

from autoclaw.persistence.base import RuntimeBase
from autoclaw.persistence.models.runtime.common import (
    FLOW_STATUS_VALUES,
    STRUCTURAL_REVISION_CAUSE_VALUES,
    sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from autoclaw.persistence.models.runtime.dispatch.turns import DispatchTurnModel
    from autoclaw.persistence.models.runtime.flow.graph import (
        FlowEdgeModel,
        FlowNodeModel,
        NodePlanRevisionModel,
    )


class FlowModel(RuntimeBase):
    __tablename__ = "flows"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in(FLOW_STATUS_VALUES)})",
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
        ForeignKeyConstraint(
            ["flow_id", "parent_flow_revision_id"],
            ["flow_revisions.flow_id", "flow_revisions.flow_revision_id"],
            name="fk_flow_revisions_parent_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            f"cause IS NULL OR cause IN ({sql_in(STRUCTURAL_REVISION_CAUSE_VALUES)})",
            name="ck_flow_revisions_cause",
        ),
    )

    flow_revision_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    revision_index: Mapped[int] = mapped_column("revision_no", Integer)
    parent_flow_revision_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
        primaryjoin=lambda: and_(
            foreign(FlowRevisionModel.parent_flow_revision_id)
            == remote(FlowRevisionModel.flow_revision_id),
            foreign(FlowRevisionModel.flow_id) == remote(FlowRevisionModel.flow_id),
        ),
        foreign_keys=lambda: [
            FlowRevisionModel.parent_flow_revision_id,
            FlowRevisionModel.flow_id,
        ],
        remote_side=lambda: [
            FlowRevisionModel.flow_revision_id,
            FlowRevisionModel.flow_id,
        ],
        lazy="selectin",
        overlaps="flow,flow_revisions",
    )
    child_revisions: Mapped[list[FlowRevisionModel]] = relationship(
        back_populates="parent_revision",
        foreign_keys=lambda: [
            FlowRevisionModel.parent_flow_revision_id,
            FlowRevisionModel.flow_id,
        ],
        lazy="selectin",
        order_by="FlowRevisionModel.revision_index",
        overlaps="flow,flow_revisions",
    )
    created_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        back_populates="created_flow_revisions",
        foreign_keys=[created_by_dispatch_id],
        lazy="selectin",
    )
    nodes: Mapped[list[FlowNodeModel]] = relationship(
        "FlowNodeModel",
        back_populates="flow_revision",
        foreign_keys="FlowNodeModel.flow_revision_id",
        lazy="selectin",
        order_by="FlowNodeModel.order_index",
    )
    edges: Mapped[list[FlowEdgeModel]] = relationship(
        "FlowEdgeModel",
        back_populates="flow_revision",
        foreign_keys="FlowEdgeModel.flow_revision_id",
        lazy="selectin",
        order_by="FlowEdgeModel.order_index",
    )
    node_plan_revisions: Mapped[list[NodePlanRevisionModel]] = relationship(
        "NodePlanRevisionModel",
        back_populates="flow_revision",
        foreign_keys="NodePlanRevisionModel.flow_revision_id",
        lazy="selectin",
        order_by="NodePlanRevisionModel.node_plan_revision_id",
    )


__all__ = [
    "FlowModel",
    "FlowRevisionModel",
]
