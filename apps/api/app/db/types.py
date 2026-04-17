from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

PortableJSON = JSON().with_variant(JSONB, "postgresql")
