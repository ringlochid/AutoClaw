from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    FlowNodeModel,
)
from autoclaw.runtime.contracts import EgressBoundary
from autoclaw.runtime.errors import (
    boundary_precondition_error,
    illegal_state_error,
    missing_required_publication_error,
)
from autoclaw.runtime.flow.queries import flow_node_by_key
from autoclaw.runtime.release.basis import (
    current_pointer_pairs,
    ensure_assignment_required_publications,
    ensure_current_assignment_basis_is_current,
    ensure_current_checkpoint_projection,
    ensure_release_green_child_assignment_basis_is_current,
    flow_node_assignment_attempt_rows,
)


async def ensure_release_green_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
    is_boundary_mode: bool = False,
) -> None:
    current_node = await flow_node_by_key(session, flow_revision_id, current_node_key)
    await ensure_current_assignment_basis_is_current(
        session,
        task_id=task_id,
        assignment=current_assignment,
        action_name="release_green",
        is_boundary_mode=is_boundary_mode,
    )
    await ensure_assignment_required_publications(
        session,
        task_id=task_id,
        assignment=current_assignment,
        is_boundary_mode=is_boundary_mode,
    )
    child_assignment_rows = await flow_node_assignment_attempt_rows(
        session,
        flow_revision_id=flow_revision_id,
        parent_flow_node_id=current_node.flow_node_id,
    )
    child_pointer_pairs = await _release_green_child_pointer_pairs(
        session,
        task_id=task_id,
        child_assignment_rows=child_assignment_rows,
    )
    for child, child_assignment, attempt in child_assignment_rows:
        await _validate_release_green_child_row(
            session,
            task_id=task_id,
            flow_revision_id=flow_revision_id,
            child=child,
            child_assignment=child_assignment,
            attempt=attempt,
            child_pointer_pairs=child_pointer_pairs,
            is_boundary_mode=is_boundary_mode,
        )


async def ensure_release_blocked_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
    is_boundary_mode: bool = False,
) -> None:
    await ensure_current_assignment_basis_is_current(
        session,
        task_id=task_id,
        assignment=current_assignment,
        action_name="release_blocked",
        is_boundary_mode=is_boundary_mode,
    )
    await _load_release_blocked_root_attempt(
        session,
        task_id=task_id,
        current_assignment=current_assignment,
        is_boundary_mode=is_boundary_mode,
    )
    blocked_found = await _validate_release_blocked_flow_rows(
        session,
        task_id=task_id,
        flow_revision_id=flow_revision_id,
        current_node_key=current_node_key,
        is_boundary_mode=is_boundary_mode,
    )
    if not blocked_found:
        _raise_release_publication_error(
            summary="release_blocked requires a current blocked basis",
            is_boundary_mode=is_boundary_mode,
        )


def _raise_release_state_error(*, summary: str, is_boundary_mode: bool) -> None:
    if is_boundary_mode:
        raise boundary_precondition_error(summary)
    raise illegal_state_error(summary)


def _raise_release_publication_error(*, summary: str, is_boundary_mode: bool) -> None:
    if is_boundary_mode:
        raise boundary_precondition_error(summary)
    raise missing_required_publication_error(summary)


