from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sqlite3
import sys
import tomllib
from importlib import resources
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock

import pytest
from autoclaw import cli
from autoclaw.cli.commands.bootstrap import ensure_database_ready_with_legacy_sqlite_repair
from autoclaw.config import DEFAULT_API_PORT, DEFAULT_LOG_LEVEL, OpenClawSettings, get_settings
from autoclaw.db.session import dispose_db_engine, get_async_engine
from autoclaw.runtime.openclaw.connection import ClientConnection, connect_and_handshake
from autoclaw.runtime.openclaw.contracts import OpenClawAuthError
from autoclaw.runtime.openclaw.fixtures import hello_ok_fixture
from autoclaw.runtime.openclaw.protocol import OpenClawHelloOkPayload
from autoclaw.runtime.openclaw.request_builders import build_openclaw_compatibility_report
from click import Group
from click.testing import CliRunner
from sqlalchemy import inspect, text

SEED_KIND_TO_TABLE = {
    "roles": "role_definitions",
    "policies": "policy_definitions",
    "workflows": "workflow_definitions",
}


def _build_init_args(config_path: Path, data_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        host="127.0.0.1",
        port=DEFAULT_API_PORT,
        log_level=DEFAULT_LOG_LEVEL,
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        force=True,
        skip_db_upgrade=False,
        json=True,
    )


def _available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.bind(("127.0.0.1", 0))
        return int(probe_socket.getsockname()[1])


def _packaged_seed_counts() -> dict[str, int]:
    definitions_root = resources.files("autoclaw.registry.seed_definitions")
    with resources.as_file(definitions_root) as seed_root:
        return {
            kind: len(list(seed_root.joinpath(kind).glob("*.yaml"))) for kind in SEED_KIND_TO_TABLE
        }


def _seeded_registry_counts(database_path: Path) -> tuple[set[str], dict[str, int]]:
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        counts = {
            kind: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for kind, table in SEED_KIND_TO_TABLE.items()
        }
    return table_names, counts


@pytest.mark.asyncio
async def test_init_writes_canonical_config_and_db_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    try:
        result = await cli.cmd_init(_build_init_args(config_path, data_dir))
    finally:
        await dispose_db_engine()

    assert result == 0
    assert config_path.exists()
    assert data_dir.joinpath("autoclaw.db").exists()

    config_text = config_path.read_text(encoding="utf-8")
    config_payload = tomllib.loads(config_text)
    assert f'level = "{DEFAULT_LOG_LEVEL}"' in config_text
    assert 'api_key = "api-test-key"' in config_text
    assert 'internal_api_key = "internal-test-key"' in config_text
    assert "definitions_root" not in config_text
    assert "[app]" not in config_text
    assert config_payload["database"]["echo"] is False
    assert config_payload["openclaw"]["base_url"] == "http://127.0.0.1:18789"
    assert config_payload["openclaw"]["agent_id"] == "autoclaw-worker"
    assert config_payload["openclaw"]["operator_agent_id"] == "autoclaw-operator"
    assert config_payload["openclaw"]["timeout_ms"] == 120000
    assert config_payload["runtime"]["watchdog_enabled"] is True

    database_path = data_dir / "autoclaw.db"
    expected_seed_counts = _packaged_seed_counts()
    table_names, seeded_counts = _seeded_registry_counts(database_path)
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert seeded_counts == expected_seed_counts

    payload = capsys.readouterr().out
    assert '"ok": true' in payload


