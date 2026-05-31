from __future__ import annotations

import click

from .context import CliContext
from .errors import CliFailure, failure_from_click_exception, unexpected_failure
from .json_output import emit_json
from .render import render_failure


def emit_failure(
    context: CliContext,
    failure: CliFailure,
    *,
    exc: BaseException | None = None,
) -> None:
    if context.json_output:
        emit_json(
            {
                "ok": False,
                "error": {
                    "kind": failure.kind,
                    "message": failure.message,
                    "hint": failure.hint,
                    "details": failure.details,
                },
            }
        )
        return
    render_failure(context, failure, exc)


def emit_click_exception(
    context: CliContext,
    exc: click.ClickException,
    argv: tuple[str, ...],
) -> None:
    emit_failure(context, failure_from_click_exception(exc, argv), exc=exc)


def emit_unexpected_exception(context: CliContext, exc: BaseException) -> None:
    emit_failure(context, unexpected_failure(exc), exc=exc)
