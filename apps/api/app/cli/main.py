from __future__ import annotations

import sys

import click

from .context import scan_cli_context
from .failure_output import emit_click_exception, emit_unexpected_exception
from .root import cli


def build_parser() -> click.Group:
    return cli


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    runtime = scan_cli_context(argv_list)
    try:
        result = cli.main(
            args=argv_list,
            prog_name="autoclaw",
            standalone_mode=False,
            obj=runtime,
        )
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)
    except click.ClickException as exc:
        emit_click_exception(runtime, exc, runtime.argv)
        return int(exc.exit_code)
    except click.exceptions.Abort:
        return 2
    except BaseException as exc:
        emit_unexpected_exception(runtime, exc)
        return 1
    return int(result) if isinstance(result, int) else 0
