from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db_session
from app.schemas.runtime import CompiledPlanRead
from app.services.compiler_service import compile_published_workflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/{workflow_key}/compile", response_model=CompiledPlanRead, status_code=status.HTTP_201_CREATED)
async def compile_workflow_route(workflow_key: str, session=Depends(get_db_session)) -> CompiledPlanRead:
    try:
        compiled_plan = await compile_published_workflow(session, workflow_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    await session.commit()

    return CompiledPlanRead(
        id=compiled_plan.id,
        workflow_version_id=compiled_plan.workflow_version_id,
        compiler_version=compiled_plan.compiler_version,
        plan_hash=compiled_plan.plan_hash,
        source_snapshot=compiled_plan.source_snapshot,
        nodes=[
            {
                "id": node.id,
                "node_key": node.node_key,
                "parent_node_key": node.parent_node_key,
                "mode": node.mode,
                "order_index": node.order_index,
                "skill_bindings": node.skill_bindings,
            }
            for node in sorted(compiled_plan.nodes, key=lambda node: node.order_index)
        ],
        edges=[
            {
                "id": edge.id,
                "from_node_key": edge.from_node_key,
                "to_node_key": edge.to_node_key,
                "edge_kind": edge.edge_kind,
                "condition_expr": edge.condition_expr,
                "order_index": edge.order_index,
            }
            for edge in sorted(compiled_plan.edges, key=lambda edge: edge.order_index)
        ],
    )
