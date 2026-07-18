from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AssignmentModel,
    AssignmentWorkPlanModel,
    AssignmentWorkPlanStepModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.dispatch.authority import (
    NodeOperationAuthority,
    exact_node_operation_authority_exists,
)
from autoclaw.runtime.errors import stale_assignment_error
from autoclaw.runtime.work_plan.contracts import (
    SetWorkPlanRequest,
    SetWorkPlanResponse,
    WorkPlanRead,
    WorkPlanStepRead,
)


async def set_assignment_work_plan(
    session: AsyncSession,
    *,
    authority: NodeOperationAuthority,
    request: SetWorkPlanRequest,
) -> SetWorkPlanResponse:
    assignment_id = authority.assignment_id
    current = await read_assignment_work_plan(session, assignment_id=assignment_id)
    if _matches_request(current, request):
        await session.commit()
        return SetWorkPlanResponse(changed=False, plan=current)

    next_revision = authority.work_plan_revision + 1
    updated_assignment_id = await session.scalar(
        update(AssignmentModel)
        .where(
            AssignmentModel.assignment_id == assignment_id,
            AssignmentModel.work_plan_revision == authority.work_plan_revision,
            exact_node_operation_authority_exists(authority),
        )
        .values(work_plan_revision=next_revision)
        .returning(AssignmentModel.assignment_id)
    )
    if updated_assignment_id is None:
        raise stale_assignment_error("the assignment work plan changed concurrently")

    await session.execute(
        delete(AssignmentWorkPlanStepModel).where(
            AssignmentWorkPlanStepModel.assignment_id == assignment_id
        )
    )
    existing_plan = await session.get(AssignmentWorkPlanModel, assignment_id)
    if not request.steps:
        if existing_plan is not None:
            await session.delete(existing_plan)
        await session.commit()
        return SetWorkPlanResponse(changed=True, plan=None)

    committed_at = utc_now()
    if existing_plan is None:
        existing_plan = AssignmentWorkPlanModel(
            assignment_id=assignment_id,
            revision=next_revision,
            explanation=request.explanation,
            authoring_dispatch_id=authority.dispatch_id,
            committed_at=committed_at,
        )
        session.add(existing_plan)
    else:
        existing_plan.revision = next_revision
        existing_plan.explanation = request.explanation
        existing_plan.authoring_dispatch_id = authority.dispatch_id
        existing_plan.committed_at = committed_at

    for order_index, step in enumerate(request.steps):
        session.add(
            AssignmentWorkPlanStepModel(
                work_plan_step_id=(
                    f"work-plan-step.{assignment_id}.{next_revision:04d}.{order_index:02d}"
                ),
                assignment_id=assignment_id,
                order_index=order_index,
                step=step.step,
                status=step.status.value,
            )
        )
    await session.commit()
    plan = await read_assignment_work_plan(session, assignment_id=assignment_id)
    assert plan is not None
    return SetWorkPlanResponse(changed=True, plan=plan)


async def read_assignment_work_plan(
    session: AsyncSession,
    *,
    assignment_id: str,
) -> WorkPlanRead | None:
    plan = await session.get(AssignmentWorkPlanModel, assignment_id)
    if plan is None:
        return None
    steps = tuple(
        WorkPlanStepRead.model_validate(row)
        for row in await session.scalars(
            select(AssignmentWorkPlanStepModel)
            .where(AssignmentWorkPlanStepModel.assignment_id == assignment_id)
            .order_by(AssignmentWorkPlanStepModel.order_index)
        )
    )
    return WorkPlanRead(
        assignment_id=assignment_id,
        revision=plan.revision,
        explanation=plan.explanation,
        steps=steps,
        authored_by_dispatch_id=plan.authoring_dispatch_id,
        updated_at=_as_utc(plan.committed_at),
    )


def _matches_request(current: WorkPlanRead | None, request: SetWorkPlanRequest) -> bool:
    if current is None:
        return not request.steps
    if current.explanation != request.explanation or len(current.steps) != len(request.steps):
        return False
    return all(
        current_step.step == requested_step.step and current_step.status == requested_step.status
        for current_step, requested_step in zip(current.steps, request.steps, strict=True)
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["read_assignment_work_plan", "set_assignment_work_plan"]
