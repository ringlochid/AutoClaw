from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

STARTUP_AUDIT_PAGE_SIZE = 200
STARTUP_AUDIT_PAGE_GUARD = 10_000


class StartupAuditPaginationError(RuntimeError):
    """The finite startup audit cannot prove that indexed paging is progressing."""


@dataclass(frozen=True)
class StartupAuditPage[SourceT, CursorT]:
    """One bounded page of exact recoverable source rows."""

    sources: tuple[SourceT, ...]
    next_cursor: CursorT | None


async def audit_startup_source_family[SourceT, CursorT](
    *,
    family_name: str,
    fetch_page: Callable[
        [CursorT | None, int],
        Awaitable[StartupAuditPage[SourceT, CursorT]],
    ],
    route_source: Callable[[SourceT], Awaitable[None]],
    cursor_advances: Callable[[CursorT, CursorT], bool],
) -> int:
    """Page one source family and route each exact row through its handler.

    ``cursor_advances`` receives the previous cursor followed by the candidate
    next cursor.
    """

    cursor: CursorT | None = None
    pages_read = 0
    sources_routed = 0

    while True:
        page = await fetch_page(cursor, STARTUP_AUDIT_PAGE_SIZE)
        pages_read += 1
        if pages_read >= STARTUP_AUDIT_PAGE_GUARD:
            raise StartupAuditPaginationError(
                f"startup audit family {family_name!r} reached the "
                f"{STARTUP_AUDIT_PAGE_GUARD}-page bug guard"
            )
        if len(page.sources) > STARTUP_AUDIT_PAGE_SIZE:
            raise StartupAuditPaginationError(
                f"startup audit family {family_name!r} returned "
                f"{len(page.sources)} sources for a {STARTUP_AUDIT_PAGE_SIZE}-row page"
            )

        next_cursor = page.next_cursor
        if cursor is not None and next_cursor is not None:
            if not cursor_advances(cursor, next_cursor):
                raise StartupAuditPaginationError(
                    f"startup audit family {family_name!r} returned a non-advancing cursor"
                )

        for source in page.sources:
            await route_source(source)
            sources_routed += 1

        if next_cursor is None:
            return sources_routed
        cursor = next_cursor


__all__ = [
    "STARTUP_AUDIT_PAGE_GUARD",
    "STARTUP_AUDIT_PAGE_SIZE",
    "StartupAuditPage",
    "StartupAuditPaginationError",
    "audit_startup_source_family",
]
