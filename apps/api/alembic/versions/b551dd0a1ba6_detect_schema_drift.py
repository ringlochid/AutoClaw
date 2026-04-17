"""backfill compiled plan effective payload for existing databases"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b551dd0a1ba6"
down_revision = "20260416_0002"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if _has_column("compiled_plan_nodes", "effective_payload"):
        return

    bind = op.get_bind()
    server_default = (
        sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else sa.text("'{}'")
    )
    op.add_column(
        "compiled_plan_nodes",
        sa.Column(
            "effective_payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=server_default,
        ),
    )
    op.alter_column("compiled_plan_nodes", "effective_payload", server_default=None)


def downgrade() -> None:
    if _has_column("compiled_plan_nodes", "effective_payload"):
        op.drop_column("compiled_plan_nodes", "effective_payload")
