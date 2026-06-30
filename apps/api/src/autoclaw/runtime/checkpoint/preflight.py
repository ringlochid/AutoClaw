from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel
from autoclaw.runtime.contracts import (
    CheckpointKind,
    CheckpointOutcome,
    CheckpointWriteBody,
    NodeKind,
)
from autoclaw.runtime.errors import boundary_precondition_error, stale_assignment_error
from autoclaw.runtime.projection import CurrentRuntimeState
from autoclaw.runtime.release.basis import ensure_assignment_required_publications
from autoclaw.runtime.release.preconditions import ensure_release_green_preconditions


async def ensure_terminal_green_checkpoint_preflight(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    checkpoint_write: CheckpointWriteBody,
    pending_publication_slots: set[str],
) -> None:
    if not _is_terminal_green_checkpoint(checkpoint_write):
        return
    await ensure_assignment_required_publications(
        session,
        task_id=task_id,
        assignment=state.current_assignment,
        pending_publication_slots=pending_publication_slots,
    )
    if state.current_node.structural_kind == NodeKind.WORKER.value:
        return
    _ensure_release_green_precondition_matches_current_assignment(
        state=state,
        dispatch=dispatch,
    )
    await ensure_release_green_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=state.flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
        current_assignment_pending_publication_slots=pending_publication_slots,
        is_boundary_mode=True,
    )


def _is_terminal_green_checkpoint(checkpoint_write: CheckpointWriteBody) -> bool:
    return (
        checkpoint_write.checkpoint_kind == CheckpointKind.TERMINAL
        and checkpoint_write.outcome == CheckpointOutcome.GREEN
    )


def _ensure_release_green_precondition_matches_current_assignment(
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
) -> None:
    if dispatch.release_precondition_kind != "release_green":
        raise boundary_precondition_error(
            "terminal green checkpoint requires release_green first",
            suggested_next_step=(
                "Commit `release_green` on this open parent/root dispatch first, then "
                "record the terminal green checkpoint."
            ),
        )
    if (
        dispatch.release_precondition_flow_revision_id != state.flow.active_flow_revision_id
        or dispatch.release_precondition_assignment_id != state.current_assignment.assignment_id
    ):
        raise stale_assignment_error("green release precondition is stale")


__all__ = ["ensure_terminal_green_checkpoint_preflight"]
