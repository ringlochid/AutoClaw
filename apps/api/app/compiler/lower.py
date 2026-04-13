from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.runtime import CompiledPlan, CompiledPlanEdge, CompiledPlanNode
from app.schemas.compiler import NormalizedCompiledPlan


async def persist_compiled_plan(
    session: AsyncSession,
    normalized_plan: NormalizedCompiledPlan,
    plan_hash: str,
) -> CompiledPlan:
    existing_plan = await session.scalar(
        select(CompiledPlan)
        .options(
            selectinload(CompiledPlan.nodes),
            selectinload(CompiledPlan.edges),
        )
        .where(CompiledPlan.plan_hash == plan_hash)
    )
    if existing_plan is not None:
        return existing_plan

    compiled_plan = CompiledPlan(
        workflow_version_id=normalized_plan.workflow_version_id,
        compiler_version=normalized_plan.compiler_version,
        plan_hash=plan_hash,
        source_snapshot=normalized_plan.source_snapshot,
    )
    session.add(compiled_plan)
    await session.flush()

    for node in normalized_plan.nodes:
        session.add(
            CompiledPlanNode(
                compiled_plan_id=compiled_plan.id,
                node_key=node.node_key,
                parent_node_key=node.parent_node_key,
                role_version_id=node.role_version_id,
                policy_version_id=node.policy_version_id,
                mode=node.mode,
                order_index=node.order_index,
                skill_bindings=node.skill_bindings,
            )
        )

    for edge in normalized_plan.edges:
        session.add(
            CompiledPlanEdge(
                compiled_plan_id=compiled_plan.id,
                from_node_key=edge.from_node,
                to_node_key=edge.to_node,
                edge_kind=edge.edge_kind,
                condition_expr=edge.condition_expr,
                order_index=edge.order_index,
            )
        )

    await session.flush()
    return await session.scalar(
        select(CompiledPlan)
        .options(
            selectinload(CompiledPlan.nodes),
            selectinload(CompiledPlan.edges),
        )
        .where(CompiledPlan.id == compiled_plan.id)
    )
