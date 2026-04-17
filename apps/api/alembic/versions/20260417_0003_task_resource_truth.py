"""add task resource truth tables and flow-node lineage fields"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.enums import (
    ResourceScope,
    TaskResourceBindingMode,
    TaskResourceBindingRole,
    WorkspaceRootKind,
    WorkspaceRootMode,
)

revision = "20260417_0003"
down_revision = "b551dd0a1ba6"
branch_labels = None
depends_on = None


RESOURCE_SCOPE = sa.Enum(
    ResourceScope,
    name="resource_scope",
    native_enum=False,
    values_callable=lambda members: [member.value for member in members],
)
WORKSPACE_ROOT_KIND = sa.Enum(
    WorkspaceRootKind,
    name="workspace_root_kind",
    native_enum=False,
    values_callable=lambda members: [member.value for member in members],
)
WORKSPACE_ROOT_MODE = sa.Enum(
    WorkspaceRootMode,
    name="workspace_root_mode",
    native_enum=False,
    values_callable=lambda members: [member.value for member in members],
)
TASK_RESOURCE_BINDING_ROLE = sa.Enum(
    TaskResourceBindingRole,
    name="task_resource_binding_role",
    native_enum=False,
    values_callable=lambda members: [member.value for member in members],
)
TASK_RESOURCE_BINDING_MODE = sa.Enum(
    TaskResourceBindingMode,
    name="task_resource_binding_mode",
    native_enum=False,
    values_callable=lambda members: [member.value for member in members],
)


def _json_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("workspace_roots"):
        op.create_table(
            "workspace_roots",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("scope", RESOURCE_SCOPE, nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=256), nullable=False),
            sa.Column("storage_uri", sa.String(length=512), nullable=False),
            sa.Column("kind", WORKSPACE_ROOT_KIND, nullable=False),
            sa.Column("mode", WORKSPACE_ROOT_MODE, nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False, server_default="active"),
            sa.Column(
                "content_hash",
                sa.String(length=128),
                nullable=False,
                server_default="",
            ),
            sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_workspace_roots")),
            sa.UniqueConstraint("key", name=op.f("uq_workspace_roots_key")),
        )
        op.create_index(op.f("ix_workspace_roots_key"), "workspace_roots", ["key"], unique=False)

    if not _has_table("context_spaces"):
        op.create_table(
            "context_spaces",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("scope", RESOURCE_SCOPE, nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=256), nullable=False),
            sa.Column("storage_uri", sa.String(length=512), nullable=False),
            sa.Column("source_workspace_root_id", sa.Uuid(), nullable=True),
            sa.Column("status", sa.String(length=64), nullable=False, server_default="active"),
            sa.Column(
                "content_hash",
                sa.String(length=128),
                nullable=False,
                server_default="",
            ),
            sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["source_workspace_root_id"],
                ["workspace_roots.id"],
                name=op.f("fk_context_spaces_source_workspace_root_id_workspace_roots"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_context_spaces")),
            sa.UniqueConstraint("key", name=op.f("uq_context_spaces_key")),
        )
        op.create_index(op.f("ix_context_spaces_key"), "context_spaces", ["key"], unique=False)

    if not _has_table("manifest_roots"):
        op.create_table(
            "manifest_roots",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("task_id", sa.Uuid(), nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("storage_uri", sa.String(length=512), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False, server_default="active"),
            sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["task_id"],
                ["tasks.id"],
                name=op.f("fk_manifest_roots_task_id_tasks"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_manifest_roots")),
            sa.UniqueConstraint("task_id", "key", name="uq_manifest_roots_task_key"),
        )

    if not _has_table("task_resource_bindings"):
        op.create_table(
            "task_resource_bindings",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("task_id", sa.Uuid(), nullable=False),
            sa.Column("binding_role", TASK_RESOURCE_BINDING_ROLE, nullable=False),
            sa.Column("workspace_root_id", sa.Uuid(), nullable=True),
            sa.Column("context_space_id", sa.Uuid(), nullable=True),
            sa.Column("manifest_root_id", sa.Uuid(), nullable=True),
            sa.Column("mode", TASK_RESOURCE_BINDING_MODE, nullable=False),
            sa.Column("read_only", sa.Boolean(), nullable=True),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "(CASE WHEN workspace_root_id IS NOT NULL THEN 1 ELSE 0 END + "
                "CASE WHEN context_space_id IS NOT NULL THEN 1 ELSE 0 END + "
                "CASE WHEN manifest_root_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
                name="ck_task_resource_bindings_exactly_one_target",
            ),
            sa.CheckConstraint(
                "(binding_role != 'manifest_root') OR (manifest_root_id IS NOT NULL)",
                name="ck_task_resource_bindings_manifest_role_target",
            ),
            sa.ForeignKeyConstraint(
                ["task_id"],
                ["tasks.id"],
                name=op.f("fk_task_resource_bindings_task_id_tasks"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["workspace_root_id"],
                ["workspace_roots.id"],
                name=op.f("fk_task_resource_bindings_workspace_root_id_workspace_roots"),
            ),
            sa.ForeignKeyConstraint(
                ["context_space_id"],
                ["context_spaces.id"],
                name=op.f("fk_task_resource_bindings_context_space_id_context_spaces"),
            ),
            sa.ForeignKeyConstraint(
                ["manifest_root_id"],
                ["manifest_roots.id"],
                name=op.f("fk_task_resource_bindings_manifest_root_id_manifest_roots"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_task_resource_bindings")),
        )
        op.create_index(
            "ix_task_resource_bindings_task_role",
            "task_resource_bindings",
            ["task_id", "binding_role"],
            unique=False,
        )
        op.create_index(
            "uq_task_resource_bindings_primary_workspace",
            "task_resource_bindings",
            ["task_id"],
            unique=True,
            postgresql_where=sa.text("binding_role = 'primary_workspace'"),
            sqlite_where=sa.text("binding_role = 'primary_workspace'"),
        )
        op.create_index(
            "uq_task_resource_bindings_primary_context",
            "task_resource_bindings",
            ["task_id"],
            unique=True,
            postgresql_where=sa.text("binding_role = 'primary_context'"),
            sqlite_where=sa.text("binding_role = 'primary_context'"),
        )
        op.create_index(
            "uq_task_resource_bindings_manifest_root",
            "task_resource_bindings",
            ["task_id"],
            unique=True,
            postgresql_where=sa.text("binding_role = 'manifest_root'"),
            sqlite_where=sa.text("binding_role = 'manifest_root'"),
        )

    if not _has_column("flow_nodes", "logical_node_key"):
        with op.batch_alter_table("flow_nodes") as batch_op:
            batch_op.add_column(
                sa.Column("logical_node_key", sa.String(length=256), nullable=True)
            )
        op.execute(
            sa.text(
                "UPDATE flow_nodes "
                "SET logical_node_key = node_key "
                "WHERE logical_node_key IS NULL"
            )
        )
        with op.batch_alter_table("flow_nodes") as batch_op:
            batch_op.alter_column(
                "logical_node_key",
                existing_type=sa.String(length=256),
                nullable=False,
            )

    if not _has_column("flow_nodes", "supersedes_flow_node_id"):
        with op.batch_alter_table("flow_nodes") as batch_op:
            batch_op.add_column(sa.Column("supersedes_flow_node_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                op.f("fk_flow_nodes_supersedes_flow_node_id_flow_nodes"),
                "flow_nodes",
                ["supersedes_flow_node_id"],
                ["id"],
            )

    if not _has_index("flow_nodes", "ix_flow_nodes_flow_logical_node"):
        op.create_index(
            "ix_flow_nodes_flow_logical_node",
            "flow_nodes",
            ["flow_id", "logical_node_key"],
            unique=False,
        )

    if not _has_column("context_manifests", "manifest_root_id"):
        with op.batch_alter_table("context_manifests") as batch_op:
            batch_op.add_column(sa.Column("manifest_root_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                op.f("fk_context_manifests_manifest_root_id_manifest_roots"),
                "manifest_roots",
                ["manifest_root_id"],
                ["id"],
            )


def downgrade() -> None:
    if _has_column("context_manifests", "manifest_root_id"):
        with op.batch_alter_table("context_manifests") as batch_op:
            batch_op.drop_constraint(
                op.f("fk_context_manifests_manifest_root_id_manifest_roots"),
                type_="foreignkey",
            )
            batch_op.drop_column("manifest_root_id")

    if _has_index("flow_nodes", "ix_flow_nodes_flow_logical_node"):
        op.drop_index("ix_flow_nodes_flow_logical_node", table_name="flow_nodes")

    if _has_column("flow_nodes", "supersedes_flow_node_id"):
        with op.batch_alter_table("flow_nodes") as batch_op:
            batch_op.drop_constraint(
                op.f("fk_flow_nodes_supersedes_flow_node_id_flow_nodes"),
                type_="foreignkey",
            )
            batch_op.drop_column("supersedes_flow_node_id")

    if _has_column("flow_nodes", "logical_node_key"):
        with op.batch_alter_table("flow_nodes") as batch_op:
            batch_op.drop_column("logical_node_key")

    if _has_table("task_resource_bindings"):
        op.drop_index(
            "uq_task_resource_bindings_manifest_root",
            table_name="task_resource_bindings",
        )
        op.drop_index(
            "uq_task_resource_bindings_primary_context",
            table_name="task_resource_bindings",
        )
        op.drop_index(
            "uq_task_resource_bindings_primary_workspace",
            table_name="task_resource_bindings",
        )
        op.drop_index(
            "ix_task_resource_bindings_task_role",
            table_name="task_resource_bindings",
        )
        op.drop_table("task_resource_bindings")

    if _has_table("manifest_roots"):
        op.drop_table("manifest_roots")

    if _has_table("context_spaces"):
        op.drop_index(op.f("ix_context_spaces_key"), table_name="context_spaces")
        op.drop_table("context_spaces")

    if _has_table("workspace_roots"):
        op.drop_index(op.f("ix_workspace_roots_key"), table_name="workspace_roots")
        op.drop_table("workspace_roots")
