from __future__ import annotations

import getpass
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from app.terminal.note import note
from app.terminal.prompt_style import style_prompt_hint, style_prompt_message, style_prompt_title
from app.terminal.theme import rich_enabled


class PromptUnavailableError(RuntimeError):
    """Interactive prompts require a real TTY."""


@dataclass(frozen=True)
class SelectOption:
    value: str
    label: str
    hint: str | None = None


def _require_tty() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PromptUnavailableError("interactive prompting requires a TTY")


def confirm(message: str, *, default: bool = True) -> bool:
    _require_tty()
    rich = rich_enabled()
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{style_prompt_message(message, rich=rich)} {suffix} ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        note("Enter yes or no.", "Invalid input", rich=rich)


def text(
    message: str,
    *,
    default: str | None = None,
    hint: str | None = None,
    sensitive: bool = False,
) -> str:
    _require_tty()
    rich = rich_enabled()
    if hint:
        note(hint, "Hint", rich=rich)
    prompt_suffix = f" [{default}]" if default else ""
    while True:
        if sensitive:
            raw = getpass.getpass(
                f"{style_prompt_message(message, rich=rich)}{prompt_suffix}: "
            ).strip()
        else:
            raw = input(f"{style_prompt_message(message, rich=rich)}{prompt_suffix}: ").strip()
        if raw:
            return raw
        if default is not None:
            return default
        note("A value is required.", "Missing input", rich=rich)


def select(
    message: str,
    *,
    options: Sequence[SelectOption],
    default_index: int = 0,
    title: str | None = None,
) -> str:
    _require_tty()
    rich = rich_enabled()
    if title:
        styled_title = style_prompt_title(title, rich=rich)
        if styled_title:
            print(styled_title)
    print(style_prompt_message(message, rich=rich))
    for index, option in enumerate(options, start=1):
        hint = style_prompt_hint(option.hint, rich=rich)
        suffix = f" - {hint}" if hint else ""
        print(f"  {index}. {option.label}{suffix}")
    while True:
        raw = input(f"Select [default {default_index + 1}]: ").strip()
        if not raw:
            return options[default_index].value
        if raw.isdigit():
            selected = int(raw) - 1
            if 0 <= selected < len(options):
                return options[selected].value
        note("Enter one of the numbered options.", "Invalid input", rich=rich)


__all__ = ["PromptUnavailableError", "SelectOption", "confirm", "select", "text"]
