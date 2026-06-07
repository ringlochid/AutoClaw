from __future__ import annotations

from types import SimpleNamespace

from autoclaw.config import RuntimeSettings
from autoclaw.runtime.dispatch.openclaw import event_ingest
from pytest import MonkeyPatch


def _runtime_settings(*, openclaw_event_poll_timeout_seconds: float) -> RuntimeSettings:
    return RuntimeSettings(openclaw_event_poll_timeout_seconds=openclaw_event_poll_timeout_seconds)


def test_openclaw_event_poll_timeout_uses_configured_runtime_setting(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        event_ingest,
        "get_settings",
        lambda: SimpleNamespace(runtime=_runtime_settings(openclaw_event_poll_timeout_seconds=0.2)),
    )

    assert event_ingest.openclaw_event_poll_timeout_seconds() == 0.2
