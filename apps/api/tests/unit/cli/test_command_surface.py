from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import cast

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.persistence.session import dispose_db_engine
from click import Group
from click.testing import CliRunner

from .cli_test_support import (
    build_cli_init_args,
    configure_openclaw_gateway_env,
    write_openclaw_gateway_config,
)


def test_build_parser_supports_baseline_commands() -> None:
    parser = cli.build_parser()
    runner = CliRunner()

    result = runner.invoke(parser, ["--help"])
    configure_help = runner.invoke(parser, ["configure", "--help"])
    service_install_help = runner.invoke(parser, ["service", "install", "--help"])

    assert result.exit_code == 0
    assert configure_help.exit_code == 0
    assert service_install_help.exit_code == 0
    assert "onboard" in result.output
    assert "configure" in result.output
    assert "doctor" in result.output
    assert "--port INTEGER" in configure_help.output
    assert "--port INTEGER" in service_install_help.output
    assert "openclaw" in parser.commands
    assert "service" in parser.commands
    assert "definitions" in parser.commands
    assert "task-compose" in parser.commands
    openclaw_group = cast(Group, parser.commands["openclaw"])
    service_group = cast(Group, parser.commands["service"])
    definitions_group = cast(Group, parser.commands["definitions"])
    task_compose_group = cast(Group, parser.commands["task-compose"])
    assert "check" in openclaw_group.commands
    assert "setup" in openclaw_group.commands
    assert "doctor" in openclaw_group.commands
    assert "install" in service_group.commands
    assert "status" in service_group.commands
    assert "import" in definitions_group.commands
    assert "start" in task_compose_group.commands


def test_render_service_unit_uses_python_module_entrypoint(tmp_path: Path) -> None:
    rendered = cli.render_service_unit(
        python_bin=Path("/tmp/autoclaw-venv/bin/python"),
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        env_file=tmp_path / "autoclaw.env",
    )

    assert "ExecStartPre=/tmp/autoclaw-venv/bin/python -m autoclaw openclaw check" in rendered
    assert "ExecStartPre=/tmp/autoclaw-venv/bin/python -m autoclaw db upgrade" in rendered
    assert "ExecStart=/tmp/autoclaw-venv/bin/python -m autoclaw serve" in rendered


def test_serve_fails_fast_when_openclaw_support_is_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    write_openclaw_gateway_config(openclaw_config)
    configure_openclaw_gateway_env(
        monkeypatch,
        config_path=openclaw_config,
        binary_path=tmp_path / "missing-openclaw",
    )
    run_called = False

    def unexpected_uvicorn_run(*args: object, **kwargs: object) -> None:
        nonlocal run_called
        run_called = True

    monkeypatch.setattr("uvicorn.run", unexpected_uvicorn_run)

    try:
        asyncio.run(cli.cmd_init(build_cli_init_args(config_path, data_dir)))
        capsys.readouterr()
        result = cli.cmd_serve(argparse.Namespace(config=str(config_path)))
    finally:
        asyncio.run(dispose_db_engine())

    assert result == 1
    assert run_called is False
    assert "OpenClaw preflight failed" in capsys.readouterr().out
