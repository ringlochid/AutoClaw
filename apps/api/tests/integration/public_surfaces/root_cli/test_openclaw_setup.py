from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.public_surfaces.root_cli.support import (
    build_fake_openclaw_host,
    build_init_args,
    load_openclaw_agents_by_id,
    write_fake_openclaw_config,
)


def _assert_selected_profile_setup(openclaw_config: Path) -> None:
    agents_by_id = load_openclaw_agents_by_id(openclaw_config)
    worker_entry = agents_by_id["leo-worker"]
    operator_entry = agents_by_id["leo-operator"]
    assert worker_entry["name"] == "Leo Worker"
    assert worker_entry["workspace"] == "/tmp/leo-worker-space"
    assert worker_entry["agentDir"] == "/tmp/leo-worker-agent"
    assert worker_entry["sandbox"]["mode"] == "workspace"
    assert worker_entry["identity"] == {"name": "Keep worker"}
    assert worker_entry["tools"]["allow"] == ["notes__search"]
    assert worker_entry["tools"]["profile"] == "full"
    assert worker_entry["tools"]["deny"] == [
        "autoclaw-operator__*",
        "group:sessions",
        "group:messaging",
        "group:ui",
        "group:nodes",
        "group:automation",
        "group:agents",
    ]
    assert worker_entry["tools"]["exec"]["host"] == "gateway"
    assert worker_entry["tools"]["exec"]["timeoutSec"] == 3600
    assert operator_entry["name"] == "Leo Operator"
    assert operator_entry["workspace"] == "/tmp/leo-operator-space"
    assert operator_entry["agentDir"] == "/tmp/leo-operator-agent"
    assert operator_entry["sandbox"]["mode"] == "workspace"
    assert operator_entry["memorySearch"]["enabled"] is True
    assert operator_entry["tools"]["allow"] == ["memory__search"]
    assert operator_entry["tools"]["profile"] == "full"
    assert operator_entry["tools"]["deny"] == ["autoclaw-node__*"]
    assert operator_entry["tools"]["exec"]["host"] == "gateway"
    assert operator_entry["tools"]["exec"]["timeoutSec"] == 3600


@pytest.mark.asyncio
async def test_root_cli_openclaw_setup_patches_selected_profiles_tool_slice_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_fake_openclaw_host(
        tmp_path,
        monkeypatch,
        agents=[
            {
                "id": "leo-worker",
                "default": True,
                "name": "Leo Worker",
                "workspace": "/tmp/leo-worker-space",
                "agentDir": "/tmp/leo-worker-agent",
                "sandbox": {"mode": "workspace"},
                "identity": {"name": "Keep worker"},
                "tools": {
                    "profile": "personal",
                    "allow": ["notes__search"],
                    "exec": {
                        "host": "local",
                        "security": "workspace",
                        "ask": "on",
                        "backgroundMs": 1000,
                        "timeoutSec": 10,
                    },
                },
            },
            {
                "id": "leo-operator",
                "name": "Leo Operator",
                "workspace": "/tmp/leo-operator-space",
                "agentDir": "/tmp/leo-operator-agent",
                "sandbox": {"mode": "workspace"},
                "memorySearch": {"enabled": True},
                "tools": {
                    "profile": "personal",
                    "allow": ["memory__search"],
                },
            },
        ],
    )
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", gateway_server.base_url)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-config-token")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__AGENT_ID", "leo-worker")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__OPERATOR_AGENT_ID", "leo-operator")

    try:
        await cli.cmd_init(build_init_args(paths))
        capsys.readouterr()
        result = await cli.cmd_openclaw_setup(
            argparse.Namespace(
                config=str(paths.config_path),
                non_interactive=True,
                json=True,
                plain=False,
                no_color=False,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["worker_agent_id"] == "leo-worker"
        assert payload["operator_agent_id"] == "leo-operator"
        _assert_selected_profile_setup(paths.openclaw_config)
    finally:
        gateway_server.close()
        await dispose_db_engine()


async def test_root_cli_openclaw_check_blocks_ambiguous_auth(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    local_openclaw_config = tmp_path / "openclaw.json"
    write_fake_openclaw_config(
        local_openclaw_config,
        gateway_auth={
            "token": "gateway-token",
            "password": "gateway-password",
        },
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", sys.executable)

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = await cli.cmd_openclaw_check(
            argparse.Namespace(
                config=str(config_path),
                json=True,
                plain=False,
                no_color=False,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        assert result == 1
        assert payload["ok"] is False
        assert payload["reason"] == "AMBIGUOUS_GATEWAY_AUTH_MODE"
    finally:
        await dispose_db_engine()


async def test_root_cli_openclaw_setup_bootstraps_gateway_token_and_port(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_fake_openclaw_host(
        tmp_path,
        monkeypatch,
        gateway_port=19055,
    )
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()

    try:
        await cli.cmd_init(build_init_args(paths))
        capsys.readouterr()
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        answers = iter(["19055", "gateway-config-token"])
        monkeypatch.setattr(
            "autoclaw.interfaces.cli.commands.openclaw.gateway_bootstrap.text",
            lambda *args, **kwargs: next(answers),
        )
        monkeypatch.setattr("builtins.input", lambda _prompt="": "")
        result = await cli.cmd_openclaw_setup(
            argparse.Namespace(
                config=str(paths.config_path),
                non_interactive=False,
                openclaw_gateway_token=None,
                openclaw_gateway_port=None,
                json=True,
                plain=False,
                no_color=False,
            )
        )
        output = capsys.readouterr().out
        json_start = output.find("{")
        payload = json.loads(output[json_start:])
    finally:
        gateway_server.close()
        await dispose_db_engine()

    assert result == 0
    assert payload["ok"] is True
    config_payload = tomllib.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config_payload["openclaw"]["gateway_token"] == "gateway-config-token"
    assert config_payload["openclaw"]["base_url"] == "http://127.0.0.1:19055"
    host_payload = json.loads(paths.openclaw_config.read_text(encoding="utf-8"))
    assert host_payload["gateway"]["port"] == 19055
    assert host_payload["gateway"]["auth"]["mode"] == "token"
    assert host_payload["gateway"]["auth"]["token"] == "gateway-config-token"
