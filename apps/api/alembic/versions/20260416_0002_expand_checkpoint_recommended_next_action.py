"""expand checkpoint recommended_next_action to text"""

import sqlalchemy as sa

from alembic import op

revision = "20260416_0002"
down_revision = "20260414_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_checkpoints") as batch_op:
        batch_op.alter_column(
            "recommended_next_action",
            existing_type=sa.String(length=128),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE node_checkpoints
            SET recommended_next_action = LEFT(recommended_next_action, 128)
            WHERE recommended_next_action IS NOT NULL
              AND LENGTH(recommended_next_action) > 128
            """
        )
    )

    with op.batch_alter_table("node_checkpoints") as batch_op:
        batch_op.alter_column(
            "recommended_next_action",
            existing_type=sa.Text(),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
