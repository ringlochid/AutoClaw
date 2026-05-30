from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tomllib
from pathlib import Path

import pytest
from anyio import Path as AnyioPath
from app import cli
from app.config import get_settings
from app.db.session import dispose_db_engine
from app.paths import default_database_path
from app.runtime.openclaw import build_openclaw_gateway_adapter
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase5a.support import task_start_payload


def _build_init_args(config_path: Path, data_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        host="127.0.0.1",
        port=8123,
        log_level="INFO",
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        force=True,
        skip_db_upgrade=False,
        json=False,
    )


def _write_json_mapping(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_fake_openclaw_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "config_path = Path(os.environ['OPENCLAW_CONFIG_PATH'])",
                "if config_path.is_file():",
                "    payload = json.loads(config_path.read_text(encoding='utf-8'))",
                "else:",
                "    payload = {}",
                "",
                "def save() -> None:",
                "    config_path.parent.mkdir(parents=True, exist_ok=True)",
                "    config_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')",
                "",
                "def merge(base, patch):",
                "    if isinstance(base, dict) and isinstance(patch, dict):",
                "        merged = dict(base)",
                "        for key, value in patch.items():",
                "            if value is None:",
                "                merged.pop(key, None)",
                "            elif isinstance(value, dict) and isinstance(merged.get(key), dict):",
                "                merged[key] = merge(merged[key], value)",
                "            else:",
                "                merged[key] = value",
                "        return merged",
                "    return patch",
                "",
                "args = sys.argv[1:]",
                "if args[:3] == ['agents', 'list', '--json']:",
                "    default_agents = [{'id': 'main', 'default': True}]",
                "    raw_agents = payload.get('agents', {}).get('list') or default_agents",
                "    out = []",
                "    has_default = any(",
                "        isinstance(item, dict) and item.get('default') is True",
                "        for item in raw_agents",
                "    )",
                "    for index, entry in enumerate(raw_agents):",
                "        if not isinstance(entry, dict):",
                "            continue",
                "        agent_id = entry.get('id')",
                "        if not isinstance(agent_id, str) or not agent_id.strip():",
                "            continue",
                "        out.append({",
                "            'id': agent_id.strip(),",
                "            'isDefault': bool(",
                "                entry.get('default') is True or (not has_default and index == 0)",
                "            ),",
                "            'name': entry.get('name'),",
                "            'workspace': entry.get('workspace'),",
                "            'agentDir': entry.get('agentDir'),",
                "        })",
                "    print(json.dumps(out))",
                "    raise SystemExit(0)",
                "if len(args) >= 6 and args[:2] == ['agents', 'add'] and args[3] == '--workspace':",
                "    agent_id = args[2]",
                "    workspace = args[4]",
                "    agents = payload.setdefault('agents', {}).setdefault('list', [])",
                "    agents.append({",
                "        'id': agent_id,",
                "        'workspace': workspace,",
                "        'agentDir': str(Path(workspace) / '.openclaw-agent'),",
                "    })",
                "    save()",
                "    print(json.dumps({'agentId': agent_id, 'workspace': workspace}))",
                "    raise SystemExit(0)",
                "if len(args) == 4 and args[:2] == ['mcp', 'set']:",
                "    name = args[2]",
                "    value = json.loads(args[3])",
                "    servers = payload.setdefault('mcp', {}).setdefault('servers', {})",
                "    servers[name] = value",
                "    save()",
                "    print(f'Saved MCP server {name}')",
                "    raise SystemExit(0)",
                "if args == ['config', 'patch', '--stdin']:",
                "    payload = merge(payload, json.load(sys.stdin))",
                "    save()",
                "    print('Patched config')",
                "    raise SystemExit(0)",
                "print('unsupported openclaw test command: ' + ' '.join(args), file=sys.stderr)",
                "raise SystemExit(2)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_openclaw_config(
    path: Path,
    *,
    agents: list[dict[str, object]] | None = None,
    gateway_auth: dict[str, object] | None = None,
    gateway_port: int | None = None,
) -> None:
    payload: dict[str, object] = {}
    if agents is not None:
        payload["agents"] = {"list": agents}
    gateway_payload: dict[str, object] = {}
    if gateway_auth is not None:
        gateway_payload["auth"] = gateway_auth
    if gateway_port is not None:
        gateway_payload["port"] = gateway_port
    if gateway_payload:
        payload["gateway"] = gateway_payload
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_stale_flows_schema(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE flows (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL
            )
            """
        )
        connection.commit()


@pytest.mark.asyncio
async def test_phase5a_root_cli_definitions_import_creates_and_replays_noop(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    definition_path = tmp_path / "phase5a-role.yaml"
    _write_json_mapping(
        definition_path,
        {
            "kind": "role",
            "id": "phase5a-cli-role",
            "description": "Role imported through the root CLI.",
            "allowed_node_kinds": ["worker"],
            "instruction": "Stay scoped to the CLI import test.",
        },
    )

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()

        created = await cli.cmd_definitions_import(
            argparse.Namespace(
                config=str(config_path),
                file=str(definition_path),
                overwrite="reject",
                json=True,
            )
        )
        created_payload = json.loads(capsys.readouterr().out)
        assert created == 0
        assert created_payload["ok"] is True
        assert created_payload["results"][0]["status"] == "imported"
        assert created_payload["results"][0]["revision_no"] == 1

        unchanged = await cli.cmd_definitions_import(
            argparse.Namespace(
                config=str(config_path),
                file=str(definition_path),
                overwrite="reject",
                json=True,
            )
        )
        unchanged_payload = json.loads(capsys.readouterr().out)
        assert unchanged == 0
        assert unchanged_payload["results"][0]["status"] == "unchanged"
        assert unchanged_payload["results"][0]["revision_no"] == 1
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_definitions_import_rejects_and_allows_new_revision(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    definition_path = tmp_path / "phase5a-role.yaml"
    _write_json_mapping(
        definition_path,
        {
            "kind": "role",
            "id": "phase5a-cli-role",
            "description": "Role imported through the root CLI.",
            "allowed_node_kinds": ["worker"],
            "instruction": "Stay scoped to the CLI import test.",
        },
    )

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        await cli.cmd_definitions_import(
            argparse.Namespace(
                config=str(config_path),
                file=str(definition_path),
                overwrite="reject",
                json=True,
            )
        )
        capsys.readouterr()

        _write_json_mapping(
            definition_path,
            {
                "kind": "role",
                "id": "phase5a-cli-role",
                "description": "Role imported through the root CLI. revision 2.",
                "allowed_node_kinds": ["worker"],
                "instruction": "Stay scoped to the CLI import test.",
            },
        )
        rejected = await cli.cmd_definitions_import(
            argparse.Namespace(
                config=str(config_path),
                file=str(definition_path),
                overwrite="reject",
                json=True,
            )
        )
        rejected_payload = json.loads(capsys.readouterr().out)
        assert rejected == 1
        assert rejected_payload["ok"] is False
        assert rejected_payload["results"][0]["status"] == "rejected"
        assert "already exists with different content" in rejected_payload["results"][0]["reason"]

        updated = await cli.cmd_definitions_import(
            argparse.Namespace(
                config=str(config_path),
                file=str(definition_path),
                overwrite="allow_new_revision",
                json=True,
            )
        )
        updated_payload = json.loads(capsys.readouterr().out)
        assert updated == 0
        assert updated_payload["ok"] is True
        assert updated_payload["results"][0]["status"] == "imported"
        assert updated_payload["results"][0]["revision_no"] == 2
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_definitions_import_scans_top_level_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    top_level = tmp_path / "top-level.yaml"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "nested.yaml"

    _write_json_mapping(
        top_level,
        {
            "kind": "role",
            "id": "top-level-role",
            "description": "Top-level role for shallow scan.",
            "allowed_node_kinds": ["worker"],
        },
    )
    _write_json_mapping(
        nested,
        {
            "kind": "role",
            "id": "nested-role",
            "description": "Nested role that should be ignored.",
            "allowed_node_kinds": ["worker"],
        },
    )

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        monkeypatch.chdir(tmp_path)
        result = await cli.cmd_definitions_import(
            argparse.Namespace(
                config=str(config_path),
                file=None,
                overwrite="reject",
                json=True,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["ok"] is True
        assert [item["key"] for item in payload["results"]] == ["top-level-role"]
        assert payload["results"][0]["status"] == "imported"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_task_compose_start_uses_file_entrypoint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_compose_path = tmp_path / "task-compose.yaml"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_json_mapping(
        task_compose_path,
        task_start_payload().model_dump(mode="json"),
    )

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        with gateway_server.configured_env():
            result = await cli.cmd_task_compose_start(
                argparse.Namespace(
                    config=str(config_path),
                    file=str(task_compose_path),
                    json=True,
                )
            )
        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["task_id"]
        assert payload["compiled_plan_id"]
        assert payload["active_flow_revision_id"]
        assert payload["flow_status"] == "running"
        assert await AnyioPath(payload["workflow_manifest_ref"]["path"]).exists()
    finally:
        gateway_server.close()
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_config_show_redacts_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = cli.cmd_config_show(
            argparse.Namespace(
                config=str(config_path),
                json=True,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["security"]["api_key"] == "__AUTOCLAW_REDACTED__"
        assert payload["security"]["internal_api_key"] == "__AUTOCLAW_REDACTED__"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_openclaw_check_reports_supported_loopback(
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
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            await cli.cmd_openclaw_setup(
                argparse.Namespace(
                    config=str(config_path),
                    non_interactive=True,
                    json=False,
                    plain=False,
                    no_color=False,
                )
            )
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
        assert result == 0
        assert payload["ok"] is True
        assert payload["support_status"] == "supported"
        assert payload["effective_auth"] == "token"
        assert payload["compatibility"]["role"] == "operator"
    finally:
        gateway_server.close()
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_writes_wrapper_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=8123,
                    log_level="INFO",
                    api_key="api-test-key",
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
        assert result == 0
        assert payload["ok"] is True
        assert config_path.exists()
        assert payload["server"]["host"] == "127.0.0.1"
        assert payload["server"]["port"] == 8123
        assert payload["server"]["ok"] is True
        assert payload["openclaw"]["support_status"] == "supported"
        assert payload["openclaw"]["loopback"] is True
        assert payload["openclaw"]["effective_auth"] == "token"
        assert payload["worker_agent_id"] == "autoclaw-worker"
        assert payload["operator_agent_id"] == "autoclaw-operator"
        assert await AnyioPath(payload["wrapper_state_path"]).exists()
        assert await AnyioPath(payload["material_paths"]["profile"]).exists()
        assert await AnyioPath(payload["material_paths"]["operator_contract"]).exists()
        assert await AnyioPath(payload["material_paths"]["mcp_surfaces"]).exists()
        config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        assert config_payload["openclaw"]["base_url"] == gateway_server.base_url
        assert config_payload["openclaw"]["binary_path"] == str(openclaw_bin)
        assert config_payload["openclaw"]["config_path"] == str(openclaw_config)
        assert config_payload["openclaw"]["agent_id"] == "autoclaw-worker"
        assert config_payload["openclaw"]["operator_agent_id"] == "autoclaw-operator"
        assert config_payload["runtime"]["watchdog_enabled"] is True
        openclaw_payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
        agents_by_id = {
            entry["id"]: entry
            for entry in openclaw_payload["agents"]["list"]
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
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
        assert openclaw_payload["mcp"]["servers"]["autoclaw-operator"]["url"].endswith(
            "/operator/mcp"
        )
        assert openclaw_payload["mcp"]["servers"]["autoclaw-node"]["url"].endswith("/node/mcp")
        assert "codex" not in openclaw_payload["mcp"]["servers"]["autoclaw-operator"]
        assert "codex" not in openclaw_payload["mcp"]["servers"]["autoclaw-node"]
    finally:
        gateway_server.close()
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_repairs_stale_sqlite_schema(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    database_path = default_database_path(data_dir)
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=True,
                json=False,
            )
        )
        capsys.readouterr()
        await dispose_db_engine()
        _write_stale_flows_schema(database_path)

        with gateway_server.configured_env():
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(data_dir),
                    database_url=None,
                    host="127.0.0.1",
                    port=8123,
                    log_level="INFO",
                    api_key="api-test-key",
                    internal_api_key="internal-test-key",
                    force=False,
                    skip_db_upgrade=False,
                    install_daemon=False,
                    skip_daemon=True,
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_persists_openclaw_runtime_inputs_for_env_free_compatibility(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(
        openclaw_config,
        gateway_auth={
            "token": "gateway-live-token",
        },
    )
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", gateway_server.base_url)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", raising=False)

    try:
        result = await cli.cmd_onboard(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(tmp_path / "autoclaw-data"),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=False,
                skip_db_upgrade=False,
                install_daemon=False,
                skip_daemon=True,
                no_start=True,
                non_interactive=True,
                json=True,
                plain=False,
                no_color=False,
            )
        )
        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["ok"] is True

        monkeypatch.delenv("AUTOCLAW_OPENCLAW__BINARY_PATH", raising=False)
        monkeypatch.delenv("OPENCLAW_CONFIG_PATH", raising=False)
        monkeypatch.delenv("AUTOCLAW_OPENCLAW__BASE_URL", raising=False)
        get_settings.cache_clear()
        with cli._command_env(config_path=config_path):
            settings = get_settings()
            adapter = build_openclaw_gateway_adapter(settings)
            compatibility = await adapter.check_compatibility()
        assert compatibility.role == "operator"
        config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        assert config_payload["openclaw"]["base_url"] == gateway_server.base_url
        assert config_payload["openclaw"]["binary_path"] == str(openclaw_bin)
        assert config_payload["openclaw"]["config_path"] == str(openclaw_config)
    finally:
        get_settings.cache_clear()
        gateway_server.close()
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_interactive_defaults_to_bootstrap_dedicated_agents(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    answers = iter(["", "", ""])  # continue, worker default, operator default
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(
        openclaw_config,
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
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", gateway_server.base_url)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-config-token")
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__OPERATOR_AGENT_ID", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    try:
        with gateway_server.configured_env():
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=8123,
                    log_level="INFO",
                    api_key="api-test-key",
                    internal_api_key="internal-test-key",
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
            check_result = await cli.cmd_openclaw_check(
                argparse.Namespace(
                    config=str(config_path),
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_interactive_guided_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    openclaw_bin = tmp_path / "openclaw"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    answers = iter(["", "", ""])  # continue, worker default, operator default
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    try:
        with gateway_server.configured_env():
            monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
            result = await cli.cmd_onboard(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(tmp_path / "autoclaw-data"),
                    database_url=None,
                    host="127.0.0.1",
                    port=8123,
                    log_level="INFO",
                    api_key="api-test-key",
                    internal_api_key="internal-test-key",
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
    assert config_path.exists()


@pytest.mark.asyncio
async def test_phase5a_root_cli_openclaw_setup_patches_selected_profiles_tool_slice_only(
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
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(
        openclaw_config,
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
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", gateway_server.base_url)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-config-token")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__AGENT_ID", "leo-worker")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__OPERATOR_AGENT_ID", "leo-operator")

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = await cli.cmd_openclaw_setup(
            argparse.Namespace(
                config=str(config_path),
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
        openclaw_payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
        agents_by_id = {
            entry["id"]: entry
            for entry in openclaw_payload["agents"]["list"]
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        worker_entry = agents_by_id["leo-worker"]
        operator_entry = agents_by_id["leo-operator"]
        assert worker_entry["name"] == "Leo Worker"
        assert worker_entry["workspace"] == "/tmp/leo-worker-space"
        assert worker_entry["agentDir"] == "/tmp/leo-worker-agent"
        assert worker_entry["sandbox"]["mode"] == "workspace"
        assert worker_entry["identity"] == {"name": "Keep worker"}
        assert worker_entry["tools"]["allow"] == ["notes__search"]
        assert worker_entry["tools"]["profile"] == "full"
        assert worker_entry["tools"]["deny"] == ["autoclaw-operator__*"]
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
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_fails_before_db_when_openclaw_binary_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_config(openclaw_config)
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
                    port=8123,
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_configure_all_fails_before_local_runtime_when_openclaw_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
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
            "app.cli_commands.operator.cmd_service_install",
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


@pytest.mark.asyncio
async def test_phase5a_configure_service_fails_before_service_install_when_openclaw_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()

        def _unexpected_service_install(_args: argparse.Namespace) -> int:
            raise AssertionError(
                "service install should not run when OpenClaw preflight is blocked"
            )

        monkeypatch.setattr(
            "app.cli_commands.operator.cmd_service_install",
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_service_install_fails_before_unit_write_when_openclaw_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    unit_dir = tmp_path / "systemd-user"
    env_file = tmp_path / "autoclaw.env"
    openclaw_config = tmp_path / "openclaw.json"
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        result = cli._cmd_service_install(
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_doctor_fix_fails_fast_when_preflight_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    openclaw_config = tmp_path / "openclaw.json"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_onboard_interactive_requires_tty(
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
            port=8123,
            log_level="INFO",
            api_key="api-test-key",
            internal_api_key="internal-test-key",
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
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_openclaw_check_blocks_ambiguous_auth(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    local_openclaw_config = tmp_path / "openclaw.json"
    _write_fake_openclaw_config(
        local_openclaw_config,
        gateway_auth={
            "token": "gateway-token",
            "password": "gateway-password",
        },
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_openclaw_config))
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", sys.executable)

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
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


@pytest.mark.asyncio
async def test_phase5a_root_cli_openclaw_setup_bootstraps_gateway_token_and_port(
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
    _write_fake_openclaw_cli(openclaw_bin)
    _write_fake_openclaw_config(openclaw_config, gateway_port=19055)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli._cmd_init(_build_init_args(config_path, data_dir))
        capsys.readouterr()
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        answers = iter(["19055", "gateway-config-token"])
        monkeypatch.setattr(
            "app.cli_commands.openclaw_wrapper.text", lambda *args, **kwargs: next(answers)
        )
        monkeypatch.setattr("builtins.input", lambda _prompt="": "")
        result = await cli.cmd_openclaw_setup(
            argparse.Namespace(
                config=str(config_path),
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
    config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert config_payload["openclaw"]["gateway_token"] == "gateway-config-token"
    assert config_payload["openclaw"]["base_url"] == "http://127.0.0.1:19055"
    host_payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
    assert host_payload["gateway"]["port"] == 19055
    assert host_payload["gateway"]["auth"]["mode"] == "token"
    assert host_payload["gateway"]["auth"]["token"] == "gateway-config-token"
