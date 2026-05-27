from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from anyio import Path as AnyioPath
from app import cli
from app.db.session import dispose_db_engine
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
