from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config import get_settings

_ENGINE_BY_LOOP: dict[int, AsyncEngine] = {}
_SESSION_FACTORY_BY_LOOP: dict[int, async_sessionmaker[AsyncSession]] = {}


def _loop_id() -> int:
    import asyncio

    return id(asyncio.get_running_loop())


def get_async_engine() -> AsyncEngine:
    settings = get_settings()
    loop_id = _loop_id()
    if loop_id not in _ENGINE_BY_LOOP:
        url = make_url(settings.database_url)
        engine_kwargs: dict[str, object] = {
            "echo": settings.debug,
        }
        if url.get_backend_name() == "sqlite":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if url.database in {None, "", ":memory:"}:
                engine_kwargs["poolclass"] = StaticPool
        else:
            engine_kwargs["pool_pre_ping"] = True

        _ENGINE_BY_LOOP[loop_id] = create_async_engine(
            settings.database_url,
            **engine_kwargs,
        )
    return _ENGINE_BY_LOOP[loop_id]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    loop_id = _loop_id()
    if loop_id not in _SESSION_FACTORY_BY_LOOP:
        _SESSION_FACTORY_BY_LOOP[loop_id] = async_sessionmaker(
            bind=get_async_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _SESSION_FACTORY_BY_LOOP[loop_id]


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def ping_database() -> None:
    async with get_session_factory()() as session:
        await session.execute(text("SELECT 1"))


async def dispose_db_engine() -> None:
    for engine in _ENGINE_BY_LOOP.values():
        await engine.dispose()
    _ENGINE_BY_LOOP.clear()
    _SESSION_FACTORY_BY_LOOP.clear()
