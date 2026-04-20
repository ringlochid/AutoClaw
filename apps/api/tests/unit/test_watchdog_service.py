from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.runtime.watchdog_service import WatchdogService


class _FakeSession:
    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    async def commit(self) -> None:
        return None


class _FakeSessionFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


@pytest.mark.asyncio
async def test_run_tick_processes_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    flow_id = uuid4()
    calls: dict[str, list] = {"run": [], "recover": []}

    async def _list_candidates(
        session: object,
        *,
        stale_after_seconds: int,
        limit: int,
    ) -> list[UUID]:
        assert stale_after_seconds == 30
        assert limit == 5
        return [flow_id]

    async def _run_flow_watchdog(
        session: object,
        *,
        flow_id: UUID,
        stale_after_seconds: int,
    ) -> tuple[SimpleNamespace, list[UUID], list[object]]:
        calls["run"].append((flow_id, stale_after_seconds))
        return SimpleNamespace(id=flow_id), [uuid4()], [object()]

    async def _recover_flow_watchdog(
        session: object,
        *,
        flow_id: UUID,
    ) -> SimpleNamespace:
        calls["recover"].append(flow_id)
        return SimpleNamespace(recovery_action=SimpleNamespace(value="wake"))

    monkeypatch.setattr(
        "app.runtime.watchdog_service.list_watchdog_candidate_flow_ids",
        _list_candidates,
    )
    monkeypatch.setattr("app.runtime.watchdog_service.run_flow_watchdog", _run_flow_watchdog)
    monkeypatch.setattr(
        "app.runtime.watchdog_service.recover_flow_watchdog",
        _recover_flow_watchdog,
    )

    settings: Any = SimpleNamespace(
        watchdog_interval_seconds=15,
        watchdog_stale_after_seconds=30,
        watchdog_max_flows_per_tick=5,
        watchdog_auto_recover=True,
        watchdog_max_auto_recoveries_per_tick=2,
    )
    service = WatchdogService(
        settings=settings,
        session_factory=_FakeSessionFactory(),  # type: ignore[arg-type]
    )
    await service.run_tick()

    assert calls["run"] == [(flow_id, 30)]
    assert calls["recover"] == [flow_id]


@pytest.mark.asyncio
async def test_run_tick_skips_recovery_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    flow_id = uuid4()
    calls: dict[str, list] = {"recover": []}

    async def _list_candidates(
        session: object,
        *,
        stale_after_seconds: int,
        limit: int,
    ) -> list[UUID]:
        return [flow_id]

    async def _run_flow_watchdog(
        session: object,
        *,
        flow_id: UUID,
        stale_after_seconds: int,
    ) -> tuple[SimpleNamespace, list[UUID], list[object]]:
        return SimpleNamespace(id=flow_id), [uuid4()], [object()]

    async def _recover_flow_watchdog(
        session: object,
        *,
        flow_id: UUID,
    ) -> SimpleNamespace:
        calls["recover"].append(flow_id)
        return SimpleNamespace(recovery_action=SimpleNamespace(value="wake"))

    monkeypatch.setattr(
        "app.runtime.watchdog_service.list_watchdog_candidate_flow_ids",
        _list_candidates,
    )
    monkeypatch.setattr("app.runtime.watchdog_service.run_flow_watchdog", _run_flow_watchdog)
    monkeypatch.setattr(
        "app.runtime.watchdog_service.recover_flow_watchdog",
        _recover_flow_watchdog,
    )

    settings: Any = SimpleNamespace(
        watchdog_interval_seconds=15,
        watchdog_stale_after_seconds=30,
        watchdog_max_flows_per_tick=5,
        watchdog_auto_recover=False,
        watchdog_max_auto_recoveries_per_tick=2,
    )
    service = WatchdogService(
        settings=settings,
        session_factory=_FakeSessionFactory(),  # type: ignore[arg-type]
    )
    await service.run_tick()

    assert calls["recover"] == []
