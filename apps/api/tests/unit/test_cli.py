from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import tomllib
from importlib import resources
from pathlib import Path

import pytest
from app import cli
from app.config import DEFAULT_LOG_LEVEL, get_settings
from app.db.session import dispose_db_engine

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
        port=8123,
        log_level=DEFAULT_LOG_LEVEL,
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        force=True,
        skip_db_upgrade=False,
        json=True,
    )


def _packaged_seed_counts() -> dict[str, int]:
    definitions_root = resources.files("app.resources").joinpath("definitions")
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
        result = await cli._cmd_init(_build_init_args(config_path, data_dir))
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
        result = await cli._cmd_init(_build_init_args(config_path, data_dir))
    finally:
        await dispose_db_engine()

    assert result == 0
    output = capsys.readouterr().out
    assert "sqlalchemy.engine.Engine" not in output


def test_build_parser_supports_baseline_commands() -> None:
    parser = cli.build_parser()

    serve_args = parser.parse_args(["serve"])
    assert serve_args.handler is cli._cmd_serve

    init_args = parser.parse_args(["init", "--json"])
    assert init_args.handler is cli._cmd_init
    assert init_args.json is True
    assert init_args.log_level == DEFAULT_LOG_LEVEL

    db_reset_args = parser.parse_args(["db", "reset", "--json"])
    assert db_reset_args.handler is cli._cmd_db_reset
    assert db_reset_args.json is True

    service_install_args = parser.parse_args(["service", "install", "--no-start"])
    assert service_install_args.handler is cli._cmd_service_install
    assert service_install_args.no_start is True

    service_start_args = parser.parse_args(["service", "start", "--json"])
    assert service_start_args.handler is cli._cmd_service_start
    assert service_start_args.json is True

    service_stop_args = parser.parse_args(["service", "stop"])
    assert service_stop_args.handler is cli._cmd_service_stop

    service_restart_args = parser.parse_args(["service", "restart"])
    assert service_restart_args.handler is cli._cmd_service_restart

    service_status_args = parser.parse_args(["service", "status"])
    assert service_status_args.handler is cli._cmd_service_status

    definitions_import_args = parser.parse_args(["definitions", "import", "--json"])
    assert definitions_import_args.handler is cli.cmd_definitions_import
    assert definitions_import_args.json is True
    assert definitions_import_args.overwrite == "reject"

    task_compose_start_args = parser.parse_args(
        ["task-compose", "start", "--file", "task-compose.yaml"]
    )
    assert task_compose_start_args.handler is cli.cmd_task_compose_start
    assert task_compose_start_args.file == "task-compose.yaml"

    onboard_args = parser.parse_args(["onboard", "--install-daemon", "--json"])
    assert onboard_args.handler is cli.cmd_onboard
    assert onboard_args.install_daemon is True
    assert onboard_args.log_level == DEFAULT_LOG_LEVEL

    configure_args = parser.parse_args(["configure", "--section", "openclaw"])
    assert configure_args.handler is cli.cmd_configure
    assert configure_args.section == "openclaw"

    doctor_args = parser.parse_args(["doctor", "--fix"])
    assert doctor_args.handler is cli.cmd_doctor
    assert doctor_args.fix is True

    config_path_args = parser.parse_args(["config", "path"])
    assert config_path_args.handler is cli.cmd_config_path

    config_show_args = parser.parse_args(["config", "show", "--json"])
    assert config_show_args.handler is cli.cmd_config_show
    assert config_show_args.json is True

    openclaw_check_args = parser.parse_args(["openclaw", "check", "--json"])
    assert openclaw_check_args.handler is cli.cmd_openclaw_check

    openclaw_setup_args = parser.parse_args(["openclaw", "setup", "--non-interactive"])
    assert openclaw_setup_args.handler is cli.cmd_openclaw_setup
    assert openclaw_setup_args.non_interactive is True

    openclaw_doctor_args = parser.parse_args(["openclaw", "doctor", "--fix"])
    assert openclaw_doctor_args.handler is cli.cmd_openclaw_doctor
    assert openclaw_doctor_args.fix is True

    service_uninstall_args = parser.parse_args(["service", "uninstall", "--remove-env-file"])
    assert service_uninstall_args.handler is cli._cmd_service_uninstall
    assert service_uninstall_args.remove_env_file is True


def test_packaged_seed_definitions_are_available() -> None:
    definitions_root = resources.files("app.resources").joinpath("definitions")

    assert definitions_root.joinpath("roles").joinpath("planning_lead.yaml").is_file()
    assert definitions_root.joinpath("policies").joinpath("standard_worker.yaml").is_file()
    assert (
        definitions_root.joinpath("workflows")
        .joinpath("normal_parent_first_release.yaml")
        .is_file()
    )


def test_render_service_unit_uses_python_module_entrypoint(tmp_path: Path) -> None:
    rendered = cli._render_service_unit(
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
        asyncio.run(cli._cmd_init(_build_init_args(config_path, data_dir)))
        capsys.readouterr()
        result = cli._cmd_serve(argparse.Namespace(config=str(config_path)))
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
        asyncio.run(cli._cmd_init(_build_init_args(config_path, data_dir)))
        capsys.readouterr()
        install_result = cli._cmd_service_install(
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
        status_result = cli._cmd_service_status(
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
    payload = json.loads(capsys.readouterr().out)
    assert payload["manager"] == "systemd-user"
    assert payload["installed"] is True
    assert payload["running"] is True
    log_lines = systemctl_log.read_text(encoding="utf-8").splitlines()
    assert "daemon-reload" in log_lines[0]
    assert any("enable autoclaw.service" in line for line in log_lines)


@pytest.mark.asyncio
async def test_db_reset_recreates_sqlite_database(tmp_path: Path) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = data_dir / "autoclaw.db"

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        database_path.write_bytes(b"stale")
        result = await cli._cmd_db_reset(
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
        await cli._cmd_init(init_args)
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
                cli._cmd_db_upgrade,
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
        init_result = await cli._cmd_init(init_args)
        upgrade_result = await asyncio.to_thread(
            cli._cmd_db_upgrade,
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
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = cli._cmd_service_start(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=False,
            )
        )
        capsys.readouterr()
        status_result = cli._cmd_service_status(
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
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        stop_result = cli._cmd_service_stop(
            argparse.Namespace(
                config=str(config_path),
                name="autoclaw",
                json=False,
            )
        )
        restart_result = cli._cmd_service_restart(
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
