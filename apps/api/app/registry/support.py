from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import TypeVar, cast, overload

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload

from app.db.models import (
    PolicyDefinitionModel,
    PolicyRevisionModel,
    RoleDefinitionModel,
    RoleRevisionModel,
    WorkflowDefinitionModel,
    WorkflowRevisionModel,
)
from app.schemas.definitions.workflow import WorkflowDefinitionInput

DefinitionModelT = TypeVar(
    "DefinitionModelT",
    WorkflowDefinitionModel,
    RoleDefinitionModel,
    PolicyDefinitionModel,
)
RevisionModelT = TypeVar(
    "RevisionModelT",
    WorkflowRevisionModel,
    RoleRevisionModel,
    PolicyRevisionModel,
)
type DefinitionModelType = (
    type[WorkflowDefinitionModel] | type[RoleDefinitionModel] | type[PolicyDefinitionModel]
)
type RevisionModelType = (
    type[WorkflowRevisionModel] | type[RoleRevisionModel] | type[PolicyRevisionModel]
)
type CurrentDefinitionModel = WorkflowDefinitionModel | RoleDefinitionModel | PolicyDefinitionModel
type CurrentRevisionModel = WorkflowRevisionModel | RoleRevisionModel | PolicyRevisionModel
type CurrentDefinitionRevisionRow = (
    tuple[WorkflowDefinitionModel, WorkflowRevisionModel]
    | tuple[RoleDefinitionModel, RoleRevisionModel]
    | tuple[PolicyDefinitionModel, PolicyRevisionModel]
)
SchemaModelT = TypeVar("SchemaModelT", bound=BaseModel)


class RegistryWorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    definition: WorkflowDefinitionInput
    revision_no: int = Field(ge=1)


def model_from_attrs(
    model_type: type[SchemaModelT],
    /,
    **attributes: object,
) -> SchemaModelT:
    return model_type.model_validate(SimpleNamespace(**attributes), from_attributes=True)


def canonical_content_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def workflow_revision_id(workflow_key: str, revision_no: int) -> str:
    return f"workflow-revision.{workflow_key}.{revision_no:03d}"


def role_revision_id(role_key: str, revision_no: int) -> str:
    return f"role-revision.{role_key}.{revision_no:03d}"


def policy_revision_id(policy_key: str, revision_no: int) -> str:
    return f"policy-revision.{policy_key}.{revision_no:03d}"


async def next_registry_revision_no(
    session: AsyncSession,
    revision_model: type[RevisionModelT],
    *,
    key_column: InstrumentedAttribute[str],
    key: str,
) -> int:
    revision_no = await session.scalar(
        select(func.max(revision_model.revision_no)).where(key_column == key)
    )
    return int(revision_no or 0) + 1


@overload
async def load_current_definition_revision(
    session: AsyncSession,
    definition_model: type[WorkflowDefinitionModel],
    revision_model: type[WorkflowRevisionModel],
    *,
    key_column: InstrumentedAttribute[str],
    key_field: str,
    key: str,
) -> WorkflowRevisionModel: ...


@overload
async def load_current_definition_revision(
    session: AsyncSession,
    definition_model: type[RoleDefinitionModel],
    revision_model: type[RoleRevisionModel],
    *,
    key_column: InstrumentedAttribute[str],
    key_field: str,
    key: str,
) -> RoleRevisionModel: ...


@overload
async def load_current_definition_revision(
    session: AsyncSession,
    definition_model: type[PolicyDefinitionModel],
    revision_model: type[PolicyRevisionModel],
    *,
    key_column: InstrumentedAttribute[str],
    key_field: str,
    key: str,
) -> PolicyRevisionModel: ...


async def load_current_definition_revision(
    session: AsyncSession,
    definition_model: DefinitionModelType,
    revision_model: RevisionModelType,
    *,
    key_column: InstrumentedAttribute[str],
    key_field: str,
    key: str,
) -> CurrentRevisionModel:
    _ = revision_model
    definition_key = cast(
        InstrumentedAttribute[str],
        getattr(definition_model, key_column.key),
    )
    current_revision = definition_model.current_revision
    rows = await session.execute(
        select(definition_model).options(joinedload(current_revision)).where(definition_key == key)
    )
    definition = cast(CurrentDefinitionModel | None, rows.unique().scalar_one_or_none())
    if definition is None:
        raise ValueError(f"unknown definition key '{key}'")
    if definition.current_revision_no is None:
        raise ValueError(f"missing current revision pointer for {key_field} '{key}'")
    revision = definition.current_revision
    if revision is None:
        raise ValueError(
            "missing current revision for "
            f"{key_field} '{key}' at revision {definition.current_revision_no}"
        )
    return revision


