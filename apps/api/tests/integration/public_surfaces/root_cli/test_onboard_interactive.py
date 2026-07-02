from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import DEFAULT_API_PORT
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.public_surfaces.root_cli.support import (
    available_loopback_port,
    build_fake_openclaw_host,
    install_interactive_stdio,
)


@pytest.mark.asyncio
async def test_root_cli_onboard_interactive_defaults_to_bootstrap_dedicated_agents(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_fake_openclaw_host(
        tmp_path,
        monkeypatch,
        agents=[
            {
                "id": "main",
                "default": True,
                "name": "Main agent",
                "workspace": "/tmp/openclaw-main",
                "agentDir": "/tmp/openclaw-main-agent",
            }
        ],
    )
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    selected_api_port = available_loopback_port()
    gateway_base_url = gateway_server.base_url
    prompt_log: list[str] = []
    answers = iter(["", "", "", "", ""])  # continue, api port, gateway port, worker, operator
    install_interactive_stdio(monkeypatch, answers=answers, prompt_log=prompt_log)

    try:
        with gateway_server.configured_env():
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(paths.config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=selected_api_port,
                    log_level="INFO",
                    api_key="api-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=True,
                    non_interactive=False,
                    json=False,
                    plain=True,
                    no_color=False,
                )
            )
            capsys.readouterr()
            config_payload = tomllib.loads(paths.config_path.read_text(encoding="utf-8"))
            check_result = await cli.cmd_openclaw_check(
                argparse.Namespace(
                    config=str(paths.config_path),
                    json=True,
                    plain=False,
                    no_color=False,
                )
            )
        payload = json.loads(capsys.readouterr().out)
    finally:
        gateway_server.close()
        await dispose_db_engine()

    assert result == 0
    assert check_result == 0
    assert payload["worker_agent_id"] == "autoclaw-worker"
    assert payload["operator_agent_id"] == "autoclaw-operator"
    assert payload["base_url"] == gateway_base_url
    assert config_payload["server"]["port"] == selected_api_port
    assert config_payload["openclaw"]["base_url"] == gateway_base_url
    host_payload = json.loads(paths.openclaw_config.read_text(encoding="utf-8"))
    host_agent_ids = [entry["id"] for entry in host_payload["agents"]["list"]]
    assert host_agent_ids == ["main", "autoclaw-worker", "autoclaw-operator"]
    assert prompt_log.count("Select [default 2]: ") == 2


async def test_root_cli_onboard_interactive_guided_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_fake_openclaw_host(tmp_path, monkeypatch)
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    selected_api_port = available_loopback_port()
    prompt_log: list[str] = []
    answers = iter(
        ["", str(selected_api_port), "18800", "", ""]
    )  # continue, api port, gateway port, worker, operator
    install_interactive_stdio(monkeypatch, answers=answers, prompt_log=prompt_log)

    try:
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(paths.config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=None,
                    log_level="INFO",
                    api_key="api-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=True,
                    non_interactive=False,
                    json=False,
                    plain=True,
                    no_color=False,
                )
            )
        output = capsys.readouterr().out
    finally:
        gateway_server.close()
        await dispose_db_engine()

    assert result == 0
    assert "AutoClaw onboard" in output
    assert paths.config_path.exists()
    config_payload = tomllib.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config_payload["server"]["port"] == selected_api_port
    assert config_payload["openclaw"]["base_url"] == "http://127.0.0.1:18800"
    assert "Selected ports" in output
    assert f"127.0.0.1:{selected_api_port}" in output
    assert "127.0.0.1:18800" in output
    assert prompt_log.count("Select [default 2]: ") == 1
    assert prompt_log.count("Select [default 1]: ") == 1


async def test_root_cli_onboard_interactive_existing_worker_bootstrap_operator(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_fake_openclaw_host(
        tmp_path,
        monkeypatch,
        agents=[
            {
                "id": "orin",
                "default": True,
                "name": "Orin",
                "workspace": "/tmp/orin-space",
                "agentDir": "/tmp/orin-agent",
            },
            {
                "id": "hikari",
                "name": "Hikari",
                "workspace": "/tmp/hikari-space",
                "agentDir": "/tmp/hikari-agent",
            },
            {
                "id": "homura",
                "name": "Homura",
                "workspace": "/tmp/homura-space",
                "agentDir": "/tmp/homura-agent",
            },
        ],
    )
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    selected_api_port = available_loopback_port()
    prompt_log: list[str] = []
    answers = iter(["", "", "", "1", "4"])
    install_interactive_stdio(monkeypatch, answers=answers, prompt_log=prompt_log)

    try:
        with gateway_server.configured_env():
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(paths.config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=selected_api_port,
                    log_level="INFO",
                    api_key="api-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=True,
                    non_interactive=False,
                    json=False,
                    plain=True,
                    no_color=False,
                )
            )
        capsys.readouterr()
    finally:
        gateway_server.close()
        await dispose_db_engine()

    assert result == 0
    config_payload = tomllib.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config_payload["openclaw"]["agent_id"] == "orin"
    assert config_payload["openclaw"]["operator_agent_id"] == "autoclaw-operator"
    host_payload = json.loads(paths.openclaw_config.read_text(encoding="utf-8"))
    host_agent_ids = [entry["id"] for entry in host_payload["agents"]["list"]]
    assert host_agent_ids == ["orin", "hikari", "homura", "autoclaw-operator"]
    assert prompt_log.count("Select [default 4]: ") == 2


async def test_root_cli_onboard_interactive_requires_tty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"

    result = await cli.cmd_onboard(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(tmp_path / "autoclaw-data"),
            database_url=None,
            host="127.0.0.1",
            port=DEFAULT_API_PORT,
            log_level="INFO",
            api_key="api-test-key",
            force=False,
            skip_db_upgrade=False,
            install_daemon=False,
            skip_daemon=True,
            no_start=False,
            non_interactive=False,
            json=False,
            plain=True,
            no_color=False,
        )
    )
    output = capsys.readouterr().out
    assert result == 2
    assert "interactive prompting requires a TTY" in output
