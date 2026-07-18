from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import autoclaw.interfaces.cli as cli
import pytest
from click import Group
from click.testing import CliRunner


def test_build_parser_supports_baseline_commands() -> None:
    parser = cli.build_parser()
    runner = CliRunner()

    result = runner.invoke(parser, ["--help"])
    service_install_help = runner.invoke(parser, ["service", "install", "--help"])

    assert result.exit_code == 0
    assert service_install_help.exit_code == 0
    assert "onboard" not in parser.commands
    assert "configure" not in parser.commands
    assert "doctor" not in parser.commands
    assert "--port INTEGER" in service_install_help.output
    assert "openclaw" not in parser.commands
    assert "status" in parser.commands
    assert "setup" in parser.commands
    assert "providers" in parser.commands
    assert "service" in parser.commands
    assert "definitions" in parser.commands
    assert "task-compose" in parser.commands
    service_group = cast(Group, parser.commands["service"])
    definitions_group = cast(Group, parser.commands["definitions"])
    task_compose_group = cast(Group, parser.commands["task-compose"])
    providers_group = cast(Group, parser.commands["providers"])
    assert "install" in service_group.commands
    assert "status" in service_group.commands
    assert "import" in definitions_group.commands
    assert "start" in task_compose_group.commands
    assert set(providers_group.commands) == {
        "check",
        "configure",
        "list",
        "login",
        "logout",
        "set-default",
        "status",
    }


def test_render_service_unit_uses_python_module_entrypoint(tmp_path: Path) -> None:
    rendered = cli.render_service_unit(
        python_bin=Path("/tmp/autoclaw-venv/bin/python"),
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        env_file=tmp_path / "autoclaw.env",
    )

    assert "openclaw check" not in rendered
    assert "ExecStartPre=/tmp/autoclaw-venv/bin/python -m autoclaw db upgrade" in rendered
    assert "ExecStart=/tmp/autoclaw-venv/bin/python -m autoclaw serve" in rendered


def test_serve_does_not_run_global_provider_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        """
[openclaw]
enabled = true
gateway_url = "not-a-websocket-url"
gateway_profile = "experimental"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    run_called = False

    def unexpected_uvicorn_run(*args: object, **kwargs: object) -> None:
        nonlocal run_called
        run_called = True

    monkeypatch.setattr("uvicorn.run", unexpected_uvicorn_run)

    result = cli.cmd_serve(argparse.Namespace(config=str(config_path)))

    assert result == 0
    assert run_called is True
    assert "preflight" not in capsys.readouterr().out.casefold()
