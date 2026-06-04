from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoclaw.db.base import RuntimeBase
from autoclaw.db.models.runtime.common import utcnow

if TYPE_CHECKING:
    from autoclaw.db.models.runtime.assignment.execution import AssignmentModel, AttemptModel
    from autoclaw.db.models.runtime.dispatch.turns import DispatchTurnModel
    from autoclaw.db.models.runtime.flow.graph import FlowNodeModel


class ContextItemModel(RuntimeBase):
    __tablename__ = "context_items"

    context_item_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("flow_nodes.flow_node_id"),
        nullable=True,
    )
    item_kind: Mapped[str] = mapped_column(String(64))
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class NodeSessionModel(RuntimeBase):
    __tablename__ = "node_sessions"

    node_session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_id"),
        nullable=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=True)
    dispatch_id: Mapped[str | None] = mapped_column(
        ForeignKey("dispatch_turns.dispatch_id"),
        nullable=True,
    )
    session_key: Mapped[str] = mapped_column(String(255), index=True)
    session_status: Mapped[str] = mapped_column(String(64))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flow_node: Mapped[FlowNodeModel] = relationship(
        "FlowNodeModel",
        foreign_keys=[flow_node_id],
        lazy="selectin",
    )
    assignment: Mapped[AssignmentModel | None] = relationship(
        "AssignmentModel",
        foreign_keys=[assignment_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel | None] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )
    dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        back_populates="node_sessions",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )


class WorkspaceRootLeaseModel(RuntimeBase):
    __tablename__ = "workspace_root_leases"

    workspace_root_lease_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    normalized_workspace_root_path: Mapped[str] = mapped_column(Text, unique=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    lease_status: Mapped[str] = mapped_column(String(64))
    leased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BudgetCounterModel(RuntimeBase):
    __tablename__ = "budget_counters"
    __table_args__ = (
        CheckConstraint("remaining >= 0", name="ck_budget_counters_remaining_nonnegative"),
        CheckConstraint("lock_version >= 1", name="ck_budget_counters_lock_version_positive"),
    )

    budget_counter_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    budget_family: Mapped[str] = mapped_column(String(255))
    scope_kind: Mapped[str] = mapped_column(String(64))
    flow_id: Mapped[str | None] = mapped_column(ForeignKey("flows.flow_id"), nullable=True)
    flow_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("flow_nodes.flow_node_id"), nullable=True
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_id"),
        nullable=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=True)
    initial_limit: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    exhausted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_version: Mapped[int] = mapped_column(Integer, default=1)


__all__ = [
    "BudgetCounterModel",
    "ContextItemModel",
    "NodeSessionModel",
    "WorkspaceRootLeaseModel",
]
