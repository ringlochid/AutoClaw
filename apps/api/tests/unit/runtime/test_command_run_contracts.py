from __future__ import annotations

from datetime import UTC, datetime

import pytest
from autoclaw.runtime.contracts import (
    COMMAND_RUN_TERMINAL_EVENT_TYPES,
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunRecord,
    CommandRunState,
    CommandRunTerminalResult,
    CommandRunTerminalSource,
    PromptCommandOutcome,
    PromptCommandResult,
    PromptCommandTerminalSource,
    TaskEventType,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 18, tzinfo=UTC)


def test_abandoned_is_a_terminal_command_state_with_its_own_event() -> None:
    assert CommandRunState.ABANDONED in TERMINAL_COMMAND_RUN_STATES
    assert (
        COMMAND_RUN_TERMINAL_EVENT_TYPES[CommandRunState.ABANDONED]
        == TaskEventType.COMMAND_RUN_ABANDONED
    )


def test_abandoned_command_record_requires_ownership_lost_diagnostic() -> None:
    payload = {
        "run_id": "command-run.target",
        "task_id": "task.target",
        "dispatch_id": "dispatch.target",
        "command": "true",
        "description": "Run a target command.",
        "state": CommandRunState.ABANDONED,
        "created_at": NOW,
        "started_at": NOW,
        "ended_at": NOW,
        "terminal_result": CommandRunTerminalResult(
            summary="Command ownership was lost during restart.",
            failure_code="command_ownership_lost",
        ),
        "terminal_event_source": CommandRunTerminalSource.PROCESS_OWNER,
    }

    record = CommandRunRecord.model_validate(payload)

    assert record.state == CommandRunState.ABANDONED
    assert record.terminal_result is not None
    assert record.terminal_result.failure_code == "command_ownership_lost"

    payload["terminal_result"] = CommandRunTerminalResult(
        summary="Command ownership was lost during restart.",
        failure_code="process_not_found",
    )
    with pytest.raises(ValidationError, match="command_ownership_lost"):
        CommandRunRecord.model_validate(payload)


def test_abandoned_prompt_result_requires_ownership_lost_diagnostic() -> None:
    result = PromptCommandResult(
        state=PromptCommandOutcome.ABANDONED,
        summary="Command ownership was lost during restart.",
        started_at=NOW,
        ended_at=NOW,
        failure_code="command_ownership_lost",
        terminal_event_source=PromptCommandTerminalSource.CONTROLLER,
    )

    assert result.failure_code == "command_ownership_lost"

    with pytest.raises(ValidationError, match="command_ownership_lost"):
        PromptCommandResult(
            state=PromptCommandOutcome.ABANDONED,
            summary="Command ownership was lost during restart.",
            started_at=NOW,
            ended_at=NOW,
            failure_code="process_not_found",
            terminal_event_source=PromptCommandTerminalSource.CONTROLLER,
        )
