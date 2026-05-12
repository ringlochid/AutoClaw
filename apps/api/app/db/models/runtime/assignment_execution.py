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
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import RuntimeBase
from app.db.models.runtime.shared import (
    ATTEMPT_STATUS_VALUES,
    CHECKPOINT_KIND_VALUES,
    CHECKPOINT_OUTCOME_VALUES,
    RUNTIME_REF_KIND_VALUES,
    sql_in,
    utcnow,
)

if TYPE_CHECKING:
    from app.db.models.runtime.dispatch_turns import DispatchTurnModel
    from app.db.models.runtime.flow_graph import FlowNodeModel
    from app.db.models.runtime.flow_runtime import FlowModel, FlowRevisionModel


class AssignmentModel(RuntimeBase):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("assignment_id", "flow_node_id"),
        ForeignKeyConstraint(
            ["current_attempt_id", "assignment_id"],
            ["attempts.attempt_id", "attempts.assignment_id"],
            name="fk_assignments_current_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["created_by_dispatch_id"],
            ["dispatch_turns.dispatch_id"],
            name="fk_assignments_created_by_dispatch",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    assignment_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_id: Mapped[str | None] = mapped_column(
        ForeignKey("flows.flow_id"),
        nullable=True,
        index=True,
    )
    flow_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("flow_revisions.flow_revision_id"),
        nullable=True,
    )
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    assignment_key: Mapped[str] = mapped_column(String(255), unique=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str] = mapped_column(Text)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    consumes_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    produces_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    transient_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    task_memory_search_hints_json: Mapped[list[str]] = mapped_column(JSON)
    current_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "attempts.attempt_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    created_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flow: Mapped[FlowModel | None] = relationship(
        "FlowModel",
        foreign_keys=[flow_id],
        lazy="raise",
    )
    flow_revision: Mapped[FlowRevisionModel | None] = relationship(
        "FlowRevisionModel",
        foreign_keys=[flow_revision_id],
        lazy="raise",
    )
    flow_node: Mapped[FlowNodeModel] = relationship(
        "FlowNodeModel",
        back_populates="assignments",
        foreign_keys=[flow_node_id],
        lazy="raise",
    )
    criteria_refs: Mapped[list[AssignmentCriteriaRefModel]] = relationship(
        back_populates="assignment",
        foreign_keys="AssignmentCriteriaRefModel.assignment_id",
        lazy="raise",
        order_by="AssignmentCriteriaRefModel.order_index",
    )
    attempts: Mapped[list[AttemptModel]] = relationship(
        back_populates="assignment",
        foreign_keys="AttemptModel.assignment_id",
        lazy="raise",
        order_by="AttemptModel.opened_at",
    )
    current_attempt: Mapped[AttemptModel | None] = relationship(
        primaryjoin=lambda: and_(
            AssignmentModel.current_attempt_id == AttemptModel.attempt_id,
            AssignmentModel.assignment_id == AttemptModel.assignment_id,
        ),
        foreign_keys=lambda: [AssignmentModel.current_attempt_id, AssignmentModel.assignment_id],
        lazy="raise",
        viewonly=True,
    )
    created_by_dispatch: Mapped[DispatchTurnModel | None] = relationship(
        "DispatchTurnModel",
        back_populates="created_assignments",
        foreign_keys=[created_by_dispatch_id],
        lazy="raise",
    )


class AssignmentCriteriaRefModel(RuntimeBase):
    __tablename__ = "assignment_criteria_refs"

    assignment_criteria_ref_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"), index=True)
    slot: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer)
    assignment: Mapped[AssignmentModel] = relationship(
        back_populates="criteria_refs",
        foreign_keys=[assignment_id],
        lazy="raise",
    )