@pytest.mark.asyncio
async def test_init_keeps_sql_echo_quiet_when_legacy_debug_env_is_set(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    monkeypatch.setenv("AUTOCLAW_DEBUG", "true")

    try:
        result = await cli.cmd_init(_build_init_args(config_path, data_dir))
    finally:
        await dispose_db_engine()

    assert result == 0
    output = capsys.readouterr().out
    assert "sqlalchemy.engine.Engine" not in output


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


def test_packaged_seed_definitions_are_available() -> None:
    definitions_root = resources.files("autoclaw.registry.seed_definitions")

    assert definitions_root.joinpath("roles").joinpath("planning_lead.yaml").is_file()
    assert definitions_root.joinpath("policies").joinpath("standard_worker.yaml").is_file()
    assert (
        definitions_root.joinpath("workflows")
        .joinpath("normal_parent_first_release.yaml")
        .is_file()
    )


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
    openclaw_config.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    run_called = False

    def _unexpected_run(*args: object, **kwargs: object) -> None:
        nonlocal run_called
        run_called = True

    monkeypatch.setattr("uvicorn.run", _unexpected_run)

    try:
        asyncio.run(cli.cmd_init(_build_init_args(config_path, data_dir)))
        capsys.readouterr()
        result = cli.cmd_serve(argparse.Namespace(config=str(config_path)))
    finally:
        asyncio.run(dispose_db_engine())

    assert result == 1
    assert run_called is False
    assert "OpenClaw preflight failed" in capsys.readouterr().out


def test_service_install_and_status_use_systemd_user_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api_port = 19123
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    unit_dir = tmp_path / "systemd-user"
    env_file = tmp_path / "autoclaw.env"
    systemctl_log = tmp_path / "systemctl.log"
    systemctl_bin = tmp_path / "systemctl"
    systemctl_bin.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from pathlib import Path",
                "import sys",
                f"log_path = Path({str(systemctl_log)!r})",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "args = sys.argv[1:]",
                "if args and args[0] == '--user':",
                "    args = args[1:]",
                "if args and args[0] == 'show':",
                (
                    "    sys.stdout.write("
                    "'LoadState=loaded\\nUnitFileState=enabled\\nActiveState=active\\n'"
                    "'SubState=running\\nFragmentPath=/tmp/autoclaw.service\\n')"
                ),
                "sys.exit(0)",
            ]
        ),
        encoding="utf-8",
    )
    systemctl_bin.chmod(0o755)
    openclaw_config = tmp_path / "openclaw.json"
    openclaw_bin = tmp_path / "openclaw"
    from tests.integration.phase5a.test_root_cli_phase5a import write_fake_openclaw_cli

    write_fake_openclaw_cli(openclaw_bin)
    openclaw_config.write_text(
        json.dumps({"gateway": {"auth": {"token": "gateway-token"}}}, indent=2),
        encoding="utf-8",
    )
    monkeypatch.setenv("AUTOCLAW_SYSTEMCTL_BIN", str(systemctl_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", "http://127.0.0.1:18789")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-token")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))

    try:
        asyncio.run(cli.cmd_init(_build_init_args(config_path, data_dir)))
        capsys.readouterr()
        install_result = cli.cmd_service_install(
            argparse.Namespace(
                config=str(config_path),
                data_dir=None,
                env_file=str(env_file),
                name="autoclaw",
                unit_dir=str(unit_dir),
                port=api_port,
                force=True,
                no_start=True,
            )
        )
        status_result = cli.cmd_service_status(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=True,
            )
        )
    finally:
        get_settings.cache_clear()

    assert install_result == 0
    assert status_result == 0
    assert unit_dir.joinpath("autoclaw.service").exists()
    assert env_file.exists()
    config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config_payload["server"]["port"] == api_port
    payload = json.loads(capsys.readouterr().out)
    assert payload["manager"] == "systemd-user"
    assert payload["installed"] is True
    assert payload["running"] is True
    log_lines = systemctl_log.read_text(encoding="utf-8").splitlines()
    assert "daemon-reload" in log_lines[0]
    assert any("enable autoclaw.service" in line for line in log_lines)


def test_service_install_fails_before_unit_write_when_requested_port_is_busy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    unit_dir = tmp_path / "systemd-user"
    env_file = tmp_path / "autoclaw.env"
    openclaw_config = tmp_path / "openclaw.json"
    openclaw_config.write_text(
        json.dumps({"gateway": {"auth": {"token": "gateway-token"}}}, indent=2),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", "http://127.0.0.1:18789")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-token")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", sys.executable)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_socket:
        busy_socket.bind(("127.0.0.1", 0))
        busy_socket.listen(1)
        busy_port = busy_socket.getsockname()[1]

        try:
            asyncio.run(cli.cmd_init(_build_init_args(config_path, data_dir)))
            capsys.readouterr()
            result = cli.cmd_service_install(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=None,
                    env_file=str(env_file),
                    name="autoclaw",
                    unit_dir=str(unit_dir),
                    port=busy_port,
                    force=True,
                    no_start=True,
                )
            )
        finally:
            get_settings.cache_clear()
            asyncio.run(dispose_db_engine())

    output = capsys.readouterr().out
    config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert result == 1
    assert "Local API bind check failed" in output
    assert config_payload["server"]["port"] == DEFAULT_API_PORT
    assert not unit_dir.joinpath("autoclaw.service").exists()
    assert not env_file.exists()


def test_service_install_reconciles_existing_unit_without_overwriting_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    unit_dir = tmp_path / "systemd-user"
    env_file = tmp_path / "autoclaw.env"
    unit_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text("CUSTOM_FLAG=1\n", encoding="utf-8")
    unit_dir.joinpath("autoclaw.service").write_text("stale unit\n", encoding="utf-8")
    systemctl_log = tmp_path / "systemctl-reconcile.log"
    systemctl_bin = tmp_path / "systemctl-reconcile"
    systemctl_bin.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from pathlib import Path",
                "import sys",
                f"log_path = Path({str(systemctl_log)!r})",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "args = sys.argv[1:]",
                "if args and args[0] == '--user':",
                "    args = args[1:]",
                "if args and args[0] == 'show':",
                (
                    "    sys.stdout.write("
                    "'LoadState=loaded\\nUnitFileState=enabled\\nActiveState=inactive\\n'"
                    "'SubState=dead\\nFragmentPath=/tmp/autoclaw.service\\n')"
                ),
                "sys.exit(0)",
            ]
        ),
        encoding="utf-8",
    )
    systemctl_bin.chmod(0o755)
    openclaw_config = tmp_path / "openclaw.json"
    openclaw_config.write_text(
        json.dumps({"gateway": {"auth": {"token": "gateway-token"}}}, indent=2),
        encoding="utf-8",
    )
    monkeypatch.setenv("AUTOCLAW_SYSTEMCTL_BIN", str(systemctl_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", "http://127.0.0.1:18789")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-token")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", sys.executable)

    try:
        init_args = _build_init_args(config_path, data_dir)
        init_args.port = _available_loopback_port()
        asyncio.run(cli.cmd_init(init_args))
        result = cli.cmd_service_install(
            argparse.Namespace(
                config=str(config_path),
                data_dir=None,
                env_file=str(env_file),
                name="autoclaw",
                unit_dir=str(unit_dir),
                port=None,
                force=False,
                no_start=True,
            )
        )
    finally:
        get_settings.cache_clear()
        asyncio.run(dispose_db_engine())

    assert result == 0
    assert env_file.read_text(encoding="utf-8") == "CUSTOM_FLAG=1\n"
    assert "ExecStart=" in unit_dir.joinpath("autoclaw.service").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_db_reset_recreates_sqlite_database(tmp_path: Path) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.db"

    try:
        await cli.cmd_init(_build_init_args(config_path, data_dir))
        database_path.write_bytes(b"stale")
        result = await cli.cmd_db_reset(
            argparse.Namespace(
                config=str(config_path),
                revision="head",
                json=False,
            )
        )
    finally:
        await dispose_db_engine()

    assert result == 0
    assert database_path.exists()
    expected_seed_counts = _packaged_seed_counts()
    table_names, seeded_counts = _seeded_registry_counts(database_path)
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert seeded_counts == expected_seed_counts


@pytest.mark.asyncio
async def test_db_upgrade_rejects_stale_sqlite_schema_that_cannot_be_retrofitted(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.db"
    init_args = _build_init_args(config_path, data_dir)
    init_args.skip_db_upgrade = True

    try:
        await cli.cmd_init(init_args)
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE flows (
                    flow_id TEXT PRIMARY KEY,
                    task_id TEXT UNIQUE,
                    compiled_plan_id TEXT,
                    status TEXT,
                    active_flow_revision_id TEXT,
                    current_open_dispatch_id TEXT,
                    current_node_key TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.commit()

        with pytest.raises(RuntimeError, match="autoclaw db reset"):
            await asyncio.to_thread(
                cli.cmd_db_upgrade,
                argparse.Namespace(config=str(config_path)),
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.db"
    init_args = _build_init_args(config_path, data_dir)
    init_args.skip_db_upgrade = True

    try:
        init_result = await cli.cmd_init(init_args)
        upgrade_result = await asyncio.to_thread(
            cli.cmd_db_upgrade,
            argparse.Namespace(
                config=str(config_path),
                revision="head",
            ),
        )
    finally:
        await dispose_db_engine()

    assert init_result == 0
    assert upgrade_result == 0
    expected_seed_counts = _packaged_seed_counts()
    table_names, seeded_counts = _seeded_registry_counts(database_path)
    assert {
        "role_definitions",
        "role_revisions",
        "policy_definitions",
        "policy_revisions",
        "workflow_definitions",
        "workflow_revisions",
        "tasks",
    }.issubset(table_names)
    assert seeded_counts == expected_seed_counts


@pytest.mark.asyncio
async def test_legacy_postgres_schema_repair_moves_tables_to_backup_schema(
    tmp_path: Path,
) -> None:
    try:
        import asyncpg  # type: ignore[import-untyped]  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed")

    database_url = os.environ.get("AUTOCLAW_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("AUTOCLAW_TEST_POSTGRES_URL not set")

    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli.cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=database_url,
            host="127.0.0.1",
            port=DEFAULT_API_PORT,
            log_level=DEFAULT_LOG_LEVEL,
            api_key="test-api-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=True,
            json=False,
        )
    )

    with cli.command_env(config_path=config_path):
        get_settings.cache_clear()
        await dispose_db_engine()
        engine = get_async_engine()
        async with engine.begin() as connection:
            await connection.execute(text("DROP TABLE IF EXISTS flows CASCADE"))
            await connection.execute(
                text("CREATE TABLE flows (task_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
            )
        await dispose_db_engine()
        repair = await ensure_database_ready_with_legacy_sqlite_repair(database_url)
        assert repair is not None
        assert repair.is_repaired is True
        assert repair.backup_path.startswith("autoclaw_legacy")
        engine = get_async_engine()
        async with engine.begin() as connection:
            public_tables = set(
                await connection.run_sync(lambda conn: inspect(conn).get_table_names())
            )
            backup_tables = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=repair.backup_path)
                )
            )
        await dispose_db_engine()

    assert "flows" in public_tables
    assert "flow_revisions" in public_tables
    assert "flows" in backup_tables


@pytest.mark.asyncio
async def test_openclaw_loopback_connection_sends_origin_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _DummyConnection:
        async def close(self) -> None:
            return None

    async def _fake_connect(*args: object, **kwargs: object) -> ClientConnection:
        captured.update(kwargs)
        return cast(ClientConnection, _DummyConnection())

    monkeypatch.setattr("autoclaw.integrations.openclaw.gateway.connection.connect", _fake_connect)
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection.receive_connect_challenge",
        AsyncMock(return_value={"type": "connect_challenge", "challenge": "abc"}),
    )
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection.build_openclaw_connect_request",
        lambda **kwargs: type("Req", (), {"id": "connect-1"})(),
    )
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection.serialize_openclaw_gateway_request",
        lambda _req: "{}",
    )
    response = type(
        "Resp",
        (),
        {"ok": False, "error": type("Err", (), {"details": None, "message": "stop"})()},
    )()
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection._request_during_handshake",
        AsyncMock(return_value=response),
    )

    with pytest.raises(OpenClawAuthError):
        await connect_and_handshake(
            config=OpenClawSettings(base_url="http://127.0.0.1:18789"),
            auth_state_path=Path("/tmp/autoclaw-auth-state.json"),
            ws_url="ws://127.0.0.1:18789/ws",
            should_use_cached_device_token=False,
            auth_state=None,
        )

    assert captured["origin"] == "http://127.0.0.1:18789"


