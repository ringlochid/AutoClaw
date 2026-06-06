from __future__ import annotations

from typing import cast


def current_dispatch_history_entry(trace_json: dict[str, object]) -> dict[str, str]:
    return cast(list[dict[str, str]], trace_json["dispatch_history"])[0]


__all__ = ["current_dispatch_history_entry"]
