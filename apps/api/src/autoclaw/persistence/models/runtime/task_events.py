from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoclaw.persistence.base import RuntimeBase
from autoclaw.persistence.models.runtime.common import sql_in, utcnow
from autoclaw.runtime.contracts import TaskEventSource, TaskEventType

if TYPE_CHECKING:
    from autoclaw.persistence.models.runtime.assignment.execution import AttemptModel
    from autoclaw.persistence.models.runtime.dispatch.turns import DispatchTurnModel
    from autoclaw.persistence.models.runtime.flow.runtime import FlowRevisionModel
    from autoclaw.persistence.models.runtime.task import TaskModel

TASK_EVENT_SOURCE_VALUES = tuple(source.value for source in TaskEventSource)
LEGACY_PROVIDER_EVENT_NORMALIZED_TYPE = "provider_event_normalized"
LEGACY_PROVIDER_RESOLUTION_RECORDED_TYPE = "provider_resolution_recorded"
TASK_EVENT_TYPE_VALUES = (
    *(event_type.value for event_type in TaskEventType),
    LEGACY_PROVIDER_EVENT_NORMALIZED_TYPE,
    LEGACY_PROVIDER_RESOLUTION_RECORDED_TYPE,
)


class TaskEventModel(RuntimeBase):
    __tablename__ = "task_events"
    __table_args__ = (
        CheckConstraint(
            f"event_source IN ({sql_in(TASK_EVENT_SOURCE_VALUES)})",
            name="ck_task_events_event_source",
        ),
        CheckConstraint(
            f"event_type IN ({sql_in(TASK_EVENT_TYPE_VALUES)})",
            name="ck_task_events_event_type",
        ),
        Index("ix_task_events_task_seq", "task_id", "event_seq", unique=True),
        Index("ix_task_events_task_event", "task_id", "event_id"),
    )

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_seq: Mapped[int] = mapped_column(Integer)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(255))
    event_source: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    flow_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("flow_revisions.flow_revision_id"),
        nullable=True,
        index=True,
    )
    dispatch_id: Mapped[str | None] = mapped_column(
        ForeignKey("dispatch_turns.dispatch_id"),
        nullable=True,
        index=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("attempts.attempt_id"),
        nullable=True,
        index=True,
    )
    node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    prev_event_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(255))
    task: Mapped[TaskModel] = relationship(
        "TaskModel",
        back_populates="task_events",
        foreign_keys=[task_id],
    )
    flow_revision: Mapped[FlowRevisionModel | None] = relationship(
        "FlowRevisionModel",
        foreign_keys=[flow_revision_id],
    )
    dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[dispatch_id],
    )
    attempt: Mapped[AttemptModel | None] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
    )


__all__ = ["TaskEventModel"]
