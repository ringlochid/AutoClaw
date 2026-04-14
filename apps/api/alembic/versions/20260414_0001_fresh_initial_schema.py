"""fresh initial schema"""

import importlib

from alembic import op
from app.db.base import Base

revision = "20260414_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    importlib.import_module("app.db.models")
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    importlib.import_module("app.db.models")
    Base.metadata.drop_all(bind)