async def _release_green_child_pointer_pairs(
    session: AsyncSession,
    *,
    task_id: str,
    child_assignment_rows: list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]],
) -> set[tuple[str, str]]:
    return await current_pointer_pairs(
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


async def _validate_release_green_child_row(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    child: FlowNodeModel,
    child_assignment: AssignmentModel | None,
    attempt: AttemptModel | None,
    child_pointer_pairs: set[tuple[str, str]],
    is_boundary_mode: bool,
) -> None:
    if child.current_assignment_id is None:
        _raise_release_state_error(
            summary=f"child node '{child.node_key}' has no current assignment",
            is_boundary_mode=is_boundary_mode,
        )
    if child_assignment is None:
        _raise_release_state_error(
            summary=f"missing child assignment '{child.current_assignment_id}'",
            is_boundary_mode=is_boundary_mode,
        )
    assert child_assignment is not None
    await ensure_release_green_child_assignment_basis_is_current(
        session,
        task_id=task_id,
        flow_revision_id=flow_revision_id,
        assignment=child_assignment,
        is_boundary_mode=is_boundary_mode,
    )
    if child_assignment.current_attempt_id is None or attempt is None:
        _raise_release_state_error(
            summary=f"child assignment '{child_assignment.assignment_key}' has no current attempt",
            is_boundary_mode=is_boundary_mode,
        )
    assert attempt is not None
    if (
        attempt.latest_checkpoint_id is None
        or attempt.terminal_outcome != EgressBoundary.GREEN.value
    ):
        _raise_release_state_error(
            summary=f"child assignment '{child_assignment.assignment_key}' is not terminal-green",
            is_boundary_mode=is_boundary_mode,
        )
    await ensure_current_checkpoint_projection(
        session,
        task_id=task_id,
        attempt_id=attempt.attempt_id,
        action_name="release_green",
        is_boundary_mode=is_boundary_mode,
    )
    for requirement in child_assignment.produces_json:
        if (child_assignment.assignment_key, str(requirement["slot"])) in child_pointer_pairs:
            continue
        _raise_release_publication_error(
            summary=(
                "missing required publication for child assignment "
                f"'{child_assignment.assignment_key}'"
            ),
            is_boundary_mode=is_boundary_mode,
        )


async def _load_release_blocked_root_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    current_assignment: AssignmentModel,
    is_boundary_mode: bool,
) -> AttemptModel:
    if current_assignment.current_attempt_id is None:
        _raise_release_publication_error(
            summary="release_blocked requires a current root attempt",
            is_boundary_mode=is_boundary_mode,
        )
    assert current_assignment.current_attempt_id is not None
    root_attempt = await session.get(AttemptModel, current_assignment.current_attempt_id)
    if root_attempt is None:
        _raise_release_state_error(
            summary=f"missing root attempt '{current_assignment.current_attempt_id}'",
            is_boundary_mode=is_boundary_mode,
        )
    assert root_attempt is not None
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
        _raise_release_publication_error(
            summary="release_blocked requires the current root basis to be terminal-blocked",
            is_boundary_mode=is_boundary_mode,
        )
    await ensure_current_checkpoint_projection(
        session,
        task_id=task_id,
        attempt_id=root_attempt.attempt_id,
        action_name="release_blocked",
        is_boundary_mode=is_boundary_mode,
    )
    return root_attempt


async def _validate_release_blocked_flow_rows(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    is_boundary_mode: bool,
) -> bool:
    blocked_found = False
    flow_rows = await flow_node_assignment_attempt_rows(
        session,
        flow_revision_id=flow_revision_id,
    )
    for node, assignment, attempt in flow_rows:
        if node.current_assignment_id is None:
            continue
        if assignment is None or assignment.current_attempt_id is None or attempt is None:
            _raise_release_state_error(
                summary=f"node '{node.node_key}' has no current attempt",
                is_boundary_mode=is_boundary_mode,
            )
        assert assignment is not None
        assert attempt is not None
        await ensure_current_assignment_basis_is_current(
            session,
            task_id=task_id,
            assignment=assignment,
            action_name="release_blocked",
            is_boundary_mode=is_boundary_mode,
        )
        if node.node_key == current_node_key:
            blocked_found = True
            continue
        if attempt.latest_checkpoint_id is None or attempt.terminal_outcome is None:
            _raise_release_publication_error(
                summary=(
                    "release_blocked requires terminal whole-flow truth; "
                    f"node '{node.node_key}' is still active"
                ),
                is_boundary_mode=is_boundary_mode,
            )
        await ensure_current_checkpoint_projection(
            session,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            action_name="release_blocked",
            is_boundary_mode=is_boundary_mode,
        )
        blocked_found = blocked_found or attempt.terminal_outcome == EgressBoundary.BLOCKED.value
    return blocked_found


__all__ = [
    "ensure_assignment_required_publications",
    "ensure_release_blocked_preconditions",
    "ensure_release_green_preconditions",
]
