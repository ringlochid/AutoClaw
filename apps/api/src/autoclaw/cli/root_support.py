from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any, ParamSpec, TypeVar

import click

from autoclaw.paths import default_config_path

P = ParamSpec("P")
T = TypeVar("T")


def config_option(function: Callable[P, T]) -> Callable[P, T]:
    return click.option("--config", default=default_config_text, show_default=True)(function)


def output_options(function: Callable[P, T]) -> Callable[P, T]:
    function = click.option(
        "--no-color",
        is_flag=True,
        help="Disable ANSI color output.",
    )(function)
    function = click.option("--plain", is_flag=True, help="Disable rich styling.")(function)
    function = click.option(
        "--json",
        "json_output",
        is_flag=True,
        help="Emit JSON output only.",
    )(function)
    return function


def build_argument_namespace(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def invoke_handler_result(result: int | Any) -> int:
    if asyncio.iscoroutine(result):
        return int(asyncio.run(result))
    return int(result)


def default_config_text() -> str:
    return str(default_config_path())


def package_version() -> str:
    try:
        return version("autoclaw")
    except PackageNotFoundError:
        return "0.1.1"


__all__ = [
    "build_argument_namespace",
    "config_option",
    "invoke_handler_result",
    "output_options",
    "package_version",
]
