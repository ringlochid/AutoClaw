"""add task/runtime bundle layer and inline context metadata"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260418_0003"
down_revision = "20260416_0002"
branch_labels = None
depends_on = None


UUID = sa.Uuid()
JSON = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
TIMESTAMP = sa.DateTime()


def _create_table_if_missing(
    name: str, *columns: sa.Column, indexes: list[sa.Index] | None = None
) -> None:
    bind = op.get_bind()
    table = sa.Table(name, sa.MetaData(), *columns)
    table.create(bind, checkfirst=True)
    for index in indexes or []:
        index.table = table
        index.create(bind, checkfirst=True)


def upgrade() -> None:
    _create_table_if_missing(
        "task_images",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("image_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("source_task_id", UUID, sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("spec_payload", JSON, nullable=False),
        indexes=[sa.Index("ix_task_images_image_hash", "image_hash", unique=True)],
    )

    _create_table_if_missing(
        "task_composes",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "task_id",
            UUID,
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("task_image_id", UUID, sa.ForeignKey("task_images.id"), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("materialization_root", sa.String(length=512), nullable=False),
        sa.Column("compose_payload", JSON, nullable=False),
    )

    _create_table_if_missing(
        "runtime_images",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("image_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "compiled_plan_node_id", UUID, sa.ForeignKey("compiled_plan_nodes.id"), nullable=True
        ),
        sa.Column("spec_payload", JSON, nullable=False),
        indexes=[sa.Index("ix_runtime_images_image_hash", "image_hash", unique=True)],
    )

    _create_table_if_missing(
        "runtime_containers",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_compose_id", UUID, sa.ForeignKey("task_composes.id"), nullable=True),
        sa.Column("runtime_image_id", UUID, sa.ForeignKey("runtime_images.id"), nullable=True),
        sa.Column("flow_id", UUID, sa.ForeignKey("flows.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "flow_node_id",
            UUID,
            sa.ForeignKey("flow_nodes.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("node_session_id", UUID, sa.ForeignKey("node_sessions.id"), nullable=True),
        sa.Column(
            "current_node_attempt_id", UUID, sa.ForeignKey("node_attempts.id"), nullable=True
        ),
        sa.Column(
            "current_context_manifest_id",
            UUID,
            sa.ForeignKey("context_manifests.id"),
            nullable=True,
        ),
        sa.Column("backend_kind", sa.String(length=64), nullable=False),
        sa.Column("backend_handle", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("bootstrap_state", sa.String(length=64), nullable=False),
        sa.Column("container_payload", JSON, nullable=False),
        sa.Column("started_at", TIMESTAMP, nullable=False),
        sa.Column("last_seen_at", TIMESTAMP, nullable=True),
        sa.Column("ended_at", TIMESTAMP, nullable=True),
        indexes=[sa.Index("ix_runtime_containers_flow_status", "flow_id", "status")],
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    context_item_columns = {column["name"] for column in inspector.get_columns("context_items")}
    if "metadata" not in context_item_columns:
        with op.batch_alter_table("context_items") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "metadata",
                    JSON,
                    nullable=False,
                    server_default=sa.text("'{}'"),
                )
            )
            batch_op.alter_column("metadata", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    context_item_columns = {column["name"] for column in inspector.get_columns("context_items")}
    if "metadata" in context_item_columns:
        with op.batch_alter_table("context_items") as batch_op:
            batch_op.drop_column("metadata")

    if inspector.has_table("runtime_containers"):
        op.drop_index("ix_runtime_containers_flow_status", table_name="runtime_containers")
        op.drop_table("runtime_containers")
    if inspector.has_table("runtime_images"):
        op.drop_index("ix_runtime_images_image_hash", table_name="runtime_images")
        op.drop_table("runtime_images")
    if inspector.has_table("task_composes"):
        op.drop_table("task_composes")
    if inspector.has_table("task_images"):
        op.drop_index("ix_task_images_image_hash", table_name="task_images")
        op.drop_table("task_images")
