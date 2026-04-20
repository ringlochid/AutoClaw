from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.runtime.watchdog import recover_flow_watchdog, run_flow_watchdog
from app.runtime.watchdog_queries import list_watchdog_candidate_flow_ids

logger = logging.getLogger(__name__)


class WatchdogService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run_forever(), name="autoclaw-watchdog")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def run_forever(self) -> None:
        logger.info("watchdog service started")
        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_tick()
                except Exception:
                    logger.exception("watchdog tick failed")
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._settings.watchdog_interval_seconds,
                    )
                except TimeoutError:
                    pass
        except asyncio.CancelledError:
            logger.info("watchdog service cancelled")
            raise
        finally:
            logger.info("watchdog service stopped")

    async def run_tick(self) -> None:
        async with self._session_factory() as session:
            candidate_flow_ids = await list_watchdog_candidate_flow_ids(
                session,
                stale_after_seconds=self._settings.watchdog_stale_after_seconds,
                limit=self._settings.watchdog_max_flows_per_tick,
            )

        if not candidate_flow_ids:
            return

        auto_recoveries = 0
        for flow_id in candidate_flow_ids:
            async with self._session_factory() as session:
                flow, stalled_attempt_ids, checkpoints = await run_flow_watchdog(
                    session,
                    flow_id=flow_id,
                    stale_after_seconds=self._settings.watchdog_stale_after_seconds,
                )
                recovery_action = None
                if (
                    stalled_attempt_ids
                    and self._settings.watchdog_auto_recover
                    and auto_recoveries < self._settings.watchdog_max_auto_recoveries_per_tick
                ):
                    recovery_result = await recover_flow_watchdog(session, flow_id=flow.id)
                    recovery_action = recovery_result.recovery_action.value
                    if recovery_result.recovery_action.value == "wake":
                        auto_recoveries += 1
                await session.commit()
                if stalled_attempt_ids or checkpoints:
                    logger.info(
                        "watchdog tick flow=%s stalled_attempts=%s checkpoints=%s recovery=%s",
                        flow_id,
                        len(stalled_attempt_ids),
                        len(checkpoints),
                        recovery_action,
                    )
