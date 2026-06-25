from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoclaw.persistence.base import RuntimeBase
from autoclaw.persistence.models.runtime.common import (
    HUMAN_REQUEST_KIND_VALUES,
    HUMAN_REQUEST_STATUS_VALUES,
    sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from autoclaw.persistence.models.runtime.assignment.execution import (
        AssignmentModel,
        AttemptModel,
    )
    from autoclaw.persistence.models.runtime.dispatch.turns import DispatchTurnModel
    from autoclaw.persistence.models.runtime.flow.graph import FlowNodeModel
    from autoclaw.persistence.models.runtime.flow.runtime import FlowModel, FlowRevisionModel
    from autoclaw.persistence.models.runtime.task import TaskModel
    from autoclaw.persistence.models.runtime.waiting import FlowWaitStateModel


class PendingHumanRequestModel(RuntimeBase):
    __tablename__ = "pending_human_requests"
    __table_args__ = (
        CheckConstraint(
            f"kind IN ({sql_in(HUMAN_REQUEST_KIND_VALUES)})",
            name="ck_pending_human_requests_kind",
        ),
        CheckConstraint(
            f"status IN ({sql_in(HUMAN_REQUEST_STATUS_VALUES)})",
            name="ck_pending_human_requests_status",
        ),
        ForeignKeyConstraint(
            ["flow_id", "flow_revision_id"],
            ["flow_revisions.flow_id", "flow_revisions.flow_revision_id"],
            name="fk_pending_human_requests_flow_revision_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["flow_id", "flow_revision_id", "flow_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.flow_revision_id", "flow_nodes.flow_node_id"],
            name="fk_pending_human_requests_flow_node_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["attempt_id", "assignment_id"],
            ["attempts.attempt_id", "attempts.assignment_id"],
            name="fk_pending_human_requests_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_pending_human_requests_task_status", "task_id", "status"),
        Index("ix_pending_human_requests_dispatch_status", "dispatch_id", "status"),
        Index("ix_pending_human_requests_flow_node_status", "flow_node_id", "status"),
    )

    request_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    dispatch_id: Mapped[str] = mapped_column(ForeignKey("dispatch_turns.dispatch_id"), index=True)
    requester_node_key: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    items_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    timeout_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    suggested_human_instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    task: Mapped[TaskModel] = relationship("TaskModel", foreign_keys=[task_id], lazy="selectin")
    flow: Mapped[FlowModel] = relationship("FlowModel", foreign_keys=[flow_id], lazy="selectin")
    flow_revision: Mapped[FlowRevisionModel] = relationship(
        "FlowRevisionModel",
        foreign_keys=[flow_revision_id],
        lazy="selectin",
    )
    flow_node: Mapped[FlowNodeModel] = relationship(
        "FlowNodeModel",
        foreign_keys=[flow_node_id],
        lazy="selectin",
    )
    assignment: Mapped[AssignmentModel] = relationship(
        "AssignmentModel",
        foreign_keys=[assignment_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )
    dispatch: Mapped[DispatchTurnModel] = relationship(
        "DispatchTurnModel",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    wait_state: Mapped[FlowWaitStateModel | None] = relationship(
        "FlowWaitStateModel",
        back_populates="pending_human_request",
        foreign_keys="FlowWaitStateModel.pending_human_request_id",
        lazy="selectin",
        uselist=False,
    )


__all__ = ["PendingHumanRequestModel"]
