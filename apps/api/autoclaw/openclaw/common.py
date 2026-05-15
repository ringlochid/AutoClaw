from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from app.db.session import get_session_factory
from app.runtime.effects import run_runtime_write
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


async def run_runtime_write_operation(
    operation: Callable[[AsyncSession], Awaitable[ResultT]],
) -> ResultT:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await run_runtime_write(
            session,
            lambda: operation(session),
        )


__all__ = [
    "default_transport_security",
    "run_read_operation",
    "run_runtime_write_operation",
]
