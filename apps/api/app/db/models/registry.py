from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DefinitionVersionStatus, SkillBindingState, SkillProvider
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, build_str_enum
from app.db.types import PortableJSON


class RoleDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_definitions"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    versions: Mapped[list[RoleVersion]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="RoleVersion.version",
    )


class RoleVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_versions"
    __table_args__ = (
        UniqueConstraint(
            "role_definition_id", "version", name="uq_role_versions_definition_version"
        ),
        Index(
            "ix_role_versions_definition_status_version",
            "role_definition_id",
            "status",
            "version",
        ),
    )

    role_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("role_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[DefinitionVersionStatus] = mapped_column(
        build_str_enum(DefinitionVersionStatus, name="definition_version_status"),
        default=DefinitionVersionStatus.DRAFT,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audit: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    definition: Mapped[RoleDefinition] = relationship(back_populates="versions")


class PolicyDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_definitions"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    versions: Mapped[list[PolicyVersion]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.version",
    )


class PolicyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint(
            "policy_definition_id", "version", name="uq_policy_versions_definition_version"
        ),
        Index(
            "ix_policy_versions_definition_status_version",
            "policy_definition_id",
            "status",
            "version",
        ),
    )

    policy_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("policy_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[DefinitionVersionStatus] = mapped_column(
        build_str_enum(
            DefinitionVersionStatus, name="definition_version_status", create_type=False
        ),
        default=DefinitionVersionStatus.DRAFT,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audit: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    definition: Mapped[PolicyDefinition] = relationship(back_populates="versions")


class WorkflowDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_definitions"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    versions: Mapped[list[WorkflowVersion]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="WorkflowVersion.version",
    )


class WorkflowVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_definition_id", "version", name="uq_workflow_versions_definition_version"
        ),
        Index(
            "ix_workflow_versions_definition_status_version",
            "workflow_definition_id",
            "status",
            "version",
        ),
    )

    workflow_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[DefinitionVersionStatus] = mapped_column(
        build_str_enum(
            DefinitionVersionStatus, name="definition_version_status", create_type=False
        ),
        default=DefinitionVersionStatus.DRAFT,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audit: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    definition: Mapped[WorkflowDefinition] = relationship(back_populates="versions")
    compiled_plans: Mapped[list[CompiledPlan]] = relationship(back_populates="workflow_version")


class SkillRegistry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skill_registry"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    provider: Mapped[SkillProvider] = mapped_column(
        build_str_enum(SkillProvider, name="skill_provider"),
        nullable=False,
    )
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    versions: Mapped[list[SkillVersion]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
        order_by="SkillVersion.created_at",
    )


class SkillVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint(
            "skill_registry_id", "version_label", name="uq_skill_versions_registry_version"
        ),
        Index(
            "ix_skill_versions_registry_status",
            "skill_registry_id",
            "status",
        ),
    )

    skill_registry_id: Mapped[UUID] = mapped_column(
        ForeignKey("skill_registry.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_label: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DefinitionVersionStatus] = mapped_column(
        build_str_enum(
            DefinitionVersionStatus, name="definition_version_status", create_type=False
        ),
        default=DefinitionVersionStatus.DRAFT,
        nullable=False,
    )
    source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    skill: Mapped[SkillRegistry] = relationship(back_populates="versions")


class RoleVersionSkillBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_version_skill_bindings"
    __table_args__ = (
        UniqueConstraint(
            "role_version_id",
            "skill_version_id",
            name="uq_role_version_skill_bindings_pair",
        ),
        Index("ix_role_version_skill_bindings_role_version", "role_version_id"),
    )

    role_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("role_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("skill_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[SkillBindingState] = mapped_column(
        build_str_enum(SkillBindingState, name="skill_binding_state"),
        default=SkillBindingState.ALLOWED,
        nullable=False,
    )


class WorkflowVersionSkillBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_version_skill_bindings"
    __table_args__ = (
        UniqueConstraint(
            "workflow_version_id",
            "skill_version_id",
            name="uq_workflow_version_skill_bindings_pair",
        ),
        Index("ix_workflow_version_skill_bindings_workflow_version", "workflow_version_id"),
    )

    workflow_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("skill_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[SkillBindingState] = mapped_column(
        build_str_enum(SkillBindingState, name="skill_binding_state", create_type=False),
        default=SkillBindingState.ALLOWED,
        nullable=False,
    )


class WorkflowNodeSkillBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_node_skill_bindings"
    __table_args__ = (
        UniqueConstraint(
            "workflow_version_id",
            "node_key",
            "skill_version_id",
            name="uq_workflow_node_skill_bindings_triplet",
        ),
        Index(
            "ix_workflow_node_skill_bindings_workflow_version_node_key",
            "workflow_version_id",
            "node_key",
        ),
    )

    workflow_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("skill_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[SkillBindingState] = mapped_column(
        build_str_enum(SkillBindingState, name="skill_binding_state", create_type=False),
        default=SkillBindingState.ALLOWED,
        nullable=False,
    )


from app.db.models.runtime import CompiledPlan  # noqa: E402  # isort: skip
