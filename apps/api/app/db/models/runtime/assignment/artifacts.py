from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
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
from app.db.models.runtime.assignment.execution import AttemptModel
from app.db.models.runtime.common import utcnow


class ArtifactPublicationModel(RuntimeBase):
    __tablename__ = "artifact_publications"
    __table_args__ = (
        UniqueConstraint("task_id", "owner_node_key", "slot", "version"),
        UniqueConstraint("task_id", "flow_node_id", "owner_node_key", "slot", "version"),
        ForeignKeyConstraint(
            ["attempt_id", "flow_node_id"],
            ["attempts.attempt_id", "attempts.flow_node_id"],
            name="fk_artifact_publications_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    artifact_publication_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    owner_node_key: Mapped[str] = mapped_column(String(255), index=True)
    slot: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    assignment_key: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_key"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    supersedes_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supersedes_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[AttemptModel] = relationship(
        foreign_keys=[attempt_id],
        lazy="raise",
    )


class ArtifactCurrentPointerModel(RuntimeBase):
    __tablename__ = "artifact_current_pointers"
    __table_args__ = (
        UniqueConstraint("task_id", "owner_node_key", "slot"),
        ForeignKeyConstraint(
            ["attempt_id", "flow_node_id"],
            ["attempts.attempt_id", "attempts.flow_node_id"],
            name="fk_artifact_current_pointers_attempt_owner",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["task_id", "flow_node_id", "owner_node_key", "slot", "current_version"],
            [
                "artifact_publications.task_id",
                "artifact_publications.flow_node_id",
                "artifact_publications.owner_node_key",
                "artifact_publications.slot",
                "artifact_publications.version",
            ],
            name="fk_artifact_current_pointers_publication",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    artifact_current_pointer_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    owner_node_key: Mapped[str] = mapped_column(String(255))
    slot: Mapped[str] = mapped_column(String(255))
    current_version: Mapped[int] = mapped_column(Integer)
    current_path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    assignment_key: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_key"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    supersedes_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_publication: Mapped[ArtifactPublicationModel] = relationship(
        primaryjoin=lambda: and_(
            ArtifactCurrentPointerModel.task_id == ArtifactPublicationModel.task_id,
            ArtifactCurrentPointerModel.flow_node_id == ArtifactPublicationModel.flow_node_id,
            ArtifactCurrentPointerModel.owner_node_key == ArtifactPublicationModel.owner_node_key,
            ArtifactCurrentPointerModel.slot == ArtifactPublicationModel.slot,
            ArtifactCurrentPointerModel.current_version == ArtifactPublicationModel.version,
        ),
        foreign_keys=lambda: [
            ArtifactCurrentPointerModel.task_id,
            ArtifactCurrentPointerModel.flow_node_id,
            ArtifactCurrentPointerModel.owner_node_key,
            ArtifactCurrentPointerModel.slot,
            ArtifactCurrentPointerModel.current_version,
        ],
        lazy="raise",
    )
    attempt: Mapped[AttemptModel] = relationship(
        foreign_keys=[attempt_id],
        lazy="raise",
    )


Index(
    "ix_artifact_publications_lookup",
    ArtifactPublicationModel.task_id,
    ArtifactPublicationModel.owner_node_key,
    ArtifactPublicationModel.slot,
)

__all__ = [
    "ArtifactCurrentPointerModel",
    "ArtifactPublicationModel",
]
