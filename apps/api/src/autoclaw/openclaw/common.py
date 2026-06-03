from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TypeVar

from app.db.session import get_session_factory
from app.file_entrypoints import load_yaml_mapping, resolved_input_path
from app.runtime.effects import (
    commit_runtime_session,
    rollback_runtime_session,
    run_runtime_write,
    wait_for_runtime_effects,
)
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.ext.asyncio import AsyncSession

ResultT = TypeVar("ResultT")

_DEFAULT_ALLOWED_HOSTS = (
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
)
_DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1",
    "http://127.0.0.1:*",
    "http://localhost",
    "http://localhost:*",
)


def default_transport_security(
    *,
    host: str,
    extra_hosts: Sequence[str] = (),
    extra_origins: Sequence[str] = (),
) -> TransportSecuritySettings:
    allowed_hosts = list(dict.fromkeys((*_DEFAULT_ALLOWED_HOSTS, host, f"{host}:*", *extra_hosts)))
    allowed_origins = list(
        dict.fromkeys(
            (
                *_DEFAULT_ALLOWED_ORIGINS,
                f"http://{host}",
                f"http://{host}:*",
                *extra_origins,
            )
        )
    )
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


async def run_read_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await operation(session)


async def run_session_write_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def run_runtime_write_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await run_runtime_write(
            session,
            lambda: operation(session),
        )


async def run_runtime_write_operation_and_wait(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
    *,
    task_id_getter: Callable[[ResultT], str],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await operation(session)
            await commit_runtime_session(session)
            await wait_for_runtime_effects(task_id=task_id_getter(result))
            return result
        except Exception:
            await rollback_runtime_session(session)
            raise


def resolved_path(path_value: str) -> Path:
    return resolved_input_path(path_value)


__all__ = [
    "default_transport_security",
    "load_yaml_mapping",
    "resolved_path",
    "run_read_operation",
    "run_runtime_write_operation",
    "run_runtime_write_operation_and_wait",
    "run_session_write_operation",
]
