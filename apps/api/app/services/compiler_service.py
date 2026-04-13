from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.compiler.lower import persist_compiled_plan
from app.compiler.normalize import normalize_resolved_workflow
from app.compiler.plan_hash import compute_plan_hash
from app.compiler.resolve import resolve_workflow_definition
from app.compiler.validate import validate_resolved_workflow
from app.db.models.runtime import CompiledPlan


async def compile_published_workflow(
    session: AsyncSession,
    workflow_key: str,
) -> CompiledPlan:
    resolved_workflow = await resolve_workflow_definition(session, workflow_key)
    validate_resolved_workflow(resolved_workflow)
    normalized_plan = normalize_resolved_workflow(resolved_workflow)
    plan_hash = compute_plan_hash(normalized_plan)
    return await persist_compiled_plan(session, normalized_plan, plan_hash)


async def get_compiled_plan(
    session: AsyncSession,
    compiled_plan_id: UUID,
) -> CompiledPlan | None:
    return cast(
        CompiledPlan | None,
        await session.scalar(
            select(CompiledPlan)
            .options(
                selectinload(CompiledPlan.nodes),
                selectinload(CompiledPlan.edges),
            )
            .where(CompiledPlan.id == compiled_plan_id)
        ),
    )
