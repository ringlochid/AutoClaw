from __future__ import annotations

import argparse
import json
import socket
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from tests.helpers.openclaw_cli import write_fake_openclaw_cli


@dataclass(frozen=True)
class RootCliPaths:
    config_path: Path
    data_dir: Path
    openclaw_bin: Path
    openclaw_config: Path


def build_root_cli_paths(tmp_path: Path) -> RootCliPaths:
    return RootCliPaths(
        config_path=tmp_path / "autoclaw-config.toml",
        data_dir=tmp_path / "autoclaw-data",
        openclaw_bin=tmp_path / "openclaw",
        openclaw_config=tmp_path / "openclaw.json",
    )


def build_init_args(
    config_or_paths: RootCliPaths | Path,
    data_dir: Path | None = None,
) -> argparse.Namespace:
    if isinstance(config_or_paths, RootCliPaths):
        config_path = config_or_paths.config_path
        resolved_data_dir = config_or_paths.data_dir
    else:
        assert data_dir is not None
        config_path = config_or_paths
        resolved_data_dir = data_dir
    return argparse.Namespace(
        config=str(config_path),
        data_dir=str(resolved_data_dir),
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


def available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.bind(("127.0.0.1", 0))
        return int(probe_socket.getsockname()[1])


def write_json_mapping(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_fake_openclaw_config(
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


def write_stale_flows_schema(database_path: Path) -> None:
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


def configure_fake_openclaw_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    openclaw_bin: Path,
    openclaw_config: Path,
) -> None:
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BINARY_PATH", str(openclaw_bin))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config))
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__BASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", raising=False)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__AGENT_ID", raising=False)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW__OPERATOR_AGENT_ID", raising=False)


def build_fake_openclaw_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    agents: list[dict[str, object]] | None = None,
    gateway_auth: dict[str, object] | None = None,
    gateway_port: int | None = None,
) -> RootCliPaths:
    paths = build_root_cli_paths(tmp_path)
    write_fake_openclaw_cli(paths.openclaw_bin)
    write_fake_openclaw_config(
        paths.openclaw_config,
        agents=agents,
        gateway_auth=gateway_auth,
        gateway_port=gateway_port,
    )
    configure_fake_openclaw_env(
        monkeypatch,
        openclaw_bin=paths.openclaw_bin,
        openclaw_config=paths.openclaw_config,
    )
    return paths


def install_interactive_stdio(
    monkeypatch: pytest.MonkeyPatch,
    *,
    answers: Iterator[str],
    prompt_log: list[str],
) -> None:
    def next_answer(prompt: str = "") -> str:
        prompt_log.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", next_answer)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)


def load_openclaw_agents_by_id(openclaw_config: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(openclaw_config.read_text(encoding="utf-8"))
    return cast(
        dict[str, dict[str, Any]],
        {
        entry["id"]: entry
        for entry in payload["agents"]["list"]
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        },
    )


__all__ = [
    "RootCliPaths",
    "available_loopback_port",
    "build_fake_openclaw_host",
    "build_init_args",
    "build_root_cli_paths",
    "configure_fake_openclaw_env",
    "install_interactive_stdio",
    "load_openclaw_agents_by_id",
    "write_fake_openclaw_config",
    "write_json_mapping",
    "write_stale_flows_schema",
]
