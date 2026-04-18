"""add requested_by and audit fields to registry definition versions"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260418_0004"
down_revision = "20260417_0003"
branch_labels = None
depends_on = None

VERSION_TABLES = (
    "role_versions",
    "policy_versions",
    "workflow_versions",
)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _json_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _json_server_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade() -> None:
    for table_name in VERSION_TABLES:
        if not _has_column(table_name, "requested_by"):
            op.add_column(
                table_name,
                sa.Column("requested_by", sa.String(length=255), nullable=True),
            )

        if not _has_column(table_name, "audit"):
            op.add_column(
                table_name,
                sa.Column(
                    "audit",
                    _json_type(),
                    nullable=False,
                    server_default=_json_server_default(),
                ),
            )
            op.alter_column(table_name, "audit", server_default=None)


def downgrade() -> None:
    for table_name in VERSION_TABLES:
        if _has_column(table_name, "audit"):
            op.drop_column(table_name, "audit")
        if _has_column(table_name, "requested_by"):
            op.drop_column(table_name, "requested_by")
