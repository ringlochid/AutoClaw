from __future__ import annotations

from typing import cast

import pytest
from autoclaw.runtime.command_run import list_command_runs
from autoclaw.runtime.contracts import OperationFailureCode
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.flow import runtime_flow_read
from autoclaw.runtime.observability import operator_snapshot
from sqlalchemy.ext.asyncio import AsyncSession


async def test_flow_read_reports_nonretryable_unavailable_capability() -> None:
    with pytest.raises(RuntimeOperationError) as error:
        await runtime_flow_read(_unused_session(), "task-1")

    assert error.value.code == OperationFailureCode.ILLEGAL_STATE
    assert error.value.is_retryable is False
    assert error.value.summary == "runtime flow reads and controls are not available in this build"
    assert error.value.suggested_next_step == (
        "Do not retry this request; use only the controller capabilities exposed by "
        "this installation."
    )


async def test_observability_reports_nonretryable_unavailable_capability() -> None:
    with pytest.raises(RuntimeOperationError) as error:
        await operator_snapshot(_unused_session(), "task-1")

    assert error.value.code == OperationFailureCode.ILLEGAL_STATE
    assert error.value.is_retryable is False
    assert error.value.summary == (
        "operator snapshots, traces, and observability refs are not available in this build"
    )
    assert error.value.suggested_next_step == (
        "Do not retry this request; use only the controller capabilities exposed by "
        "this installation."
    )


async def test_command_run_reports_nonretryable_unavailable_capability() -> None:
    with pytest.raises(RuntimeOperationError) as error:
        await list_command_runs(_unused_session(), task_id="task-1")

    assert error.value.code == OperationFailureCode.ILLEGAL_STATE
    assert error.value.is_retryable is False
    assert error.value.summary == (
        "command-run execution and readback are not available in this build"
    )
    assert error.value.suggested_next_step == (
        "Do not retry this request; use only the controller capabilities exposed by "
        "this installation."
    )


def _unused_session() -> AsyncSession:
    return cast(AsyncSession, object())
