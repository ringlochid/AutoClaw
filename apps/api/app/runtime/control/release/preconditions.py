from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from app.runtime.contracts import EgressBoundary
from app.runtime.control.flow.queries import flow_node_by_key, require_flow_for_task
from app.runtime.effects.validation import (
    attempt_checkpoint_projection_failure,
    current_surfaced_ref_failure,
    is_path_current,
)


async def _flow_node_assignment_attempt_rows(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    parent_flow_node_id: str | None = None,
) -> list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]]:
    query = (
        select(FlowNodeModel, AssignmentModel, AttemptModel)
        .options(raiseload("*"))
        .outerjoin(
            AssignmentModel,
            AssignmentModel.assignment_id == FlowNodeModel.current_assignment_id,
        )
        .outerjoin(
            AttemptModel,
            AttemptModel.attempt_id == AssignmentModel.current_attempt_id,
        )
        .where(FlowNodeModel.flow_revision_id == flow_revision_id)
        .order_by(FlowNodeModel.order_index.asc(), FlowNodeModel.node_key.asc())
    )
    if parent_flow_node_id is not None:
        query = query.where(FlowNodeModel.parent_flow_node_id == parent_flow_node_id)
    return cast(
        list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]],
        (await session.execute(query)).all(),
    )


async def _current_pointer_pairs(
    session: AsyncSession,
    *,
    task_id: str,
    assignment_keys: set[str],
    slots: set[str],
) -> set[tuple[str, str]]:
    if not assignment_keys or not slots:
        return set()
    return {
        (assignment_key, slot)
        for assignment_key, slot, current_path in cast(
            list[tuple[str, str, str]],
            (
                await session.execute(
                    select(
                        ArtifactCurrentPointerModel.assignment_key,
                        ArtifactCurrentPointerModel.slot,
                        ArtifactCurrentPointerModel.current_path,
                    ).where(
                        ArtifactCurrentPointerModel.task_id == task_id,
                        ArtifactCurrentPointerModel.assignment_key.in_(assignment_keys),
                        ArtifactCurrentPointerModel.slot.in_(slots),
                    )
                )
            ).all(),
        )
        if is_path_current(current_path)
    }


async def _ensure_current_assignment_basis_is_current(
    session: AsyncSession,
    *,
    task_id: str,
    assignment: AssignmentModel,
    action_name: str,
) -> None:
    for ref in [*assignment.criteria_json, *assignment.consumes_json]:
        failure = await current_surfaced_ref_failure(session, task_id=task_id, ref=ref)
        if failure is not None:
            raise ValueError(f"{action_name} requires current surfaced evidence: {failure}")


async def _ensure_current_checkpoint_projection(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    action_name: str,
    allow_current_dispatch_truth: bool = False,
) -> None:
    failure = await attempt_checkpoint_projection_failure(
        session,
        task_id=task_id,
        attempt_id=attempt_id,
    )
    if (
        failure == "current checkpoint projection files are missing"
        and allow_current_dispatch_truth
    ):
        flow = await require_flow_for_task(session, task_id)
        if flow.current_open_dispatch_id is not None:
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            if dispatch is not None and dispatch.attempt_id == attempt_id:
                return
    if failure is not None:
        raise ValueError(f"{action_name} requires current checkpoint evidence: {failure}")


async def ensure_assignment_required_publications(
    session: AsyncSession,
    *,
    task_id: str,
    assignment: AssignmentModel,
    allow_pending_current_attempt_publications: bool = False,
) -> None:
    slots = {str(requirement["slot"]) for requirement in assignment.produces_json}
    pointer_pairs = await _current_pointer_pairs(
        session,
        task_id=task_id,
        assignment_keys={assignment.assignment_key},
        slots=slots,
    )
    current_pointers = {
        pointer.slot: pointer
        for pointer in await session.scalars(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.assignment_key == assignment.assignment_key,
                ArtifactCurrentPointerModel.slot.in_(slots),
            )
        )
    }
    for requirement in assignment.produces_json:
        slot = str(requirement["slot"])
        if (assignment.assignment_key, slot) in pointer_pairs:
            continue
        pending_pointer = current_pointers.get(slot)
        if allow_pending_current_attempt_publications and pending_pointer is not None:
            continue
        raise ValueError(
            f"missing required publication for assignment '{assignment.assignment_key}'"
        )


