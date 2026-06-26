from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoclaw.persistence.base import RuntimeBase
from autoclaw.persistence.models.runtime.common import COMMAND_RUN_STATE_VALUES, sql_in, utcnow
from autoclaw.runtime.contracts import TaskEventSource

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


TERMINAL_COMMAND_RUN_STATE_VALUES = ("succeeded", "failed", "timed_out", "cancelled")
TERMINAL_COMMAND_RUN_EVENT_SOURCE_VALUES = tuple(source.value for source in TaskEventSource)


class CommandRunModel(RuntimeBase):
    __tablename__ = "command_runs"
    __table_args__ = (
        CheckConstraint(
            f"state IN ({sql_in(COMMAND_RUN_STATE_VALUES)})",
            name="ck_command_runs_state",
        ),
        CheckConstraint(
            "timeout_seconds IS NULL OR timeout_seconds >= 1",
            name="ck_command_runs_timeout_seconds",
        ),
        CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled') "
            "AND ended_at IS NOT NULL AND terminal_summary IS NOT NULL "
            "AND terminal_event_source IS NOT NULL) OR "
            "(state NOT IN ('succeeded', 'failed', 'timed_out', 'cancelled') "
            "AND ended_at IS NULL AND terminal_summary IS NULL "
            "AND terminal_exit_code IS NULL AND terminal_signal IS NULL "
            "AND terminal_log_ref IS NULL AND terminal_event_source IS NULL "
            "AND terminal_actor_ref IS NULL)",
            name="ck_command_runs_terminal_result",
        ),
        CheckConstraint(
            "terminal_event_source IS NULL OR terminal_event_source IN "
            f"({sql_in(TERMINAL_COMMAND_RUN_EVENT_SOURCE_VALUES)})",
            name="ck_command_runs_terminal_event_source",
        ),
        ForeignKeyConstraint(
            ["flow_id", "flow_revision_id"],
            ["flow_revisions.flow_id", "flow_revisions.flow_revision_id"],
            name="fk_command_runs_flow_revision_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["flow_id", "flow_revision_id", "flow_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.flow_revision_id", "flow_nodes.flow_node_id"],
            name="fk_command_runs_flow_node_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["attempt_id", "assignment_id"],
            ["attempts.attempt_id", "attempts.assignment_id"],
            name="fk_command_runs_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_command_runs_task_created", "task_id", "created_at", "run_id"),
        Index("ix_command_runs_task_state", "task_id", "state"),
        Index("ix_command_runs_dispatch_state", "dispatch_id", "state"),
        Index("ix_command_runs_flow_node_state", "flow_node_id", "state"),
    )

    run_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    dispatch_id: Mapped[str] = mapped_column(ForeignKey("dispatch_turns.dispatch_id"), index=True)
    requester_node_key: Mapped[str] = mapped_column(String(255))
    command: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    workdir: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(String(64), index=True)
    latest_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_log_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    terminal_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    terminal_exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    terminal_signal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    terminal_log_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    terminal_event_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    terminal_actor_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_requested_by_actor_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        back_populates="command_run",
        foreign_keys="FlowWaitStateModel.command_run_id",
        lazy="selectin",
        uselist=False,
    )


__all__ = ["TERMINAL_COMMAND_RUN_STATE_VALUES", "CommandRunModel"]
