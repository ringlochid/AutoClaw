from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest

from app import cli
from app import config as config_module
from app.db.session import dispose_db_engine


@pytest.mark.asyncio
async def test_init_uses_data_dir_default_sqlite_path_and_runs_upgrade(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    expected_database_url = config_module.default_database_url(data_dir)

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATA_DIR", raising=False)
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)

    args = argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        sqlite_path=None,
        host=None,
        port=None,
        openclaw_base_url=None,
        openclaw_agent_id=None,
        openclaw_timeout_ms=None,
        openclaw_account=None,
        log_level=None,
        api_key=None,
        internal_api_key=None,
        non_interactive=True,
        force=True,
        skip_bootstrap=True,
        skip_db_upgrade=False,
        revision="head",
        json=True,
    )

    try:
        result = await cli._cmd_init(args)
    finally:
        await dispose_db_engine()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["config_path"] == str(config_path)
    assert payload["database_url"] == expected_database_url
    assert config_path.exists()
    assert data_dir.joinpath("autoclaw.db").exists()
    assert f'url = "{expected_database_url}"' in config_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_init_writes_selected_runtime_options_to_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATA_DIR", raising=False)
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)

    args = argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        sqlite_path=None,
        host="0.0.0.0",
        port=8015,
        openclaw_base_url="http://127.0.0.1:19000",
        openclaw_agent_id="autoclaw-test-agent",
        openclaw_timeout_ms=3210,
        openclaw_account="orin_b",
        log_level="DEBUG",
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        non_interactive=True,
        force=True,
        skip_bootstrap=True,
        skip_db_upgrade=True,
        revision="head",
        json=True,
    )

    try:
        result = await cli._cmd_init(args)
    finally:
        await dispose_db_engine()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True

    config_text = config_path.read_text(encoding="utf-8")
    assert 'host = "0.0.0.0"' in config_text
    assert "port = 8015" in config_text
    assert 'base_url = "http://127.0.0.1:19000"' in config_text
    assert 'agent_id = "autoclaw-test-agent"' in config_text
    assert "timeout_ms = 3210" in config_text
    assert 'account = "orin_b"' in config_text
    assert 'level = "DEBUG"' in config_text
    assert 'api_key = "api-test-key"' in config_text
    assert 'internal_api_key = "internal-test-key"' in config_text


def test_build_parser_supports_up_and_service_commands() -> None:
    parser = cli.build_parser()

    up_args = parser.parse_args(["up", "--port", "8015"])
    assert up_args.handler is cli._cmd_up
    assert up_args.port == 8015

    init_args = parser.parse_args(["init", "--non-interactive"])
    assert init_args.handler is cli._cmd_init
    assert init_args.non_interactive is True

    service_args = parser.parse_args(["service", "up"])
    assert service_args.handler is cli._cmd_service_action
    assert service_args.service_command == "up"


