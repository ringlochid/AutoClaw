from __future__ import annotations

import argparse
import json
import sqlite3
import tomllib
from pathlib import Path
from typing import Any

import autoclaw.interfaces.cli as cli
import pytest
from anyio import Path as AnyioPath
from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import build_openclaw_gateway_adapter
from autoclaw.paths import default_database_path
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.public_surfaces.root_cli.support import (
    available_loopback_port,
    build_fake_openclaw_host,
    load_openclaw_agents_by_id,
    write_stale_flows_schema,
)


async def _assert_onboard_runtime_config(
    payload: dict[str, Any],
    *,
    config_path: Path,
    gateway_server: LocalGatewayTestServer,
    openclaw_bin: Path,
    openclaw_config: Path,
    api_port: int,
) -> None:
    assert payload["ok"] is True
    assert await AnyioPath(config_path).exists()
    assert payload["server"]["host"] == "127.0.0.1"
    assert payload["server"]["port"] == api_port
    assert isinstance(payload["server"]["ok"], bool)
    assert payload["openclaw"]["support_status"] == "supported"
    assert payload["openclaw"]["loopback"] is True
    assert payload["openclaw"]["effective_auth"] == "token"
    assert payload["worker_agent_id"] == "autoclaw-worker"
    assert payload["operator_agent_id"] == "autoclaw-operator"
    assert await AnyioPath(payload["wrapper_state_path"]).exists()
    assert await AnyioPath(payload["material_paths"]["profile"]).exists()
    assert await AnyioPath(payload["material_paths"]["operator_contract"]).exists()
    assert await AnyioPath(payload["material_paths"]["mcp_surfaces"]).exists()
    config_payload = tomllib.loads(await AnyioPath(config_path).read_text())
    assert config_payload["openclaw"]["base_url"] == gateway_server.base_url
    assert config_payload["openclaw"]["binary_path"] == str(openclaw_bin)
    assert config_payload["openclaw"]["config_path"] == str(openclaw_config)
    assert config_payload["openclaw"]["agent_id"] == "autoclaw-worker"
    assert config_payload["openclaw"]["operator_agent_id"] == "autoclaw-operator"
    assert config_payload["server"]["port"] == api_port
    assert config_payload["runtime"]["watchdog_enabled"] is True


def _assert_onboard_host_materials(openclaw_config: Path) -> None:
    agents_by_id = load_openclaw_agents_by_id(openclaw_config)
    worker_entry = agents_by_id["autoclaw-worker"]
    operator_entry = agents_by_id["autoclaw-operator"]
    assert worker_entry["name"] == "autoclaw-worker"
    assert worker_entry["workspace"].endswith("/.openclaw/workspaces/autoclaw-worker")
    assert worker_entry["agentDir"].endswith("/.openclaw/agents/autoclaw-worker/agent")
    assert worker_entry["reasoningDefault"] == "on"
    assert worker_entry["identity"] == {
        "name": "AutoClaw Worker",
        "theme": "quiet, exact, tool-first",
    }
    assert "thinkingDefault" not in worker_entry
    assert worker_entry["sandbox"]["mode"] == "off"
    assert worker_entry["tools"]["deny"] == ["autoclaw-operator__*"]
    assert worker_entry["tools"]["exec"]["host"] == "gateway"
    assert worker_entry["tools"]["exec"]["timeoutSec"] == 3600
    assert operator_entry["name"] == "autoclaw-operator"
    assert operator_entry["workspace"].endswith("/.openclaw/workspaces/autoclaw-operator")
    assert operator_entry["agentDir"].endswith("/.openclaw/agents/autoclaw-operator/agent")
    assert operator_entry["memorySearch"]["enabled"] is False
    assert operator_entry["sandbox"]["mode"] == "off"
    assert operator_entry["tools"]["deny"] == ["autoclaw-node__*"]
    assert operator_entry["tools"]["exec"]["host"] == "gateway"
    openclaw_payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
    assert openclaw_payload["mcp"]["servers"]["autoclaw-operator"]["url"].endswith("/operator/mcp")
    assert openclaw_payload["mcp"]["servers"]["autoclaw-node"]["url"].endswith("/node/mcp")
    assert "codex" not in openclaw_payload["mcp"]["servers"]["autoclaw-operator"]
    assert "codex" not in openclaw_payload["mcp"]["servers"]["autoclaw-node"]


