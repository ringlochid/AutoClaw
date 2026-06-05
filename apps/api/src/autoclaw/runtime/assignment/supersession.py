from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import AssignmentModel, AttemptModel, FlowNodeModel
from autoclaw.runtime.errors import (
    conflicting_continuation_error,
    missing_resource_error,
)


async def load_superseded_child_assignment(
    session: AsyncSession,
    *,
    child_node: FlowNodeModel,
) -> AssignmentModel | None:
    current_assignment_id = child_node.current_assignment_id
    if current_assignment_id is None:
        return None
    current_assignment = await session.get(
        AssignmentModel,
        current_assignment_id,
        options=(raiseload("*"),),
    )
    if current_assignment is None:
        raise missing_resource_error(f"missing current assignment '{current_assignment_id}'")
    current_attempt_id = current_assignment.current_attempt_id
    if current_attempt_id is None:
        raise conflicting_continuation_error(
            f"assign_child cannot overwrite incomplete child assignment "
            f"'{current_assignment.assignment_key}'"
        )
    current_attempt = await session.get(
        AttemptModel,
        current_attempt_id,
        options=(raiseload("*"),),
    )
    if current_attempt is None:
        raise missing_resource_error(f"missing attempt '{current_attempt_id}'")
    if current_attempt.closed_at is None or current_attempt.status in {"pending", "running"}:
        raise conflicting_continuation_error(
            f"assign_child cannot overwrite open child assignment "
            f"'{current_assignment.assignment_key}'"
        )
    return current_assignment


__all__ = ["load_superseded_child_assignment"]