def test_render_service_unit_uses_python_module_entrypoint(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    data_dir = tmp_path / "data"
    env_file = tmp_path / "autoclaw.env"

    rendered = cli._render_service_unit(
        python_bin=Path("/tmp/autoclaw-venv/bin/python"),
        config_path=config_path,
        data_dir=data_dir,
        env_file=env_file,
    )

    assert "ExecStartPre=/tmp/autoclaw-venv/bin/python -m autoclaw db upgrade" in rendered
    assert "ExecStart=/tmp/autoclaw-venv/bin/python -m autoclaw serve" in rendered
    assert f"Environment=AUTOCLAW_CONFIG={config_path}" in rendered
    assert f"EnvironmentFile=-{env_file}" in rendered


def test_detect_local_openclaw_base_url_prefers_running_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    calls: list[str] = []

    def fake_get(url: str, *, timeout: object, follow_redirects: bool) -> FakeResponse:
        del timeout, follow_redirects
        calls.append(url)
        if url.startswith("http://127.0.0.1:18789/"):
            return FakeResponse(200)
        raise cli.httpx.ConnectError("not running")

    monkeypatch.setattr(cli.httpx, "get", fake_get)
    settings = config_module.load_settings()
    args = argparse.Namespace(openclaw_base_url=None)

    detected_url, detected = cli._detect_local_openclaw_base_url(args, settings)

    assert detected is True
    assert detected_url == "http://127.0.0.1:18789"
    assert calls


def test_run_init_wizard_handles_string_data_dir_for_sqlite_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    answers = iter(
        [
            str(tmp_path / "wizard-config.toml"),
            str(tmp_path / "wizard-data"),
            "sqlite",
            str(tmp_path / "wizard-data" / "wizard.db"),
            "local",
            "8001",
            "http://127.0.0.1:18789",
            "wizard-agent",
            "orin_a",
            "INFO",
            False,
            False,
            True,
        ]
    )

    class FakePrompt:
        def ask(self) -> object:
            return next(answers)

    class FakeQuestionary:
        class Choice:
            def __init__(self, title: str, value: str) -> None:
                self.title = title
                self.value = value

        @staticmethod
        def text(*_args: object, **_kwargs: object) -> FakePrompt:
            return FakePrompt()

        @staticmethod
        def select(*_args: object, **_kwargs: object) -> FakePrompt:
            return FakePrompt()

        @staticmethod
        def confirm(*_args: object, **_kwargs: object) -> FakePrompt:
            return FakePrompt()

    class FakeConsole:
        def print(self, *_args: object, **_kwargs: object) -> None:
            return None

        def rule(self, *_args: object, **_kwargs: object) -> None:
            return None

    class FakePanel:
        @staticmethod
        def fit(*_args: object, **_kwargs: object) -> str:
            return "panel"

    monkeypatch.setattr(
        cli,
        "_load_init_prompt_libs",
        lambda: (FakeQuestionary, FakeConsole, FakePanel),
    )
    monkeypatch.setattr(
        cli,
        "_detect_local_openclaw_base_url",
        lambda _args, _settings: ("http://127.0.0.1:18789", True),
    )

    args = argparse.Namespace(
        config=None,
        data_dir=None,
        database_url=None,
        sqlite_path=None,
        host=None,
        port=None,
        openclaw_base_url=None,
        openclaw_agent_id=None,
        openclaw_account=None,
        log_level=None,
        skip_bootstrap=False,
        skip_db_upgrade=False,
        force=False,
    )

    cli._run_init_wizard(args, config_module.load_settings())

    assert args.sqlite_path == str(tmp_path / "wizard-data" / "wizard.db")
    assert args.config == str(tmp_path / "wizard-config.toml")
    assert args.data_dir == str(tmp_path / "wizard-data")
    assert args.skip_db_upgrade is True
    assert args.skip_bootstrap is True


@pytest.mark.asyncio
async def test_init_uses_interactive_wizard_answers_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "wizard-config.toml"
    data_dir = tmp_path / "wizard-data"

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATA_DIR", raising=False)
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)
    monkeypatch.setattr(cli, "_supports_interactive_init", lambda _args: True)

    def fake_wizard(args: argparse.Namespace, _settings: object) -> None:
        args.config = str(config_path)
        args.data_dir = str(data_dir)
        args.sqlite_path = str(data_dir / "wizard.db")
        args.database_url = None
        args.host = "0.0.0.0"
        args.port = 8123
        args.openclaw_base_url = "http://127.0.0.1:19999"
        args.openclaw_agent_id = "wizard-agent"
        args.openclaw_account = "orin_wizard"
        args.log_level = "DEBUG"
        args.skip_db_upgrade = True
        args.skip_bootstrap = True
        args.force = True

    monkeypatch.setattr(cli, "_run_init_wizard", fake_wizard)

    args = argparse.Namespace(
        config=None,
        data_dir=None,
        database_url=None,
        sqlite_path=None,
        host=None,
        port=None,
        openclaw_base_url=None,
        openclaw_agent_id=None,
        openclaw_timeout_ms=None,
        openclaw_account=None,
        log_level=None,
        api_key=None,
        internal_api_key=None,
        non_interactive=False,
        force=False,
        skip_bootstrap=False,
        skip_db_upgrade=False,
        revision="head",
        json=True,
    )

    try:
        result = await cli._cmd_init(args)
    finally:
        await dispose_db_engine()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True

    config_text = config_path.read_text(encoding="utf-8")
    assert 'host = "0.0.0.0"' in config_text
    assert "port = 8123" in config_text
    assert 'base_url = "http://127.0.0.1:19999"' in config_text
    assert 'agent_id = "wizard-agent"' in config_text
    assert 'account = "orin_wizard"' in config_text
    assert 'level = "DEBUG"' in config_text
    assert data_dir.joinpath("wizard.db").parent.exists()


