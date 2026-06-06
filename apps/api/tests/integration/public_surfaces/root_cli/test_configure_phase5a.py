from __future__ import annotations

import argparse
import json
import sqlite3
import tomllib
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import DEFAULT_API_PORT
from autoclaw.interfaces.cli.commands.bootstrap import update_config_sections
from autoclaw.paths import default_database_path
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_cli import write_fake_openclaw_cli
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.public_surfaces.root_cli.support import (
    build_init_args,
    write_fake_openclaw_config,
)


@pytest.mark.asyncio
async def test_phase5a_root_cli_configure_interactive_guided_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    answers = iter(["1", "", ""])  # section, worker default, operator default
    write_fake_openclaw_cli(openclaw_bin)
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_configure(
                argparse.Namespace(
                    config=str(config_path),
                    section="all",
                    force=False,
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
    assert "AutoClaw configure" in output
    assert "openclaw_dual_surface" in output
async def test_phase5a_root_cli_configure_service_persists_requested_port(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_port = 19123
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_fake_openclaw_cli(openclaw_bin)
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    install_calls: list[object] = []
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.commands.service.SERVICE_MANAGER.install",
        lambda request: install_calls.append(request),
    )

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()
        with gateway_server.configured_env():
            result = await cli.cmd_configure(
                argparse.Namespace(
                    config=str(config_path),
                    section="service",
                    port=api_port,
                    force=False,
                    no_start=True,
                    non_interactive=True,
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
    assert payload == {"ok": True, "section": "service", "actions": ["service_manager"]}
    assert len(install_calls) == 1
    config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config_payload["server"]["port"] == api_port
    openclaw_payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
    assert openclaw_payload["mcp"]["servers"]["autoclaw-operator"]["url"] == (
        f"http://127.0.0.1:{api_port}/operator/mcp"
    )
    assert openclaw_payload["mcp"]["servers"]["autoclaw-node"]["url"] == (
        f"http://127.0.0.1:{api_port}/node/mcp"
    )
async def test_phase5a_root_cli_onboard_install_daemon_reconciles_requested_port_everywhere(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_port = 18124
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_fake_openclaw_cli(openclaw_bin)
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    install_calls: list[object] = []
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.commands.service.SERVICE_MANAGER.install",
        lambda request: install_calls.append(request),
    )

    try:
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(data_dir),
                    database_url=None,
                    host="127.0.0.1",
                    port=api_port,
                    log_level="INFO",
                    api_key="api-test-key",
                    internal_api_key="internal-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=True,
                    skip_daemon=False,
                    no_start=True,
                    non_interactive=True,
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
    assert payload["ok"] is True
    assert payload["daemon_installed"] is True
    assert payload["server"]["port"] == api_port
    assert len(install_calls) == 1
    config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config_payload["server"]["port"] == api_port
    host_payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
    assert host_payload["mcp"]["servers"]["autoclaw-operator"]["url"] == (
        f"http://127.0.0.1:{api_port}/operator/mcp"
    )
    assert host_payload["mcp"]["servers"]["autoclaw-node"]["url"] == (
        f"http://127.0.0.1:{api_port}/node/mcp"
    )
async def test_phase5a_root_cli_configure_definitions_reseeds_packaged_registry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = default_database_path(data_dir)

    try:
        await cli.cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=DEFAULT_API_PORT,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=True,
                json=False,
            )
        )
        capsys.readouterr()
        result = await cli.cmd_configure(
            argparse.Namespace(
                config=str(config_path),
                section="definitions",
                force=False,
                no_start=True,
                non_interactive=True,
                json=True,
                plain=False,
                no_color=False,
            )
        )
        payload = json.loads(capsys.readouterr().out)
    finally:
        await dispose_db_engine()

    assert result == 0
    assert payload["ok"] is True
    assert payload["actions"] == ["definitions_registry"]
    assert database_path.exists()
    with sqlite3.connect(database_path) as connection:
        counts = {
            "roles": connection.execute("SELECT COUNT(*) FROM role_definitions").fetchone()[0],
            "policies": connection.execute("SELECT COUNT(*) FROM policy_definitions").fetchone()[0],
            "workflows": connection.execute("SELECT COUNT(*) FROM workflow_definitions").fetchone()[
                0
            ],
        }
    assert all(count > 0 for count in counts.values())
async def test_phase5a_root_cli_configure_web_refreshes_console_origins(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()
        update_config_sections(
            config_path,
            section_updates={"server": {"console_origins": ["http://127.0.0.1:9999"]}},
        )
        result = await cli.cmd_configure(
            argparse.Namespace(
                config=str(config_path),
                section="web",
                force=False,
                no_start=True,
                non_interactive=True,
                json=True,
                plain=False,
                no_color=False,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    finally:
        await dispose_db_engine()

    assert result == 0
    assert payload["ok"] is True
    assert payload["actions"] == ["web_console"]
    assert config_payload["server"]["console_origins"] == [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]