def test_build_openclaw_compatibility_report_tolerates_missing_hello_auth_scopes() -> None:
    response = hello_ok_fixture(scopes=[])
    hello_ok = OpenClawHelloOkPayload.model_validate(response["payload"])
    report = build_openclaw_compatibility_report(
        ws_url="ws://127.0.0.1:18789/ws",
        hello_ok=hello_ok,
        retry_used_cached_device_token=False,
    )
    assert report.role == "operator"
    assert report.scopes == ()


@pytest.mark.asyncio
async def test_service_start_and_status_use_managed_service_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    systemctl_log = tmp_path / "systemctl-start.log"
    systemctl_bin = tmp_path / "systemctl-start"
    systemctl_bin.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from pathlib import Path",
                "import sys",
                f"log_path = Path({str(systemctl_log)!r})",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "args = sys.argv[1:]",
                "if args and args[0] == '--user':",
                "    args = args[1:]",
                "if args and args[0] == 'show':",
                (
                    "    sys.stdout.write("
                    "'LoadState=loaded\\nUnitFileState=enabled\\nActiveState=active\\n'"
                    "'SubState=running\\nFragmentPath=/tmp/autoclaw.service\\n')"
                ),
                "sys.exit(0)",
            ]
        ),
        encoding="utf-8",
    )
    systemctl_bin.chmod(0o755)
    monkeypatch.setenv("AUTOCLAW_SYSTEMCTL_BIN", str(systemctl_bin))

    try:
        await cli.cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = cli.cmd_service_start(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=False,
            )
        )
        capsys.readouterr()
        status_result = cli.cmd_service_status(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=True,
            )
        )
    finally:
        get_settings.cache_clear()
        await dispose_db_engine()

    assert result == 0
    assert status_result == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["manager"] == "systemd-user"
    assert status_payload["installed"] is True
    assert status_payload["running"] is True
    log_lines = systemctl_log.read_text(encoding="utf-8").splitlines()
    assert any("start autoclaw.service" in line for line in log_lines)


