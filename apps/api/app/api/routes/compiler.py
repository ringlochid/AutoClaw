from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.presenters.runtime import to_compiled_plan_read
from app.schemas.runtime import CompiledPlanRead
from app.services.compiler_service import compile_published_workflow, get_compiled_plan

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post(
    "/{workflow_key}/compile", response_model=CompiledPlanRead, status_code=status.HTTP_201_CREATED
)
async def compile_workflow_route(workflow_key: str, session: DbSession) -> CompiledPlanRead:
    try:
        compiled_plan = await compile_published_workflow(session, workflow_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    await session.commit()
    return to_compiled_plan_read(compiled_plan)


@router.get("/compiled-plans/{compiled_plan_id}", response_model=CompiledPlanRead)
async def get_compiled_plan_route(compiled_plan_id: UUID, session: DbSession) -> CompiledPlanRead:
    compiled_plan = await get_compiled_plan(session, compiled_plan_id)
    if compiled_plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No compiled plan found: {compiled_plan_id}",
        )
    return to_compiled_plan_read(compiled_plan)
