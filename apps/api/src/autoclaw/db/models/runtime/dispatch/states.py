from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoclaw.db.base import RuntimeBase
from autoclaw.db.models.runtime.common import (
    DISPATCH_DELIVERY_STATUS_VALUES,
    PROVIDER_EVENT_KIND_VALUES,
    PROVIDER_EVENT_SOURCE_VALUES,
    sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from autoclaw.db.models.runtime.assignment.execution import AttemptModel
    from autoclaw.db.models.runtime.dispatch.turns import DispatchTurnModel


class DispatchDeliveryStateModel(RuntimeBase):
    __tablename__ = "dispatch_delivery_states"
    __table_args__ = (
        CheckConstraint(
            f"transport_state IN ({sql_in(DISPATCH_DELIVERY_STATUS_VALUES)})",
            name="ck_dispatch_delivery_states_transport_state",
        ),
        ForeignKeyConstraint(
            ["previous_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_delivery_states_previous_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["superseded_by_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_delivery_states_superseded_by_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    dispatch_id: Mapped[str] = mapped_column(
        ForeignKey(
            "dispatch_turns.dispatch_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        primary_key=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_key"),
        nullable=True,
    )
    node_key: Mapped[str] = mapped_column(String(255))
    transport_family: Mapped[str] = mapped_column(String(255))
    transport_state: Mapped[str] = mapped_column(String(255))
    last_provider_event_kind: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_final_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_provider_signal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_controller_progress_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_controller_terminal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    dispatch: Mapped[DispatchTurnModel] = relationship(
        "DispatchTurnModel",
        back_populates="delivery_state",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel | None] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )
    previous_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[previous_dispatch_id],
        lazy="selectin",
    )
    superseded_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[superseded_by_dispatch_id],
        lazy="selectin",
    )


class DispatchContinuityStateModel(RuntimeBase):
    __tablename__ = "dispatch_continuity_states"

    dispatch_id: Mapped[str] = mapped_column(
        ForeignKey(
            "dispatch_turns.dispatch_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        primary_key=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_key"),
        nullable=True,
    )
    node_key: Mapped[str] = mapped_column(String(255))
    session_key_present: Mapped[bool] = mapped_column(Boolean, default=False)
    invalidation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    dispatch: Mapped[DispatchTurnModel] = relationship(
        "DispatchTurnModel",
        back_populates="continuity_state",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel | None] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )


class DispatchWatchdogStateModel(RuntimeBase):
    __tablename__ = "dispatch_watchdog_states"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recovery_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_watchdog_states_recovery_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["previous_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_watchdog_states_previous_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["superseded_by_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_dispatch_watchdog_states_superseded_by_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    dispatch_id: Mapped[str] = mapped_column(
        ForeignKey(
            "dispatch_turns.dispatch_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        primary_key=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.assignment_key"),
        nullable=True,
    )
    node_key: Mapped[str] = mapped_column(String(255))
    watchdog_state: Mapped[str] = mapped_column(String(255))
    current_watchdog_kind: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_watchdog_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recovery_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    dispatch: Mapped[DispatchTurnModel] = relationship(
        "DispatchTurnModel",
        back_populates="watchdog_state",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel | None] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )
    recovery_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[recovery_dispatch_id],
        lazy="selectin",
    )
    previous_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[previous_dispatch_id],
        lazy="selectin",
    )
    superseded_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        foreign_keys=[superseded_by_dispatch_id],
        lazy="selectin",
    )


class ProviderEventRecordModel(RuntimeBase):
    __tablename__ = "provider_event_records"
    __table_args__ = (
        UniqueConstraint("dispatch_id", "event_no"),
        CheckConstraint(
            f"event_source IN ({sql_in(PROVIDER_EVENT_SOURCE_VALUES)})",
            name="ck_provider_event_records_event_source",
        ),
        CheckConstraint(
            f"event_kind IN ({sql_in(PROVIDER_EVENT_KIND_VALUES)})",
            name="ck_provider_event_records_event_kind",
        ),
        Index("ix_provider_event_records_dispatch_event_no", "dispatch_id", "event_no"),
        Index("ix_provider_event_records_dispatch_observed_at", "dispatch_id", "observed_at"),
    )

    provider_event_record_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    dispatch_id: Mapped[str] = mapped_column(ForeignKey("dispatch_turns.dispatch_id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    event_no: Mapped[int] = mapped_column(Integer)
    event_source: Mapped[str] = mapped_column(String(64))
    event_kind: Mapped[str] = mapped_column(String(255))
    provider_event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_payload_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        "observed_at", DateTime(timezone=True), default=utcnow
    )
    provider_occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dispatch: Mapped[DispatchTurnModel] = relationship(
        "DispatchTurnModel",
        back_populates="provider_events",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )


__all__ = [
    "DispatchContinuityStateModel",
    "DispatchDeliveryStateModel",
    "DispatchWatchdogStateModel",
    "ProviderEventRecordModel",
]
