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

from app.db.base import RuntimeBase
from app.db.models.runtime.shared import (
    CHECKPOINT_OUTCOME_VALUES,
    DISPATCH_CALLBACK_BINDING_STATUS_VALUES,
    DISPATCH_CONTROL_STATE_VALUES,
    DISPATCH_DELIVERY_STATUS_VALUES,
    DISPATCH_OBSERVATION_STATE_VALUES,
    DISPATCH_PHASE_VALUES,
    DISPATCH_STATUS_VALUES,
    PROMPT_SEND_MODE_VALUES,
    PROVIDER_EVENT_KIND_VALUES,
    PROVIDER_EVENT_SOURCE_VALUES,
    RELEASE_PRECONDITION_KIND_VALUES,
    STAGED_CONTINUATION_KIND_VALUES,
    _sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from app.db.models.runtime.assignment import AssignmentModel, AttemptModel
    from app.db.models.runtime.flow import FlowModel, FlowNodeModel, FlowRevisionModel


class DispatchTurnModel(RuntimeBase):
    __tablename__ = "dispatch_turns"
    __table_args__ = (
        CheckConstraint(
            f"phase IN ({_sql_in(DISPATCH_PHASE_VALUES)})",
            name="ck_dispatch_turns_phase",
        ),
        CheckConstraint(
            f"status IN ({_sql_in(DISPATCH_STATUS_VALUES)})",
            name="ck_dispatch_turns_status",
        ),
        CheckConstraint(
            f"send_mode IN ({_sql_in(PROMPT_SEND_MODE_VALUES)})",
            name="ck_dispatch_turns_send_mode",
        ),
        CheckConstraint(
            f"delivery_status IN ({_sql_in(DISPATCH_DELIVERY_STATUS_VALUES)})",
            name="ck_dispatch_turns_delivery_status",
        ),
        CheckConstraint(
            f"control_state IN ({_sql_in(DISPATCH_CONTROL_STATE_VALUES)})",
            name="ck_dispatch_turns_control_state",
        ),
        CheckConstraint(
            "staged_continuation_kind IS NULL OR "
            f"staged_continuation_kind IN ({_sql_in(STAGED_CONTINUATION_KIND_VALUES)})",
            name="ck_dispatch_turns_staged_continuation_kind",
        ),
        CheckConstraint(
            "release_precondition_kind IS NULL OR "
            f"release_precondition_kind IN ({_sql_in(RELEASE_PRECONDITION_KIND_VALUES)})",
            name="ck_dispatch_turns_release_precondition_kind",
        ),
        CheckConstraint(
            "accepted_boundary IS NULL OR "
            f"accepted_boundary IN ('yield', {_sql_in(CHECKPOINT_OUTCOME_VALUES)})",
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
        Index("ix_dispatch_turns_send_mode", "send_mode"),
        Index("ix_dispatch_turns_delivery_status", "delivery_status"),
        UniqueConstraint(
            "dispatch_id",
            "attempt_id",
            "assignment_id",
            "task_id",
            name="uq_dispatch_turns_callback_binding_tuple",
        ),
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
    phase: Mapped[str] = mapped_column(String(64), default="execution")
    status: Mapped[str] = mapped_column(String(64), default="accepted")
    prompt_name: Mapped[str] = mapped_column(String(255))
    send_mode: Mapped[str] = mapped_column(String(64))
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
    staged_continuation_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
        back_populates="dispatch",
        foreign_keys="DispatchDeliveryStateModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    continuity_state: Mapped[DispatchContinuityStateModel | None] = relationship(
        back_populates="dispatch",
        foreign_keys="DispatchContinuityStateModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    watchdog_state: Mapped[DispatchWatchdogStateModel | None] = relationship(
        back_populates="dispatch",
        foreign_keys="DispatchWatchdogStateModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    provider_events: Mapped[list[ProviderEventRecordModel]] = relationship(
        back_populates="dispatch",
        foreign_keys="ProviderEventRecordModel.dispatch_id",
        lazy="selectin",
        order_by="ProviderEventRecordModel.event_no",
    )
    callback_binding: Mapped[DispatchCallbackBindingModel | None] = relationship(
        back_populates="dispatch",
        foreign_keys="DispatchCallbackBindingModel.dispatch_id",
        lazy="selectin",
        uselist=False,
    )
    node_sessions: Mapped[list[NodeSessionModel]] = relationship(
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


class DispatchCallbackBindingModel(RuntimeBase):
    __tablename__ = "dispatch_callback_bindings"
    __table_args__ = (
        CheckConstraint(
            f"binding_status IN ({_sql_in(DISPATCH_CALLBACK_BINDING_STATUS_VALUES)})",
            name="ck_dispatch_callback_bindings_status",
        ),
        ForeignKeyConstraint(
            ["dispatch_id", "attempt_id", "assignment_id", "task_id"],
            [
                "dispatch_turns.dispatch_id",
                "dispatch_turns.attempt_id",
                "dispatch_turns.assignment_id",
                "dispatch_turns.task_id",
            ],
            name="fk_dispatch_callback_bindings_dispatch_tuple",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    dispatch_callback_binding_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    dispatch_id: Mapped[str] = mapped_column(
        ForeignKey("dispatch_turns.dispatch_id"),
        unique=True,
        index=True,
    )
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"))
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    session_key: Mapped[str] = mapped_column(String(255), unique=True)
    binding_status: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatch: Mapped[DispatchTurnModel] = relationship(
        back_populates="callback_binding",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )
    assignment: Mapped[AssignmentModel] = relationship(
        "AssignmentModel",
        foreign_keys=[assignment_id],
        lazy="selectin",
    )


class DispatchDeliveryStateModel(RuntimeBase):
    __tablename__ = "dispatch_delivery_states"
    __table_args__ = (
        CheckConstraint(
            f"transport_state IN ({_sql_in(DISPATCH_DELIVERY_STATUS_VALUES)})",
            name="ck_dispatch_delivery_states_transport_state",
        ),
        CheckConstraint(
            f"controller_observation_state IN ({_sql_in(DISPATCH_OBSERVATION_STATE_VALUES)})",
            name="ck_dispatch_delivery_states_controller_observation_state",
        ),
        CheckConstraint(
            f"send_mode IN ({_sql_in(PROMPT_SEND_MODE_VALUES)})",
            name="ck_dispatch_delivery_states_send_mode",
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
    controller_observation_state: Mapped[str] = mapped_column(String(255))
    last_provider_event_kind: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_final_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    send_mode: Mapped[str] = mapped_column(String(64))
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
        foreign_keys=[previous_dispatch_id],
        lazy="selectin",
    )
    superseded_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
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
    continuity_state: Mapped[str] = mapped_column(String(255))
    previous_response_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_key_present: Mapped[bool] = mapped_column(Boolean, default=False)
    invalidation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    dispatch: Mapped[DispatchTurnModel] = relationship(
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
        foreign_keys=[recovery_dispatch_id],
        lazy="selectin",
    )
    previous_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        foreign_keys=[previous_dispatch_id],
        lazy="selectin",
    )
    superseded_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        foreign_keys=[superseded_by_dispatch_id],
        lazy="selectin",
    )


class ProviderEventRecordModel(RuntimeBase):
    __tablename__ = "provider_event_records"
    __table_args__ = (
        UniqueConstraint("dispatch_id", "event_no"),
        CheckConstraint(
            f"event_source IN ({_sql_in(PROVIDER_EVENT_SOURCE_VALUES)})",
            name="ck_provider_event_records_event_source",
        ),
        CheckConstraint(
            f"event_kind IN ({_sql_in(PROVIDER_EVENT_KIND_VALUES)})",
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
        back_populates="provider_events",
        foreign_keys=[dispatch_id],
        lazy="selectin",
    )
    attempt: Mapped[AttemptModel] = relationship(
        "AttemptModel",
        foreign_keys=[attempt_id],
        lazy="selectin",
    )


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
    session_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    "DispatchCallbackBindingModel",
    "DispatchContinuityStateModel",
    "DispatchDeliveryStateModel",
    "DispatchTurnModel",
    "DispatchWatchdogStateModel",
    "NodeSessionModel",
    "ProviderEventRecordModel",
    "WorkspaceRootLeaseModel",
]