class AttemptModel(RuntimeBase):
    __tablename__ = "attempts"
    __table_args__ = (
        UniqueConstraint("attempt_id", "assignment_id"),
        UniqueConstraint("attempt_id", "flow_node_id"),
        CheckConstraint(
            f"status IN ({sql_in(ATTEMPT_STATUS_VALUES)})",
            name="ck_attempts_status",
        ),
        CheckConstraint(
            "terminal_outcome IS NULL OR "
            f"terminal_outcome IN ({sql_in(CHECKPOINT_OUTCOME_VALUES)})",
            name="ck_attempts_terminal_outcome",
        ),
        ForeignKeyConstraint(
            ["latest_checkpoint_id", "attempt_id"],
            ["attempt_checkpoints.checkpoint_id", "attempt_checkpoints.attempt_id"],
            name="fk_attempts_latest_checkpoint_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    attempt_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"), index=True)
    assignment_key: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_key"))
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    retry_of_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("attempts.attempt_id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(64), default="running")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    latest_checkpoint_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "attempt_checkpoints.checkpoint_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    terminal_outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignment: Mapped[AssignmentModel] = relationship(
        back_populates="attempts",
        foreign_keys=[assignment_id],
        lazy="raise",
    )
    retry_of_attempt: Mapped[AttemptModel | None] = relationship(
        back_populates="retry_attempts",
        foreign_keys=[retry_of_attempt_id],
        remote_side=lambda: [AttemptModel.attempt_id],
        lazy="raise",
    )
    retry_attempts: Mapped[list[AttemptModel]] = relationship(
        back_populates="retry_of_attempt",
        lazy="raise",
        order_by="AttemptModel.opened_at",
    )
    checkpoints: Mapped[list[AttemptCheckpointModel]] = relationship(
        back_populates="attempt",
        foreign_keys="AttemptCheckpointModel.attempt_id",
        lazy="raise",
        order_by="AttemptCheckpointModel.recorded_at",
    )
    latest_checkpoint: Mapped[AttemptCheckpointModel | None] = relationship(
        primaryjoin=lambda: and_(
            AttemptModel.latest_checkpoint_id == AttemptCheckpointModel.checkpoint_id,
            AttemptModel.attempt_id == AttemptCheckpointModel.attempt_id,
        ),
        foreign_keys=lambda: [AttemptModel.latest_checkpoint_id, AttemptModel.attempt_id],
        lazy="raise",
        viewonly=True,
    )
    consumed_refs: Mapped[list[AttemptConsumedRefModel]] = relationship(
        back_populates="attempt",
        foreign_keys="AttemptConsumedRefModel.attempt_id",
        lazy="raise",
        order_by="AttemptConsumedRefModel.order_index",
    )
    produced_refs: Mapped[list[AttemptProducedRefModel]] = relationship(
        back_populates="attempt",
        foreign_keys="AttemptProducedRefModel.attempt_id",
        lazy="raise",
        order_by="AttemptProducedRefModel.order_index",
    )
    dispatch_turns: Mapped[list[DispatchTurnModel]] = relationship(
        "DispatchTurnModel",
        back_populates="attempt",
        foreign_keys="DispatchTurnModel.attempt_id",
        lazy="raise",
        order_by="DispatchTurnModel.rendered_at",
    )


class AttemptCheckpointModel(RuntimeBase):
    __tablename__ = "attempt_checkpoints"
    __table_args__ = (
        UniqueConstraint("checkpoint_id", "attempt_id"),
        CheckConstraint(
            f"checkpoint_kind IN ({sql_in(CHECKPOINT_KIND_VALUES)})",
            name="ck_attempt_checkpoints_kind",
        ),
        CheckConstraint(
            f"outcome IS NULL OR outcome IN ({sql_in(CHECKPOINT_OUTCOME_VALUES)})",
            name="ck_attempt_checkpoints_outcome",
        ),
        CheckConstraint(
            "checkpoint_kind != 'progress' OR outcome IS NULL",
            name="ck_attempt_checkpoints_progress_outcome",
        ),
        CheckConstraint(
            "checkpoint_kind != 'terminal' OR outcome IS NOT NULL",
            name="ck_attempt_checkpoints_terminal_outcome",
        ),
        ForeignKeyConstraint(
            ["attempt_id", "assignment_id"],
            ["attempts.attempt_id", "attempts.assignment_id"],
            name="fk_attempt_checkpoints_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["assignment_id", "flow_node_id"],
            ["assignments.assignment_id", "assignments.flow_node_id"],
            name="fk_attempt_checkpoints_assignment_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_attempt_checkpoints_attempt_recorded_at", "attempt_id", "recorded_at"),
        Index("ix_attempt_checkpoints_summary", "summary"),
    )

    checkpoint_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"), index=True)
    assignment_key: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_key"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    checkpoint_kind: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    next_step: Mapped[str] = mapped_column(Text)
    blockers_json: Mapped[list[str]] = mapped_column(JSON)
    risks_json: Mapped[list[str]] = mapped_column(JSON)
    produced_artifact_claims_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    produced_artifacts_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    artifact_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    transient_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    task_memory_search_hints_json: Mapped[list[str]] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    assignment: Mapped[AssignmentModel] = relationship(
        foreign_keys=[assignment_id],
        lazy="raise",
    )
    attempt: Mapped[AttemptModel] = relationship(
        back_populates="checkpoints",
        foreign_keys=[attempt_id],
        lazy="raise",
    )


class AttemptConsumedRefModel(RuntimeBase):
    __tablename__ = "attempt_consumed_refs"
    __table_args__ = (
        CheckConstraint(
            f"ref_kind IN ({sql_in(RUNTIME_REF_KIND_VALUES)})",
            name="ck_attempt_consumed_refs_kind",
        ),
    )

    attempt_consumed_ref_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    ref_kind: Mapped[str] = mapped_column(String(64))
    slot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)
    attempt: Mapped[AttemptModel] = relationship(
        back_populates="consumed_refs",
        foreign_keys=[attempt_id],
        lazy="raise",
    )


class AttemptProducedRefModel(RuntimeBase):
    __tablename__ = "attempt_produced_refs"

    attempt_produced_ref_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    owner_node_key: Mapped[str] = mapped_column(String(255), index=True)
    assignment_key: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_key"))
    slot: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    became_current: Mapped[bool] = mapped_column(default=False)
    order_index: Mapped[int] = mapped_column(Integer)
    attempt: Mapped[AttemptModel] = relationship(
        back_populates="produced_refs",
        foreign_keys=[attempt_id],
        lazy="raise",
    )


Index("ix_assignments_task_node", AssignmentModel.task_id, AssignmentModel.node_key)
Index("ix_attempts_task_node", AttemptModel.task_id, AttemptModel.node_key)

__all__ = [
    "AssignmentCriteriaRefModel",
    "AssignmentModel",
    "AttemptCheckpointModel",
    "AttemptConsumedRefModel",
    "AttemptModel",
    "AttemptProducedRefModel",
]
