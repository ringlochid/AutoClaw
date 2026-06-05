from __future__ import annotations

from autoclaw.persistence.models import DispatchTurnModel
from autoclaw.runtime.errors import (
    conflicting_continuation_error,
    illegal_state_error,
)


def ensure_no_staged_child_assignment(
    dispatch: DispatchTurnModel,
    *,
    action_name: str,
) -> None:
    if dispatch.staged_child_assignment_id is not None:
        raise conflicting_continuation_error(
            f"{action_name} is illegal after staging a child assignment"
        )


def ensure_no_terminal_release_basis(
    dispatch: DispatchTurnModel,
    *,
    action_name: str,
) -> None:
    if terminal_release_basis_committed(dispatch):
        raise illegal_state_error(
            f"{action_name} is illegal after terminal release basis was committed"
        )


def terminal_release_basis_committed(dispatch: DispatchTurnModel) -> bool:
    return dispatch.release_precondition_kind is not None
