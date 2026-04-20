from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import httpx
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
    definitions_root = config_path.parent / "definitions"
    config_text = config_path.read_text(encoding="utf-8")
    assert f'url = "{expected_database_url}"' in config_text
    assert f'definitions_root = "{definitions_root}"' in config_text
    assert definitions_root.joinpath("roles").is_dir()
    assert definitions_root.joinpath("policies").is_dir()
    assert definitions_root.joinpath("workflows").is_dir()


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
        definitions_root=str(tmp_path / "custom-definitions"),
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
    assert f'definitions_root = "{tmp_path / "custom-definitions"}"' in config_text
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

    task_compose_bootstrap_args = parser.parse_args(["task-compose", "bootstrap"])
    assert task_compose_bootstrap_args.handler is cli._cmd_db_bootstrap

    task_compose_args = parser.parse_args(["task-compose", "start", "./demo.yaml"])
    assert task_compose_args.handler is cli._cmd_task_compose_start
    assert task_compose_args.file == "./demo.yaml"


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


def test_validate_task_compose_payload_rejects_invalid_yaml_shape() -> None:
    with pytest.raises(ValueError) as exc_info:
        cli._validate_task_compose_payload({"workflow": {"key": "default-bugfix"}})

    message = str(exc_info.value)
    assert "Task compose YAML validation failed:" in message
    assert "metadata" in message


@pytest.mark.asyncio
async def test_task_compose_start_reads_yaml_and_posts_to_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        """
[app]
env = "test"
name = "autoclaw"

[server]
host = "127.0.0.1"
port = 8123

[security]
api_key = "task-compose-test-key"
internal_api_key = "task-compose-test-key"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    compose_path = tmp_path / "demo-compose.yaml"
    compose_path.write_text(
        """
metadata:
  title: Demo task
  description: YAML compose launch
workflow:
  key: max-complexity-review
input:
  brief: hello
roots:
  workspace: true
  context: true
  manifests: true
context_refs:
  - task_input
skill_dependencies:
  - key: contract-checker
    runtime_name: autoclaw-contract-checker
    required: true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "flow_id": "flow-1",
                "task_id": "task-1",
                "task_compose": {"id": "compose-1"},
            },
        )

    transport = httpx.MockTransport(handler)

    real_async_client = httpx.AsyncClient

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._client = real_async_client(base_url=base_url, timeout=timeout, transport=transport)

        async def __aenter__(self) -> httpx.AsyncClient:
            return self._client

        async def __aexit__(self, exc_type, exc, tb) -> None:
            await self._client.aclose()

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.setattr(cli.httpx, "AsyncClient", FakeAsyncClient)

    args = argparse.Namespace(file=str(compose_path), config=str(config_path), api_key=None, json=True)
    result = await cli._cmd_task_compose_start(args)

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["flow_id"] == "flow-1"
    assert payload["task_id"] == "task-1"
    assert captured["url"] == "http://127.0.0.1:8123/tasks/composes/start"
    assert captured["headers"]["x-autoclaw-api-key"] == "task-compose-test-key"
    body = json.loads(captured["body"])
    assert body["metadata"]["title"] == "Demo task"
    assert body["workflow"]["key"] == "max-complexity-review"
    assert body["skill_dependencies"][0]["runtime_name"] == "autoclaw-contract-checker"


