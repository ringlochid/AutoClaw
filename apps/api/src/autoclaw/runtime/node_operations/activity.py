from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NodeActivitySignal:
    task_id: str
    dispatch_id: str
    activity_revision: int
    occurred_at: datetime


type NodeActivitySignalPublisher = Callable[[NodeActivitySignal], Awaitable[None]]


__all__ = ["NodeActivitySignal", "NodeActivitySignalPublisher"]
