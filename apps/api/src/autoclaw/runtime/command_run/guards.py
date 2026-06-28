from __future__ import annotations

from autoclaw.persistence.models import CommandRunModel, FlowWaitStateModel
from autoclaw.runtime.command_run.reads import command_run_conflict
from autoclaw.runtime.contracts import (
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunState,
    WaitingCause,
)


def ensure_command_run_can_be_cancelled(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
    is_already_requested_allowed: bool = False,
) -> None:
    ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state in {state.value for state in TERMINAL_COMMAND_RUN_STATES}:
        raise command_run_conflict(f"command run '{run_id}' is already terminal")
    if command_run.state == CommandRunState.CANCELLATION_REQUESTED.value:
        if is_already_requested_allowed:
            return
        raise command_run_conflict(f"command run '{run_id}' already has cancellation requested")


def ensure_command_run_can_be_claimed_for_local_start(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state != CommandRunState.PENDING_START.value:
        raise command_run_conflict(
            f"command run '{run_id}' is no longer pending local process start"
        )


def ensure_command_run_can_record_progress(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state in {state.value for state in TERMINAL_COMMAND_RUN_STATES}:
        raise command_run_conflict(f"command run '{run_id}' is already terminal")


def ensure_command_run_can_record_owned_process_pid(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state != CommandRunState.RUNNING.value:
        raise command_run_conflict(
            f"command run '{run_id}' is not in the local-running state needed to persist a pid"
        )


def ensure_command_run_can_record_terminal_result(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    ensure_command_run_owns_active_wait(
        command_run=command_run,
        wait_state=wait_state,
        run_id=run_id,
    )
    assert command_run is not None
    if command_run.state in {state.value for state in TERMINAL_COMMAND_RUN_STATES}:
        raise command_run_conflict(f"command run '{run_id}' is already terminal")


def ensure_command_run_owns_active_wait(
    *,
    command_run: CommandRunModel | None,
    wait_state: FlowWaitStateModel | None,
    run_id: str,
) -> None:
    if command_run is None:
        raise command_run_conflict(f"command run '{run_id}' is not current")
    if (
        wait_state is None
        or wait_state.waiting_cause != WaitingCause.WAITING_FOR_COMMAND_RUN.value
        or wait_state.command_run_id != command_run.run_id
    ):
        raise command_run_conflict(
            f"command run '{run_id}' no longer owns the active command-run wait"
        )


__all__ = [
    "ensure_command_run_can_be_cancelled",
    "ensure_command_run_can_be_claimed_for_local_start",
    "ensure_command_run_can_record_owned_process_pid",
    "ensure_command_run_can_record_progress",
    "ensure_command_run_can_record_terminal_result",
    "ensure_command_run_owns_active_wait",
]