async def test_doctor_reports_packaged_and_configured_definitions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "doctor-config.toml"
    data_dir = tmp_path / "doctor-data"
    definitions_root = tmp_path / "definitions"
    for kind in ("roles", "policies", "workflows"):
        kind_dir = definitions_root / kind
        kind_dir.mkdir(parents=True, exist_ok=True)
        kind_dir.joinpath(f"custom-{kind[:-1]}.yaml").write_text(
            f"id: custom-{kind[:-1]}\nname: Custom {kind[:-1]}\n",
            encoding="utf-8",
        )

    config_path.write_text(
        f"""
[app]
env = "development"
debug = false
name = "autoclaw"

[paths]
data_dir = "{data_dir}"
definitions_root = "{definitions_root}"

[database]
url = "sqlite+aiosqlite:///{data_dir / "autoclaw.db"}"

[openclaw]
base_url = "http://127.0.0.1:18789"
agent_id = "autoclaw-worker"
timeout_ms = 120000
account = "orin_a"

[server]
host = "127.0.0.1"
port = 8123
console_origins = []

[logging]
level = "INFO"

[security]
api_key = "doctor-key"
internal_api_key = "doctor-internal-key"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATA_DIR", raising=False)

    async def fake_ping_database() -> None:
        return None

    monkeypatch.setattr(cli, "ping_database", fake_ping_database)
    monkeypatch.setattr(cli, "_resolve_console_dist_root", lambda: tmp_path)

    args = argparse.Namespace(
        config=str(config_path),
        database_url=None,
        sqlite_path=None,
        json=True,
    )

    result = await cli._cmd_doctor(args)
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["resources"]["definitions"]["packaged"]["root"] == "app.resources:definitions"
    assert payload["resources"]["definitions"]["configured"]["root"] == str(definitions_root)
    assert payload["resources"]["definitions"]["configured"]["exists"] is True
    assert payload["resources"]["definitions"]["configured"]["roles"] == 1
    assert payload["resources"]["definitions"]["configured"]["policies"] == 1
    assert payload["resources"]["definitions"]["configured"]["workflows"] == 1


def test_prompt_yes_no_requires_enter_and_accepts_y_or_n() -> None:
    assert cli._parse_yes_no_text("", default=True) is True
    assert cli._parse_yes_no_text("", default=False) is False
    assert cli._parse_yes_no_text("y", default=False) is True
    assert cli._parse_yes_no_text("Y", default=False) is True
    assert cli._parse_yes_no_text("n", default=True) is False
    assert cli._parse_yes_no_text("N", default=True) is False
    assert cli._parse_yes_no_text("maybe", default=True) is None


def test_run_init_wizard_handles_string_data_dir_for_sqlite_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    answers = iter(
        [
            str(tmp_path / "wizard-config.toml"),
            str(tmp_path / "wizard-data"),
            str(tmp_path / "wizard-definitions"),
            "sqlite",
            str(tmp_path / "wizard-data" / "wizard.db"),
            "local",
            "8123",
            "http://127.0.0.1:18789",
            "wizard-agent",
            "orin_a",
            "INFO",
            "n",
            "n",
            "y",
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
    assert args.definitions_root == str(tmp_path / "wizard-definitions")
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
        args.definitions_root = str(config_path.parent / "definitions")
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
        args.definitions_root = str(config_path.parent / "definitions")
        args.sqlite_path = str(data_dir / "service.db")
        args.database_url = None
        args.host = "127.0.0.1"
        args.port = 8123
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



def test_resolve_database_url_falls_back_to_environment_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_url = "sqlite+aiosqlite:////tmp/env/autoclaw.db"
    monkeypatch.setenv("AUTOCLAW_DATABASE_URL", env_url)

    args = argparse.Namespace(database_url=None, sqlite_path=None)

    assert cli._resolve_database_url(args) == env_url


def test_resolve_database_url_prefers_cli_database_url_over_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_url = "sqlite+aiosqlite:////tmp/env/autoclaw.db"
    cli_url = "sqlite+aiosqlite:////tmp/cli/autoclaw.db"
    monkeypatch.setenv("AUTOCLAW_DATABASE_URL", env_url)

    args = argparse.Namespace(database_url=cli_url, sqlite_path=None)

    assert cli._resolve_database_url(args) == cli_url


def test_ensure_sqlite_directory_creates_parent_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "autoclaw.db"

    assert not db_path.parent.exists()

    cli._ensure_sqlite_directory(f"sqlite+aiosqlite:////{db_path}")

    assert db_path.parent.exists()


def test_ensure_sqlite_directory_noop_for_non_sqlite_url() -> None:
    cli._ensure_sqlite_directory("postgresql://user:pass@localhost/db")


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
