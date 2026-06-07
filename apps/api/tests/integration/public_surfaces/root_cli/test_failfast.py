from __future__ import annotations

import argparse
import json
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import DEFAULT_API_PORT
from autoclaw.paths import default_database_path
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.public_surfaces.root_cli.support import (
    build_init_args,
    write_fake_openclaw_config,
)


@pytest.mark.asyncio
async def test_root_cli_onboard_fails_before_db_when_openclaw_binary_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        with gateway_server.configured_env():
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(data_dir),
                    database_url=None,
                    host="127.0.0.1",
                    port=DEFAULT_API_PORT,
                    log_level="INFO",
                    api_key="test-api-key",
                    internal_api_key="internal-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
                    no_start=False,
                    non_interactive=True,
                    json=True,
                    plain=False,
                    no_color=False,
                )
            )
        payload = json.loads(capsys.readouterr().out)
        assert result == 1
        assert payload["ok"] is False
        assert payload["created_local_config"] is False
        assert payload["openclaw"]["support_status"] == "blocked"
        assert payload["openclaw"]["reason"] == "OPENCLAW_BINARY_NOT_FOUND"
        assert payload["openclaw"]["config_exists"] is True
        assert config_path.exists() is False
        assert not default_database_path(data_dir).exists()
    finally:
        gateway_server.close()
        await dispose_db_engine()


async def test_root_cli_configure_all_fails_before_local_runtime_when_openclaw_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli.cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=DEFAULT_API_PORT,
                log_level="INFO",
                api_key="test-api-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=True,
                json=False,
            )
        )
        capsys.readouterr()

        def _unexpected_service_install(_args: argparse.Namespace) -> int:
            raise AssertionError(
                "service install should not run when OpenClaw preflight is blocked"
            )

        monkeypatch.setattr(
            "autoclaw.interfaces.cli.commands.onboard.cmd_service_install",
            _unexpected_service_install,
        )
        with gateway_server.configured_env():
            result = await cli.cmd_configure(
                argparse.Namespace(
                    config=str(config_path),
                    section="all",
                    force=False,
                    no_start=True,
                    non_interactive=True,
                    json=True,
                    plain=False,
                    no_color=False,
                )
            )
        payload = json.loads(capsys.readouterr().out)
        assert result == 1
        assert payload["ok"] is False
        assert payload["section"] == "all"
        assert payload["actions"] == []
        assert payload["openclaw"]["support_status"] == "blocked"
        assert payload["openclaw"]["reason"] == "OPENCLAW_BINARY_NOT_FOUND"
        assert not default_database_path(data_dir).exists()
    finally:
        gateway_server.close()
        await dispose_db_engine()


async def test_configure_service_fails_before_service_install_when_openclaw_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()

        def _unexpected_service_install(_args: argparse.Namespace) -> int:
            raise AssertionError(
                "service install should not run when OpenClaw preflight is blocked"
            )

        monkeypatch.setattr(
            "autoclaw.interfaces.cli.commands.onboard.cmd_service_install",
            _unexpected_service_install,
        )
        with gateway_server.configured_env():
            result = await cli.cmd_configure(
                argparse.Namespace(
                    config=str(config_path),
                    section="service",
                    force=False,
                    no_start=True,
                    non_interactive=True,
                    json=True,
                    plain=False,
                    no_color=False,
                )
            )
        payload = json.loads(capsys.readouterr().out)
        assert result == 1
        assert payload["ok"] is False
        assert payload["section"] == "service"
        assert payload["actions"] == []
        assert payload["openclaw"]["support_status"] == "blocked"
        assert payload["openclaw"]["reason"] == "OPENCLAW_BINARY_NOT_FOUND"
    finally:
        gateway_server.close()
        await dispose_db_engine()


async def test_root_cli_service_install_fails_before_unit_write_when_openclaw_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    unit_dir = tmp_path / "systemd-user"
    env_file = tmp_path / "autoclaw.env"
    openclaw_config = tmp_path / "openclaw.json"
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = cli.cmd_service_install(
            argparse.Namespace(
                config=str(config_path),
                data_dir=None,
                env_file=str(env_file),
                name="autoclaw",
                unit_dir=str(unit_dir),
                force=True,
                no_start=True,
            )
        )
        output = capsys.readouterr().out
        assert result == 1
        assert "OpenClaw preflight failed" in output
        assert not unit_dir.joinpath("autoclaw.service").exists()
        assert not env_file.exists()
    finally:
        await dispose_db_engine()


async def test_root_cli_doctor_fix_fails_fast_when_preflight_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
        capsys.readouterr()
        with gateway_server.configured_env():
            result = await cli.cmd_doctor(
                argparse.Namespace(
                    config=str(config_path),
                    fix=True,
                    json=True,
                    plain=False,
                    no_color=False,
                )
            )
        payload = json.loads(capsys.readouterr().out)
        assert result == 1
        assert payload["ok"] is False
        assert payload["openclaw"]["support_status"] == "blocked"
        assert payload["openclaw"]["reason"] == "OPENCLAW_BINARY_NOT_FOUND"
    finally:
        gateway_server.close()
        await dispose_db_engine()
