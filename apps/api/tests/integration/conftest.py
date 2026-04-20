from __future__ import annotations

import importlib
import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.db.base import Base

os.environ.setdefault("AUTOCLAW_ENV", "test")
os.environ.setdefault("AUTOCLAW_API_KEY", "autoclaw-operator-test-key")
os.environ.setdefault("AUTOCLAW_INTERNAL_API_KEY", "autoclaw-internal-test-key")

get_settings.cache_clear()

importlib.import_module("app.db.models")

TEST_DATABASE_URL = os.getenv(
    "AUTOCLAW_DATABASE_URL",
    "postgresql+asyncpg://autoclaw:autoclaw@localhost:5433/autoclaw_test",
)


@pytest_asyncio.fixture()
async def test_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def reset_database(test_engine: AsyncEngine) -> AsyncIterator[None]:
    async with test_engine.begin() as connection:
        try:
            await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        except DBAPIError:
            await connection.rollback()
            async with test_engine.connect() as cleanup_connection:
                await cleanup_connection.execution_options(isolation_level="AUTOCOMMIT")
                await cleanup_connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = current_database() AND pid <> pg_backend_pid()"
                    )
                )
            async with test_engine.begin() as retry_connection:
                await retry_connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                await retry_connection.execute(text("CREATE SCHEMA public"))
                await retry_connection.run_sync(Base.metadata.create_all)
            yield
            return
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture()
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
