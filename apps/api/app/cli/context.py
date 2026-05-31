from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from rich.console import Console

from .theme import build_rich_theme


@dataclass(frozen=True)
class CliContext:
    json_output: bool = False
    plain: bool = False
    no_color: bool = False
    debug: bool = False
    argv: tuple[str, ...] = ()

    def overlay(
        self,
        *,
        json_output: bool | None = None,
        plain: bool | None = None,
        no_color: bool | None = None,
        debug: bool | None = None,
        argv: tuple[str, ...] | None = None,
    ) -> CliContext:
        return CliContext(
            json_output=self.json_output if json_output is None else json_output,
            plain=self.plain if plain is None else plain,
            no_color=self.no_color if no_color is None else no_color,
            debug=self.debug if debug is None else debug,
            argv=self.argv if argv is None else argv,
        )

    def rich_enabled(self) -> bool:
        if self.json_output or self.plain or self.no_color:
            return False
        if os.environ.get("NO_COLOR"):
            return False
        return sys.stdout.isatty()

    def console(self, *, stderr: bool = False) -> Console:
        rich = self.rich_enabled()
        return Console(
            stderr=stderr,
            force_terminal=rich,
            no_color=not rich,
            theme=build_rich_theme(),
            soft_wrap=True,
        )


def scan_cli_context(argv: list[str]) -> CliContext:
    return CliContext(
        json_output="--json" in argv,
        plain="--plain" in argv,
        no_color="--no-color" in argv,
        debug=(
            "--debug" in argv
            or os.environ.get("AUTOCLAW_DEBUG", "").lower() in {"1", "true", "yes", "on"}
        ),
        argv=tuple(argv),
    )
