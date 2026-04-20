"""Persist role/workflow skill binding links."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_0004"
down_revision = "20260418_0003"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    skill_binding_state = sa.Enum(
        "allowed",
        "preferred",
        "required",
        "blocked",
        name="skill_binding_state",
        native_enum=False,
    )
    skill_binding_state.create(op.get_bind(), checkfirst=True)

    if not _has_table("role_version_skill_bindings"):
        op.create_table(
            "role_version_skill_bindings",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("role_version_id", sa.UUID(), nullable=False),
            sa.Column("skill_version_id", sa.UUID(), nullable=False),
            sa.Column("state", skill_binding_state, nullable=False),
            sa.ForeignKeyConstraint(["role_version_id"], ["role_versions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["skill_version_id"], ["skill_versions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "role_version_id", "skill_version_id", name="uq_role_version_skill_bindings_pair"
            ),
        )
        op.create_index(
            "ix_role_version_skill_bindings_role_version",
            "role_version_skill_bindings",
            ["role_version_id"],
            unique=False,
        )

    if not _has_table("workflow_version_skill_bindings"):
        op.create_table(
            "workflow_version_skill_bindings",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("workflow_version_id", sa.UUID(), nullable=False),
            sa.Column("skill_version_id", sa.UUID(), nullable=False),
            sa.Column("state", skill_binding_state, nullable=False),
            sa.ForeignKeyConstraint(
                ["workflow_version_id"], ["workflow_versions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["skill_version_id"], ["skill_versions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workflow_version_id",
                "skill_version_id",
                name="uq_workflow_version_skill_bindings_pair",
            ),
        )
        op.create_index(
            "ix_workflow_version_skill_bindings_workflow_version",
            "workflow_version_skill_bindings",
            ["workflow_version_id"],
            unique=False,
        )

    if not _has_table("workflow_node_skill_bindings"):
        op.create_table(
            "workflow_node_skill_bindings",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("workflow_version_id", sa.UUID(), nullable=False),
            sa.Column("node_key", sa.String(length=128), nullable=False),
            sa.Column("skill_version_id", sa.UUID(), nullable=False),
            sa.Column("state", skill_binding_state, nullable=False),
            sa.ForeignKeyConstraint(
                ["workflow_version_id"], ["workflow_versions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["skill_version_id"], ["skill_versions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workflow_version_id",
                "node_key",
                "skill_version_id",
                name="uq_workflow_node_skill_bindings_triplet",
            ),
        )
        op.create_index(
            "ix_workflow_node_skill_bindings_workflow_version_node_key",
            "workflow_node_skill_bindings",
            ["workflow_version_id", "node_key"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("workflow_node_skill_bindings"):
        op.drop_index(
            "ix_workflow_node_skill_bindings_workflow_version_node_key",
            table_name="workflow_node_skill_bindings",
        )
        op.drop_table("workflow_node_skill_bindings")

    if _has_table("workflow_version_skill_bindings"):
        op.drop_index(
            "ix_workflow_version_skill_bindings_workflow_version",
            table_name="workflow_version_skill_bindings",
        )
        op.drop_table("workflow_version_skill_bindings")

    if _has_table("role_version_skill_bindings"):
        op.drop_index(
            "ix_role_version_skill_bindings_role_version",
            table_name="role_version_skill_bindings",
        )
        op.drop_table("role_version_skill_bindings")

    sa.Enum(name="skill_binding_state").drop(op.get_bind(), checkfirst=True)
