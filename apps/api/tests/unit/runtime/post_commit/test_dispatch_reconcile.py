from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast

from autoclaw.config import RuntimeSettings
from autoclaw.persistence.models import DispatchTurnModel
from autoclaw.runtime.post_commit import dispatch_reconcile
from pytest import MonkeyPatch


def _runtime_settings(*, provider_wait_timeout_slice_ms: int) -> RuntimeSettings:
    return RuntimeSettings(provider_wait_timeout_slice_ms=provider_wait_timeout_slice_ms)


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