async def load_definition_revision_by_no(
    session: AsyncSession,
    revision_model: type[RevisionModelT],
    *,
    key_column: InstrumentedAttribute[str],
    key_field: str,
    key: str,
    revision_no: int,
) -> RevisionModelT:
    revision = await session.scalar(
        select(revision_model).where(
            key_column == key,
            revision_model.revision_no == revision_no,
        )
    )
    if revision is None:
        raise ValueError(f"missing {key_field} '{key}' revision {revision_no}")
    return revision


async def load_definition_revision_by_content_hash(
    session: AsyncSession,
    revision_model: type[RevisionModelT],
    *,
    key_column: InstrumentedAttribute[str],
    key: str,
    content_hash: str,
) -> RevisionModelT | None:
    return cast(
        RevisionModelT | None,
        await session.scalar(
            select(revision_model)
            .where(
                key_column == key,
                revision_model.content_hash == content_hash,
            )
            .order_by(revision_model.revision_no.desc())
        ),
    )


def seed_source_matches(
    *,
    stored_source_path: str | None,
    expected_source_path: str,
) -> bool:
    if stored_source_path is None:
        return False
    normalized_stored_path = stored_source_path.replace("\\", "/")
    if normalized_stored_path == expected_source_path:
        return True
    packaged_prefix = "seed://packaged/"
    if not expected_source_path.startswith(packaged_prefix):
        return False
    relative_seed_path = expected_source_path.removeprefix(packaged_prefix)
    return normalized_stored_path.endswith(f"/definitions/{relative_seed_path}")


async def load_definition_for_update(
    session: AsyncSession,
    definition_model: type[DefinitionModelT],
    *,
    key_column: InstrumentedAttribute[str],
    key: str,
) -> DefinitionModelT | None:
    row: DefinitionModelT | None = await session.scalar(
        select(definition_model).where(key_column == key).with_for_update()
    )
    return row


async def acquire_definition_owner_row(
    session: AsyncSession,
    definition_model: type[DefinitionModelT],
    *,
    key_column: InstrumentedAttribute[str],
    key: str,
    build_row: Callable[[], DefinitionModelT],
) -> tuple[DefinitionModelT, bool]:
    row = await load_definition_for_update(
        session,
        definition_model,
        key_column=key_column,
        key=key,
    )
    if row is not None and row.current_revision_no is not None:
        return row, False

    row = build_row()
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        row = await load_definition_for_update(
            session,
            definition_model,
            key_column=key_column,
            key=key,
        )
        if row is None:
            raise
        return row, False

    return row, True


@overload
async def load_current_definition_revision_rows(
    session: AsyncSession,
    definition_model: type[WorkflowDefinitionModel],
    revision_model: type[WorkflowRevisionModel],
    *,
    definition_key: InstrumentedAttribute[str],
    revision_key: InstrumentedAttribute[str],
    current_revision_no: InstrumentedAttribute[int | None],
) -> list[tuple[WorkflowDefinitionModel, WorkflowRevisionModel]]: ...


@overload
async def load_current_definition_revision_rows(
    session: AsyncSession,
    definition_model: type[RoleDefinitionModel],
    revision_model: type[RoleRevisionModel],
    *,
    definition_key: InstrumentedAttribute[str],
    revision_key: InstrumentedAttribute[str],
    current_revision_no: InstrumentedAttribute[int | None],
) -> list[tuple[RoleDefinitionModel, RoleRevisionModel]]: ...


@overload
async def load_current_definition_revision_rows(
    session: AsyncSession,
    definition_model: type[PolicyDefinitionModel],
    revision_model: type[PolicyRevisionModel],
    *,
    definition_key: InstrumentedAttribute[str],
    revision_key: InstrumentedAttribute[str],
    current_revision_no: InstrumentedAttribute[int | None],
) -> list[tuple[PolicyDefinitionModel, PolicyRevisionModel]]: ...


async def load_current_definition_revision_rows(
    session: AsyncSession,
    definition_model: DefinitionModelType,
    revision_model: RevisionModelType,
    *,
    definition_key: InstrumentedAttribute[str],
    revision_key: InstrumentedAttribute[str],
    current_revision_no: InstrumentedAttribute[int | None],
) -> Sequence[CurrentDefinitionRevisionRow]:
    _ = revision_model, revision_key
    current_revision = definition_model.current_revision
    definitions = cast(
        list[CurrentDefinitionModel],
        (
            await session.scalars(
                select(definition_model)
                .options(joinedload(current_revision))
                .where(current_revision_no.is_not(None))
                .order_by(definition_key.asc())
            )
        )
        .unique()
        .all(),
    )

    rows: list[CurrentDefinitionRevisionRow] = []
    for definition_row in definitions:
        revision_row = definition_row.current_revision
        if revision_row is None:
            definition_id = cast(str, getattr(definition_row, definition_key.key))
            raise ValueError(
                "missing current revision for "
                f"{definition_key.key} '{definition_id}' at revision "
                f"{definition_row.current_revision_no}"
            )
        rows.append(cast(CurrentDefinitionRevisionRow, (definition_row, revision_row)))
    return rows
