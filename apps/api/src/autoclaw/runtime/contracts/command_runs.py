from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import (
    CommandRunState,
    TaskEventType,
    TaskIdentifier,
)

TERMINAL_COMMAND_RUN_STATES = frozenset(
    {
        CommandRunState.SUCCEEDED,
        CommandRunState.FAILED,
        CommandRunState.TIMED_OUT,
        CommandRunState.CANCELLED,
    }
)

type CommandRunTerminalState = Literal[
    CommandRunState.SUCCEEDED,
    CommandRunState.FAILED,
    CommandRunState.TIMED_OUT,
    CommandRunState.CANCELLED,
]

COMMAND_RUN_TERMINAL_EVENT_TYPES = {
    CommandRunState.SUCCEEDED: TaskEventType.COMMAND_RUN_SUCCEEDED,
    CommandRunState.FAILED: TaskEventType.COMMAND_RUN_FAILED,
    CommandRunState.TIMED_OUT: TaskEventType.COMMAND_RUN_TIMED_OUT,
    CommandRunState.CANCELLED: TaskEventType.COMMAND_RUN_CANCELLED,
}


class CommandRunStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command: RuntimeSchemaText
    description: RuntimeSchemaText
    workdir: RuntimeSchemaText | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)


class CommandRunStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    run_id: RuntimeSchemaText
    task_id: TaskIdentifier
    state: Literal[CommandRunState.PENDING_START, CommandRunState.RUNNING]


class CommandRunTerminalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    summary: RuntimeSchemaText
    exit_code: int | None = None
    signal: RuntimeSchemaText | None = None
    log_ref: RuntimeSchemaText | None = None


class CommandRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    run_id: RuntimeSchemaText
    task_id: TaskIdentifier
    dispatch_id: RuntimeSchemaText
    attempt_id: RuntimeSchemaText | None = None
    command: RuntimeSchemaText
    description: RuntimeSchemaText
    workdir: RuntimeSchemaText | None = None
    state: CommandRunState
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    latest_update: RuntimeSchemaText | None = None
    latest_log_ref: RuntimeSchemaText | None = None
    terminal_result: CommandRunTerminalResult | None = None

    @model_validator(mode="after")
    def validate_terminal_result(self) -> CommandRunRecord:
        if self.state in TERMINAL_COMMAND_RUN_STATES:
            if self.terminal_result is None:
                raise ValueError("terminal command run states require terminal_result")
            if self.ended_at is None:
                raise ValueError("terminal command run states require ended_at")
            return self
        if self.terminal_result is not None:
            raise ValueError("non-terminal command run states must not set terminal_result")
        return self


class CommandRunProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    run_id: RuntimeSchemaText
    summary: RuntimeSchemaText
    log_ref: RuntimeSchemaText | None = None
    occurred_at: datetime


class CommandRunTerminalResultRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    run_id: RuntimeSchemaText
    state: CommandRunTerminalState
    summary: RuntimeSchemaText
    exit_code: int | None = None
    signal: RuntimeSchemaText | None = None
    log_ref: RuntimeSchemaText | None = None
    ended_at: datetime


class CommandRunListItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    run_id: RuntimeSchemaText
    state: CommandRunState
    command: RuntimeSchemaText
    description: RuntimeSchemaText | None = None
    workdir: RuntimeSchemaText | None = None
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    summary: RuntimeSchemaText | None = None
    exit_code: int | None = None
    signal: RuntimeSchemaText | None = None
    log_ref: RuntimeSchemaText | None = None


class CommandRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: TaskIdentifier
    items: tuple[CommandRunListItem, ...]
    next_cursor: RuntimeSchemaText | None = None


class CommandRunCancelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: TaskIdentifier
    run: CommandRunListItem


__all__ = [
    "COMMAND_RUN_TERMINAL_EVENT_TYPES",
    "TERMINAL_COMMAND_RUN_STATES",
    "CommandRunCancelResponse",
    "CommandRunListItem",
    "CommandRunListResponse",
    "CommandRunProgressUpdate",
    "CommandRunRecord",
    "CommandRunStartRequest",
    "CommandRunStartResponse",
    "CommandRunTerminalResult",
    "CommandRunTerminalResultRead",
    "CommandRunTerminalState",
]
