from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast

import pytest
from autoclaw.config import RuntimeSettings
from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.post_commit import dispatch_reconcile
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession


def _runtime_settings(
    *,
    provider_wait_timeout_slice_ms: int = 5000,
    terminal_truth_commit_grace_seconds: float = 0.5,
    terminal_truth_commit_poll_interval_seconds: float = 0.01,
) -> RuntimeSettings:
    return RuntimeSettings(
        provider_wait_timeout_slice_ms=provider_wait_timeout_slice_ms,
        terminal_truth_commit_grace_seconds=terminal_truth_commit_grace_seconds,
        terminal_truth_commit_poll_interval_seconds=terminal_truth_commit_poll_interval_seconds,
    )


def test_gateway_wait_timeout_uses_configured_slice_without_deadline(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dispatch_reconcile,
        "get_settings",
        lambda: SimpleNamespace(runtime=_runtime_settings(provider_wait_timeout_slice_ms=1234)),
    )

    dispatch = cast(
        DispatchTurnModel,
        SimpleNamespace(control_deadline_at=None),
    )

    assert dispatch_reconcile.gateway_wait_timeout_ms(dispatch) == 1234


def test_gateway_wait_timeout_caps_wait_to_remaining_deadline(
    monkeypatch: MonkeyPatch,
) -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)
    monkeypatch.setattr(
        dispatch_reconcile,
        "get_settings",
        lambda: SimpleNamespace(runtime=_runtime_settings(provider_wait_timeout_slice_ms=5000)),
    )
    monkeypatch.setattr(dispatch_reconcile, "utc_now", lambda: now)

    dispatch = cast(
        DispatchTurnModel,
        SimpleNamespace(control_deadline_at=now + timedelta(milliseconds=400)),
    )

    assert dispatch_reconcile.gateway_wait_timeout_ms(dispatch) == 400


@pytest.mark.asyncio
async def test_gateway_dispatch_without_run_id_is_not_provider_poll_pending(
    monkeypatch: MonkeyPatch,
) -> None:
    async def no_terminal_truth(*_args: object, **_kwargs: object) -> bool:
        return False

    async def fail_if_wait_called(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("agent.wait must not run without a gateway_run_id")

    monkeypatch.setattr(
        dispatch_reconcile,
        "_fence_if_terminal_truth_committed",
        no_terminal_truth,
    )
    monkeypatch.setattr(
        dispatch_reconcile.dispatch_gateway,
        "wait_for_gateway_dispatch",
        fail_if_wait_called,
    )
    dispatch = cast(
        DispatchTurnModel,
        SimpleNamespace(control_state="live", gateway_run_id=None),
    )

    pending, changed = await dispatch_reconcile.reconcile_gateway_dispatch(
        cast(AsyncSession, object()),
        task_id="task-no-run-id",
        flow=cast(FlowModel, object()),
        dispatch=dispatch,
    )

    assert pending is False
    assert changed is False
