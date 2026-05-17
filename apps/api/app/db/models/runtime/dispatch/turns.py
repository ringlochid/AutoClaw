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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import RuntimeBase
from app.db.models.runtime.common import (
    CHECKPOINT_OUTCOME_VALUES,
    DISPATCH_CONTROL_STATE_VALUES,
    DISPATCH_DELIVERY_STATUS_VALUES,
    RELEASE_PRECONDITION_KIND_VALUES,
    sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from app.db.models.runtime.assignment.execution import AssignmentModel, AttemptModel
    from app.db.models.runtime.dispatch.states import (
        DispatchContinuityStateModel,
        DispatchDeliveryStateModel,
        DispatchWatchdogStateModel,
        ProviderEventRecordModel,
    )
    from app.db.models.runtime.dispatch.support import NodeSessionModel
    from app.db.models.runtime.flow.graph import FlowNodeModel
    from app.db.models.runtime.flow.runtime import FlowModel, FlowRevisionModel


class DispatchTurnModel(RuntimeBase):
    __tablename__ = "dispatch_turns"
    __table_args__ = (
        CheckConstraint(
            f"delivery_status IN ({sql_in(DISPATCH_DELIVERY_STATUS_VALUES)})",
            name="ck_dispatch_turns_delivery_status",
        ),
        CheckConstraint(
            f"control_state IN ({sql_in(DISPATCH_CONTROL_STATE_VALUES)})",
            name="ck_dispatch_turns_control_state",
        ),
        CheckConstraint(
            "release_precondition_kind IS NULL OR "
            f"release_precondition_kind IN ({sql_in(RELEASE_PRECONDITION_KIND_VALUES)})",
            name="ck_dispatch_turns_release_precondition_kind",
        ),
        CheckConstraint(
            "accepted_boundary IS NULL OR "
            f"accepted_boundary IN ('yield', {sql_in(CHECKPOINT_OUTCOME_VALUES)})",
            name="ck_dispatch_turns_accepted_boundary",
        ),
        CheckConstraint(
            "flow_node_id IS NULL OR flow_revision_id IS NOT NULL",
            name="ck_dispatch_turns_flow_node_requires_flow_revision",
        ),
        CheckConstraint(
            "assignment_id IS NULL OR flow_node_id IS NOT NULL",
            name="ck_dispatch_turns_assignment_requires_flow_node",
        ),
        CheckConstraint(
            "attempt_id IS NULL OR assignment_id IS NOT NULL",
            name="ck_dispatch_turns_attempt_requires_assignment",
        ),
        ForeignKeyConstraint(
            ["flow_id", "flow_revision_id"],
            ["flow_revisions.flow_id", "flow_revisions.flow_revision_id"],
            name="fk_dispatch_turns_flow_revision_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["flow_id", "flow_revision_id", "flow_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.flow_revision_id", "flow_nodes.flow_node_id"],
            name="fk_dispatch_turns_flow_node_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["attempt_id", "assignment_id"],
            ["attempts.attempt_id", "attempts.assignment_id"],
            name="fk_dispatch_turns_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["previous_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_turns_previous_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["superseded_by_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_turns_superseded_by_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["staged_child_assignment_id"],
            ["assignments.assignment_id"],
            name="fk_dispatch_turns_staged_child_assignment",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["release_precondition_flow_revision_id"],
            ["flow_revisions.flow_revision_id"],
            name="fk_dispatch_turns_release_precondition_flow_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["release_precondition_assignment_id"],
            ["assignments.assignment_id"],
            name="fk_dispatch_turns_release_precondition_assignment",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_dispatch_turns_assignment_key", "assignment_key"),
        Index("ix_dispatch_turns_delivery_status", "delivery_status"),
        UniqueConstraint("flow_id", "dispatch_id"),
        Index("ix_dispatch_turns_task_node_rendered_at", "task_id", "node_key", "rendered_at"),
    )

    dispatch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    flow_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("flow_revisions.flow_revision_id"),
        nullable=True,
    )
    flow_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("flow_nodes.flow_node_id"),
        nullable=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_id"),
        nullable=True,
    )
    assignment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=True)
    prompt_name: Mapped[str] = mapped_column(String(255))
    delivery_status: Mapped[str] = mapped_column(String(64))
    control_state: Mapped[str] = mapped_column(String(64))
    gateway_session_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gateway_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    control_state_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    abort_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fenced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prompt_path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(255))
    previous_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    staged_child_assignment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_precondition_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    release_precondition_flow_revision_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    release_precondition_assignment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    release_precondition_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    relevant_checkpoint_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("attempts.attempt_id"),
        nullable=True,
    )
    release_precondition_descendant_refs_json: Mapped[list[dict[str, object]] | None] = (
        mapped_column(JSON, nullable=True)
    )
    accepted_boundary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    closed_by_boundary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    rendered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flow: Mapped[FlowModel] = relationship(
        "FlowModel",
        back_populates="dispatch_turns",
        foreign_keys=[flow_id],
        lazy="selectin",
    )
    flow_revision: Mapped[FlowRevisionModel | None] = relationship(
        "FlowRevisionModel",
        foreign_keys=[flow_revision_id],
        lazy="selectin",
    )
    flow_node: Mapped[FlowNodeModel | None] = relationship(
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
        back_populates="dispatch_turns",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )
    previous_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        back_populates="next_dispatches",
        foreign_keys=[previous_dispatch_id],
        remote_side=lambda: [DispatchTurnModel.dispatch_id],
        lazy="selectin",
    )
    next_dispatches: Mapped[list[DispatchTurnModel]] = relationship(
        back_populates="previous_dispatch",
        foreign_keys="DispatchTurnModel.previous_dispatch_id",
        lazy="selectin",
        order_by="DispatchTurnModel.rendered_at",
    )
    superseded_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        back_populates="superseded_dispatches",
        foreign_keys=[superseded_by_dispatch_id],
        remote_side=lambda: [DispatchTurnModel.dispatch_id],
        lazy="selectin",
    )
    superseded_dispatches: Mapped[list[DispatchTurnModel]] = relationship(
        back_populates="superseded_by_dispatch",
        foreign_keys="DispatchTurnModel.superseded_by_dispatch_id",
        lazy="selectin",
        order_by="DispatchTurnModel.rendered_at",
    )
    staged_child_assignment: Mapped[AssignmentModel | None] = relationship(
        "AssignmentModel",
        foreign_keys=[staged_child_assignment_id],
        lazy="selectin",
    )
    release_precondition_flow_revision: Mapped[FlowRevisionModel | None] = relationship(
        "FlowRevisionModel",
        foreign_keys=[release_precondition_flow_revision_id],
        lazy="selectin",
    )
    release_precondition_assignment: Mapped[AssignmentModel | None] = relationship(
        "AssignmentModel",
        foreign_keys=[release_precondition_assignment_id],
        lazy="selectin",
    )
    delivery_state: Mapped[DispatchDeliveryStateModel | None] = relationship(
        "DispatchDeliveryStateModel",
        back_populates="dispatch",
        foreign_keys="DispatchDeliveryStateModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    continuity_state: Mapped[DispatchContinuityStateModel | None] = relationship(
        "DispatchContinuityStateModel",
        back_populates="dispatch",
        foreign_keys="DispatchContinuityStateModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    watchdog_state: Mapped[DispatchWatchdogStateModel | None] = relationship(
        "DispatchWatchdogStateModel",
        back_populates="dispatch",
        foreign_keys="DispatchWatchdogStateModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    provider_events: Mapped[list[ProviderEventRecordModel]] = relationship(
        "ProviderEventRecordModel",
        back_populates="dispatch",
        foreign_keys="ProviderEventRecordModel.dispatch_id",
        lazy="selectin",
        order_by="ProviderEventRecordModel.event_no",
    )
    node_sessions: Mapped[list[NodeSessionModel]] = relationship(
        "NodeSessionModel",
        back_populates="dispatch",
        foreign_keys="NodeSessionModel.dispatch_id",
        lazy="selectin",
        order_by="NodeSessionModel.opened_at",
    )
    created_assignments: Mapped[list[AssignmentModel]] = relationship(
        "AssignmentModel",
        back_populates="created_by_dispatch",
        foreign_keys="AssignmentModel.created_by_dispatch_id",
        lazy="selectin",
        order_by="AssignmentModel.created_at",
    )
    created_flow_revisions: Mapped[list[FlowRevisionModel]] = relationship(
        "FlowRevisionModel",
        back_populates="created_by_dispatch",
        foreign_keys="FlowRevisionModel.created_by_dispatch_id",
        lazy="selectin",
        order_by="FlowRevisionModel.revision_index",
    )


__all__ = ["DispatchTurnModel"]