@pytest.mark.asyncio
async def test_root_cli_onboard_writes_wrapper_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_port = 18123
    paths = build_fake_openclaw_host(tmp_path, monkeypatch)
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()

    try:
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(paths.config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=api_port,
                    log_level="INFO",
                    api_key="api-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=False,
                    non_interactive=True,
                    json=True,
                    plain=False,
                    no_color=False,
                    verbose=False,
                )
            )
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert result == 0
        assert "Running database upgrade" not in captured.err
        assert "Seeding packaged definitions" not in captured.err
        assert "Running openclaw agents list --json" not in captured.err
        await _assert_onboard_runtime_config(
            payload,
            config_path=paths.config_path,
            gateway_server=gateway_server,
            openclaw_bin=paths.openclaw_bin,
            openclaw_config=paths.openclaw_config,
            api_port=api_port,
        )
        _assert_onboard_host_materials(paths.openclaw_config)
    finally:
        gateway_server.close()
        await dispose_db_engine()


async def test_root_cli_onboard_repairs_stale_sqlite_schema(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_port = 18126
    paths = build_fake_openclaw_host(tmp_path, monkeypatch)
    config_path = paths.config_path
    data_dir = paths.data_dir
    database_path = default_database_path(data_dir)
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()

    try:
        await cli.cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=api_port,
                log_level="INFO",
                api_key="api-test-key",
                force=True,
                skip_db_upgrade=True,
                json=False,
            )
        )
        capsys.readouterr()
        await dispose_db_engine()
        write_stale_flows_schema(database_path)

        with gateway_server.configured_env():
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(data_dir),
                    database_url=None,
                    host="127.0.0.1",
                    port=api_port,
                    log_level="INFO",
                    api_key="api-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=True,
                    non_interactive=True,
                    json=True,
                    plain=False,
                    no_color=False,
                    verbose=False,
                )
            )
        payload = json.loads(capsys.readouterr().out)
    finally:
        gateway_server.close()
        await dispose_db_engine()

    assert result == 0
    assert payload["ok"] is True
    assert payload["database_repair"] is not None
    assert payload["database_repair"]["repaired"] is True
    backup_path = AnyioPath(payload["database_repair"]["backup_path"])
    assert await backup_path.exists()
    assert "flows" in payload["database_repair"]["skipped_tables"]
    with sqlite3.connect(database_path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert "tasks" in tables
    assert "flow_revisions" in tables


async def test_root_cli_onboard_persists_openclaw_runtime_inputs_for_env_free_compatibility(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_port = 18127
    paths = build_fake_openclaw_host(
        tmp_path,
        monkeypatch,
        gateway_auth={"token": "gateway-live-token"},
    )
    config_path = paths.config_path
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", gateway_server.base_url)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", raising=False)

    try:
        result = await cli.cmd_onboard(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(tmp_path / "autoclaw-data"),
                database_url=None,
                host="127.0.0.1",
                port=api_port,
                log_level="INFO",
                api_key="api-test-key",
                force=False,
                skip_db_upgrade=False,
                install_daemon=False,
                skip_daemon=True,
                no_start=True,
                non_interactive=True,
                json=True,
                plain=False,
                no_color=False,
                verbose=False,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["ok"] is True

        monkeypatch.delenv("AUTOCLAW_OPENCLAW__BINARY_PATH", raising=False)
        monkeypatch.delenv("OPENCLAW_CONFIG_PATH", raising=False)
        monkeypatch.delenv("AUTOCLAW_OPENCLAW__BASE_URL", raising=False)
        get_settings.cache_clear()
        with cli.command_env(config_path=config_path):
            settings = get_settings()
            adapter = build_openclaw_gateway_adapter(settings)
            compatibility = await adapter.check_compatibility()
        assert compatibility.role == "operator"
        config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        assert config_payload["openclaw"]["base_url"] == gateway_server.base_url
        assert config_payload["openclaw"]["binary_path"] == str(paths.openclaw_bin)
        assert config_payload["openclaw"]["config_path"] == str(paths.openclaw_config)
    finally:
        get_settings.cache_clear()
        gateway_server.close()
        await dispose_db_engine()


async def test_root_cli_onboard_human_progress_reports_major_steps(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_port = available_loopback_port()
    paths = build_fake_openclaw_host(tmp_path, monkeypatch)
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()

    try:
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(paths.config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=api_port,
                    log_level="INFO",
                    api_key="api-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=True,
                    non_interactive=True,
                    json=False,
                    plain=True,
                    no_color=False,
                    verbose=False,
                )
            )
        captured = capsys.readouterr()
    finally:
        gateway_server.close()
        await dispose_db_engine()

    assert result == 0
    assert "AutoClaw onboard" in captured.out
    assert "Checking OpenClaw support" in captured.err
    assert "Writing local config" in captured.err
    assert "Checking local API bind target" in captured.err
    assert "Running database upgrade" in captured.err
    assert "Seeding packaged definitions" in captured.err
    assert "Reconciling OpenClaw integration" in captured.err
    assert "Running openclaw agents list --json" in captured.err
    assert "Running openclaw mcp set autoclaw-node" in captured.err