async def ensure_release_green_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
) -> None:
    current_node = await flow_node_by_key(session, flow_revision_id, current_node_key)
    await _ensure_current_assignment_basis_is_current(
        session,
        task_id=task_id,
        assignment=current_assignment,
        action_name="release_green",
    )
    await ensure_assignment_required_publications(
        session,
        task_id=task_id,
        assignment=current_assignment,
    )
    child_assignment_rows = await _flow_node_assignment_attempt_rows(
        session,
        flow_revision_id=flow_revision_id,
        parent_flow_node_id=current_node.flow_node_id,
    )
    child_pointer_pairs = await _current_pointer_pairs(
        session,
        task_id=task_id,
        assignment_keys={
            assignment.assignment_key
            for _, assignment, _ in child_assignment_rows
            if assignment is not None and assignment.produces_json
        },
        slots={
            str(requirement["slot"])
            for _, assignment, _ in child_assignment_rows
            if assignment is not None
            for requirement in assignment.produces_json
        },
    )
    for child, child_assignment, attempt in child_assignment_rows:
        if child.current_assignment_id is None:
            raise ValueError(f"child node '{child.node_key}' has no current assignment")
        if child_assignment is None:
            raise ValueError(f"missing child assignment '{child.current_assignment_id}'")
        await _ensure_current_assignment_basis_is_current(
            session,
            task_id=task_id,
            assignment=child_assignment,
            action_name="release_green",
        )
        if child_assignment.current_attempt_id is None or attempt is None:
            raise ValueError(
                f"child assignment '{child_assignment.assignment_key}' has no current attempt"
            )
        if (
            attempt.latest_checkpoint_id is None
            or attempt.terminal_outcome != EgressBoundary.GREEN.value
        ):
            raise ValueError(
                f"child assignment '{child_assignment.assignment_key}' is not terminal-green"
            )
        await _ensure_current_checkpoint_projection(
            session,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            action_name="release_green",
        )
        for requirement in child_assignment.produces_json:
            if (
                child_assignment.assignment_key,
                str(requirement["slot"]),
            ) not in child_pointer_pairs:
                raise ValueError(
                    "missing required publication for child assignment "
                    f"'{child_assignment.assignment_key}'"
                )


async def ensure_release_blocked_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
) -> None:
    await _ensure_current_assignment_basis_is_current(
        session,
        task_id=task_id,
        assignment=current_assignment,
        action_name="release_blocked",
    )
    if current_assignment.current_attempt_id is None:
        raise ValueError("release_blocked requires a current root attempt")
    root_attempt = await session.get(AttemptModel, current_assignment.current_attempt_id)
    if root_attempt is None:
        raise ValueError(f"missing root attempt '{current_assignment.current_attempt_id}'")
    root_checkpoint = None
    if root_attempt.latest_checkpoint_id is not None:
        root_checkpoint = await session.get(
            AttemptCheckpointModel,
            root_attempt.latest_checkpoint_id,
        )
    if (
        root_checkpoint is None
        or root_checkpoint.checkpoint_kind != "terminal"
        or root_checkpoint.outcome != EgressBoundary.BLOCKED.value
    ):
        raise ValueError("release_blocked requires the current root basis to be terminal-blocked")
    await _ensure_current_checkpoint_projection(
        session,
        task_id=task_id,
        attempt_id=root_attempt.attempt_id,
        action_name="release_blocked",
        allow_current_dispatch_truth=True,
    )

    blocked_found = False
    for node, assignment, attempt in await _flow_node_assignment_attempt_rows(
        session,
        flow_revision_id=flow_revision_id,
    ):
        if node.current_assignment_id is None:
            continue
        if assignment is None or assignment.current_attempt_id is None or attempt is None:
            raise ValueError(f"node '{node.node_key}' has no current attempt")
        await _ensure_current_assignment_basis_is_current(
            session,
            task_id=task_id,
            assignment=assignment,
            action_name="release_blocked",
        )
        if node.node_key == current_node_key:
            blocked_found = True
            continue
        if attempt.latest_checkpoint_id is None or attempt.terminal_outcome is None:
            raise ValueError(
                "release_blocked requires terminal whole-flow truth; "
                f"node '{node.node_key}' is still active"
            )
        await _ensure_current_checkpoint_projection(
            session,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            action_name="release_blocked",
        )
        blocked_found = blocked_found or attempt.terminal_outcome == EgressBoundary.BLOCKED.value
    if not blocked_found:
        raise ValueError("release_blocked requires a current blocked basis")


__all__ = [
    "ensure_assignment_required_publications",
    "ensure_release_blocked_preconditions",
    "ensure_release_green_preconditions",
]
