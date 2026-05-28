from __future__ import annotations

from app.terminal.theme import accent, heading, muted


def style_prompt_message(message: str, *, rich: bool) -> str:
    return accent(message, rich=rich)


def style_prompt_title(title: str | None, *, rich: bool) -> str | None:
    if title is None:
        return None
    return heading(title, rich=rich)


def style_prompt_hint(hint: str | None, *, rich: bool) -> str | None:
    if hint is None:
        return None
    return muted(hint, rich=rich)


__all__ = ["style_prompt_hint", "style_prompt_message", "style_prompt_title"]
