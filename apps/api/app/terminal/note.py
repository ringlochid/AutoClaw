from __future__ import annotations

import shutil

from app.terminal.prompt_style import style_prompt_title
from app.terminal.theme import muted


def _wrap_line(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def wrap_note_message(message: str, *, width: int | None = None) -> list[str]:
    columns = shutil.get_terminal_size((100, 20)).columns
    max_width = max(40, min(width or columns - 6, 88))
    wrapped: list[str] = []
    for raw_line in message.splitlines() or [""]:
        wrapped.extend(_wrap_line(raw_line, max_width))
    return wrapped


def render_note(message: str, title: str | None = None, *, rich: bool) -> str:
    lines = wrap_note_message(message)
    content_width = max([len(line) for line in lines] + [len(title or "")])
    border = "┌" + "─" * (content_width + 2) + "┐"
    footer = "└" + "─" * (content_width + 2) + "┘"
    rendered: list[str] = [border]
    styled_title = style_prompt_title(title, rich=rich)
    if styled_title:
        pad = max(content_width - len(title or ""), 0)
        rendered.append(f"│ {styled_title}{' ' * pad} │")
        rendered.append("├" + "─" * (content_width + 2) + "┤")
    for line in lines:
        styled_line = muted(line, rich=rich)
        rendered.append(f"│ {styled_line}{' ' * (content_width - len(line))} │")
    rendered.append(footer)
    return "\n".join(rendered)


def note(message: str, title: str | None = None, *, rich: bool) -> None:
    print(render_note(message, title, rich=rich))


__all__ = ["note", "render_note", "wrap_note_message"]