@pytest.mark.asyncio
async def test_init_interactive_flow_offers_service_install_after_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "service-config.toml"
    data_dir = tmp_path / "service-data"
    prompted: list[tuple[Path, Path]] = []

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATA_DIR", raising=False)
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)
    monkeypatch.setattr(cli, "_supports_interactive_init", lambda _args: True)

    def fake_wizard(args: argparse.Namespace, _settings: object) -> None:
        args.config = str(config_path)
        args.data_dir = str(data_dir)
        args.sqlite_path = str(data_dir / "service.db")
        args.database_url = None
        args.host = "127.0.0.1"
        args.port = 8001
        args.openclaw_base_url = "http://127.0.0.1:18789"
        args.openclaw_agent_id = "wizard-agent"
        args.openclaw_account = "orin_a"
        args.log_level = "INFO"
        args.skip_db_upgrade = True
        args.skip_bootstrap = True
        args.force = True

    def fake_prompt_service_install(
        _args: argparse.Namespace,
        *,
        config_path: Path,
        data_dir: Path,
    ) -> None:
        prompted.append((config_path, data_dir))

    monkeypatch.setattr(cli, "_run_init_wizard", fake_wizard)
    monkeypatch.setattr(cli, "_prompt_install_service_after_init", fake_prompt_service_install)

    args = argparse.Namespace(
        config=None,
        data_dir=None,
        database_url=None,
        sqlite_path=None,
        host=None,
        port=None,
        openclaw_base_url=None,
        openclaw_agent_id=None,
        openclaw_timeout_ms=None,
        openclaw_account=None,
        log_level=None,
        api_key=None,
        internal_api_key=None,
        non_interactive=False,
        force=False,
        skip_bootstrap=False,
        skip_db_upgrade=False,
        revision="head",
        json=False,
    )

    try:
        result = await cli._cmd_init(args)
    finally:
        await dispose_db_engine()

    assert result == 0
    assert prompted == [(config_path, data_dir)]
    output = capsys.readouterr().out
    assert "Initialized AutoClaw" in output


def test_service_install_writes_unit_and_runs_systemctl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config" / "config.toml"
    data_dir = tmp_path / "data"
    unit_dir = tmp_path / "systemd" / "user"
    env_file = tmp_path / "config" / "autoclaw.env"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
[app]
name = "autoclaw"

[database]
url = "sqlite+aiosqlite:///tmp/autoclaw.db"

[paths]
data_dir = "/tmp/autoclaw-data"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli, "_run_command", fake_run)
    monkeypatch.setattr(cli, "_ensure_binary_available", lambda _binary: None)

    args = argparse.Namespace(
        name="autoclaw",
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        sqlite_path=None,
        env_file=str(env_file),
        unit_dir=str(unit_dir),
        force=True,
        no_start=True,
        json=False,
    )

    result = cli._cmd_service_install(args)

    unit_path = unit_dir / "autoclaw.service"
    assert result == 0
    assert unit_path.exists()
    assert env_file.exists()
    unit_text = unit_path.read_text(encoding="utf-8")
    assert "-m autoclaw serve --config" in unit_text
    assert commands == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "autoclaw.service"],
    ]