@pytest.mark.asyncio
async def test_service_stop_and_restart_use_managed_service_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    systemctl_log = tmp_path / "systemctl-stop.log"
    systemctl_bin = tmp_path / "systemctl-stop"
    systemctl_bin.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from pathlib import Path",
                "import sys",
                f"log_path = Path({str(systemctl_log)!r})",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "args = sys.argv[1:]",
                "if args and args[0] == '--user':",
                "    args = args[1:]",
                "if args and args[0] == 'show':",
                (
                    "    sys.stdout.write("
                    "'LoadState=loaded\\nUnitFileState=enabled\\nActiveState=inactive\\n'"
                    "'SubState=dead\\nFragmentPath=/tmp/autoclaw.service\\n')"
                ),
                "sys.exit(0)",
            ]
        ),
        encoding="utf-8",
    )
    systemctl_bin.chmod(0o755)
    monkeypatch.setenv("AUTOCLAW_SYSTEMCTL_BIN", str(systemctl_bin))

    try:
        await cli.cmd_init(_build_init_args(config_path, data_dir))
        stop_result = cli.cmd_service_stop(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=False,
            )
        )
        restart_result = cli.cmd_service_restart(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=False,
            )
        )
    finally:
        get_settings.cache_clear()
        await dispose_db_engine()

    assert stop_result == 0
    assert restart_result == 0
    log_lines = systemctl_log.read_text(encoding="utf-8").splitlines()
    assert any("stop autoclaw.service" in line for line in log_lines)
    assert any("restart autoclaw.service" in line for line in log_lines)
