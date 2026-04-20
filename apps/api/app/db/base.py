from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum as PythonEnum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import MetaData, Uuid, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=_utcnow_naive,
        onupdate=_utcnow_naive,
        nullable=False,
    )


def build_str_enum(enum_cls: type[PythonEnum], *, name: str, create_type: bool = True) -> SqlEnum:
    return SqlEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        create_type=create_type,
        native_enum=False,
    )
