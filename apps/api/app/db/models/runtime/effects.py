from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import RuntimeBase
from app.db.models.runtime.shared import (
    RUNTIME_EFFECT_KIND_VALUES,
    RUNTIME_EFFECT_STATE_VALUES,
    sql_in,
    utcnow,
)


class RuntimeEffectModel(RuntimeBase):
    __tablename__ = "runtime_effects"
    __table_args__ = (
        CheckConstraint(
            f"effect_kind IN ({sql_in(RUNTIME_EFFECT_KIND_VALUES)})",
            name="ck_runtime_effects_effect_kind",
        ),
        CheckConstraint(
            f"effect_state IN ({sql_in(RUNTIME_EFFECT_STATE_VALUES)})",
            name="ck_runtime_effects_effect_state",
        ),
        CheckConstraint(
            "requested_revision >= 1",
            name="ck_runtime_effects_requested_revision_positive",
        ),
        CheckConstraint(
            "processed_revision >= 0",
            name="ck_runtime_effects_processed_revision_nonnegative",
        ),
        CheckConstraint(
            "processed_revision <= requested_revision",
            name="ck_runtime_effects_processed_revision_not_ahead",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_runtime_effects_attempt_count_nonnegative",
        ),
        Index(
            "ix_runtime_effects_state_priority_available_at",
            "effect_state",
            "priority",
            "available_at",
        ),
        Index("ix_runtime_effects_dedupe_key", "dedupe_key", unique=True),
    )

    runtime_effect_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.task_id"),
        index=True,
        nullable=True,
    )
    dedupe_key: Mapped[str] = mapped_column(Text)
    effect_kind: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer)
    requested_revision: Mapped[int] = mapped_column(Integer, default=1)
    processed_revision: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    effect_state: Mapped[str] = mapped_column(String(64), default="pending")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


__all__ = ["RuntimeEffectModel"]
