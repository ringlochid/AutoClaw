from __future__ import annotations

import argparse
import json
from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from anyio import Path as AnyioPath
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.openclaw_cli import write_fake_openclaw_cli
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.integration.public_surfaces.root_cli.support import (
    build_init_args,
    write_fake_openclaw_config,
    write_json_mapping,
)
from tests.integration.public_surfaces.support import task_start_payload


@pytest.mark.asyncio
async def test_root_cli_definitions_import_creates_and_replays_noop(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    definition_path = tmp_path / "root-cli-role.yaml"
    write_json_mapping(
        definition_path,
        {
            "kind": "role",
            "id": "root-cli-role",
            "description": "Role imported through the root CLI.",
            "allowed_node_kinds": ["worker"],
            "instruction": "Stay scoped to the CLI import test.",
        },
    )

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
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


async def test_root_cli_definitions_import_rejects_and_allows_new_revision(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    definition_path = tmp_path / "root-cli-role.yaml"
    write_json_mapping(
        definition_path,
        {
            "kind": "role",
            "id": "root-cli-role",
            "description": "Role imported through the root CLI.",
            "allowed_node_kinds": ["worker"],
            "instruction": "Stay scoped to the CLI import test.",
        },
    )

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
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

        write_json_mapping(
            definition_path,
            {
                "kind": "role",
                "id": "root-cli-role",
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


async def test_root_cli_definitions_import_scans_top_level_only(
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

    write_json_mapping(
        top_level,
        {
            "kind": "role",
            "id": "top-level-role",
            "description": "Top-level role for shallow scan.",
            "allowed_node_kinds": ["worker"],
        },
    )
    write_json_mapping(
        nested,
        {
            "kind": "role",
            "id": "nested-role",
            "description": "Nested role that should be ignored.",
            "allowed_node_kinds": ["worker"],
        },
    )

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
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


async def test_root_cli_task_compose_start_uses_file_entrypoint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_compose_path = tmp_path / "task-compose.yaml"
    gateway_server = LocalGatewayTestServer()
    gateway_server.start()
    write_json_mapping(
        task_compose_path,
        task_start_payload().model_dump(mode="json"),
    )

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
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


async def test_root_cli_config_show_redacts_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
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


async def test_root_cli_openclaw_check_reports_supported_loopback(
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
    write_fake_openclaw_cli(openclaw_bin)
    write_fake_openclaw_config(openclaw_config)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))

    try:
        await cli.cmd_init(build_init_args(config_path, data_dir))
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
