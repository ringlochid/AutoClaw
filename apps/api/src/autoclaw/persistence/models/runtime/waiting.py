from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoclaw.persistence.base import RuntimeBase
from autoclaw.persistence.models.runtime.common import WAITING_CAUSE_VALUES, sql_in, utcnow

if TYPE_CHECKING:
    from autoclaw.persistence.models.runtime.command_runs import CommandRunModel
    from autoclaw.persistence.models.runtime.dispatch.turns import DispatchTurnModel
    from autoclaw.persistence.models.runtime.flow.runtime import FlowModel
    from autoclaw.persistence.models.runtime.human_requests import PendingHumanRequestModel
    from autoclaw.persistence.models.runtime.task import TaskModel


class FlowWaitStateModel(RuntimeBase):
    __tablename__ = "flow_wait_states"
    __table_args__ = (
        CheckConstraint(
            f"waiting_cause IN ({sql_in(WAITING_CAUSE_VALUES)})",
            name="ck_flow_wait_states_waiting_cause",
        ),
        CheckConstraint(
            "waiting_cause != 'waiting_for_human_request' OR pending_human_request_id IS NOT NULL",
            name="ck_flow_wait_states_human_request_source",
        ),
        CheckConstraint(
            "waiting_cause != 'waiting_for_command_run' OR command_run_id IS NOT NULL",
            name="ck_flow_wait_states_command_run_source",
        ),
        Index("ix_flow_wait_states_task_cause", "task_id", "waiting_cause"),
    )

    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    waiting_cause: Mapped[str] = mapped_column(String(64))
    pending_human_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("pending_human_requests.request_id"),
        nullable=True,
    )
    command_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("command_runs.run_id"),
        nullable=True,
    )
    created_by_dispatch_id: Mapped[str | None] = mapped_column(
        ForeignKey("dispatch_turns.dispatch_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    flow: Mapped[FlowModel] = relationship("FlowModel", foreign_keys=[flow_id], lazy="selectin")
    task: Mapped[TaskModel] = relationship("TaskModel", foreign_keys=[task_id], lazy="selectin")
    pending_human_request: Mapped[PendingHumanRequestModel | None] = relationship(
        "PendingHumanRequestModel",
        back_populates="wait_state",
        foreign_keys=[pending_human_request_id],
        lazy="selectin",
    )
    command_run: Mapped[CommandRunModel | None] = relationship(
        "CommandRunModel",
        back_populates="wait_state",
        foreign_keys=[command_run_id],
        lazy="selectin",
    )
    created_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[created_by_dispatch_id],
        lazy="selectin",
    )


__all__ = ["FlowWaitStateModel"]
