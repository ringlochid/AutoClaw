from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoclaw.config import Settings
from autoclaw.integrations.openclaw.gateway.discovery import (
    OpenClawResolvedHostState,
    load_openclaw_config_payload,
    normalize_openclaw_secret,
)

AUTOCLAW_NODE_MCP_SERVER_NAME = "autoclaw-node"
AUTOCLAW_OPERATOR_MCP_SERVER_NAME = "autoclaw-operator"
AUTOCLAW_WORKER_AGENT_ID = "autoclaw-worker"
AUTOCLAW_OPERATOR_AGENT_ID = "autoclaw-operator"
OPENCLAW_DEFAULT_AGENT_ID = "main"
OPENCLAW_AGENT_WORKSPACE_ROOT = Path.home() / ".openclaw" / "workspaces"
OPENCLAW_AGENT_DIR_ROOT = Path.home() / ".openclaw" / "agents"
WORKER_OPERATOR_TOOL_DENY = f"{AUTOCLAW_OPERATOR_MCP_SERVER_NAME}__*"
OPERATOR_NODE_TOOL_DENY = f"{AUTOCLAW_NODE_MCP_SERVER_NAME}__*"
WORKER_RUNTIME_TOOL_DENY = (WORKER_OPERATOR_TOOL_DENY,)
OPENCLAW_EXEC_TOOL_SETTINGS = {
    "host": "gateway",
    "security": "full",
    "ask": "off",
    "backgroundMs": 30000,
    "timeoutSec": 3600,
}
OPENCLAW_DEFAULT_GATEWAY_PORT = 18789
OpenClawCommandObserver = Callable[[str], None]
OpenClawCommandOutputObserver = Callable[[str, int, str, str], None]
OPENCLAW_SECRET_PATTERN = re.compile(
    r"(?i)((?:authorization|api[_-]?key|internal[_-]?api[_-]?key|password|secret|token)"
    r"[\"']?\s*[:=]\s*[\"']?)([^\"'\s,}]+)"
)
OPENCLAW_BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+/=-]+)")


@dataclass(frozen=True)
class OpenClawAgentSummary:
    id: str
    is_default: bool
    name: str | None = None
    workspace: str | None = None
    agent_dir: str | None = None


def build_autoclaw_mcp_servers(
    settings: Settings,
) -> dict[str, dict[str, Any]]:
    base_url = f"http://{settings.api_host}:{settings.api_port}"
    operator_server: dict[str, Any] = {
        "url": f"{base_url}/operator/mcp",
        "transport": "streamable-http",
        "headers": {
            "Authorization": f"Bearer {settings.api_key}",
        },
    }
    node_server: dict[str, Any] = {
        "url": f"{base_url}/node/mcp",
        "transport": "streamable-http",
    }
    return {
        AUTOCLAW_OPERATOR_MCP_SERVER_NAME: operator_server,
        AUTOCLAW_NODE_MCP_SERVER_NAME: node_server,
    }


def load_host_agents_from_config(
    host_state: OpenClawResolvedHostState,
) -> tuple[OpenClawAgentSummary, ...]:
    payload = load_openclaw_config_payload(Path(host_state.config_path))
    if not isinstance(payload, dict):
        return (OpenClawAgentSummary(id=OPENCLAW_DEFAULT_AGENT_ID, is_default=True),)
    agents_payload = payload.get("agents")
    if not isinstance(agents_payload, dict):
        return (OpenClawAgentSummary(id=OPENCLAW_DEFAULT_AGENT_ID, is_default=True),)
    raw_list = agents_payload.get("list")
    if not isinstance(raw_list, list) or not raw_list:
        return (OpenClawAgentSummary(id=OPENCLAW_DEFAULT_AGENT_ID, is_default=True),)

    summaries: list[OpenClawAgentSummary] = []
    default_id = None
    for entry in raw_list:
        if (
            isinstance(entry, dict)
            and entry.get("default") is True
            and isinstance(entry.get("id"), str)
        ):
            default_id = entry["id"].strip()
            break
    if not default_id:
        for entry in raw_list:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                default_id = entry["id"].strip()
                break
    default_id = default_id or OPENCLAW_DEFAULT_AGENT_ID

    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        raw_id = entry.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        agent_id = raw_id.strip()
        summaries.append(
            OpenClawAgentSummary(
                id=agent_id,
                is_default=agent_id == default_id,
                name=entry.get("name") if isinstance(entry.get("name"), str) else None,
                workspace=entry.get("workspace")
                if isinstance(entry.get("workspace"), str)
                else None,
                agent_dir=entry.get("agentDir") if isinstance(entry.get("agentDir"), str) else None,
            )
        )
    return tuple(summaries) or (
        OpenClawAgentSummary(id=OPENCLAW_DEFAULT_AGENT_ID, is_default=True),
    )


def load_host_mcp_servers_from_config(
    host_state: OpenClawResolvedHostState,
) -> dict[str, dict[str, Any]]:
    payload = load_openclaw_config_payload(Path(host_state.config_path))
    if not isinstance(payload, dict):
        return {}
    mcp_payload = payload.get("mcp")
    if not isinstance(mcp_payload, dict):
        return {}
    servers_payload = mcp_payload.get("servers")
    if not isinstance(servers_payload, dict):
        return {}
    return {
        str(name): value
        for name, value in servers_payload.items()
        if isinstance(name, str) and isinstance(value, dict)
    }


def set_openclaw_agent_profiles(
    host_state: OpenClawResolvedHostState,
    *,
    worker_agent_id: str,
    operator_agent_id: str,
    command_observer: OpenClawCommandObserver | None = None,
    command_output_observer: OpenClawCommandOutputObserver | None = None,
) -> tuple[str, ...]:
    payload = load_openclaw_config_payload(Path(host_state.config_path)) or {}
    if not isinstance(payload, dict):
        payload = {}
    agents_payload = payload.get("agents")
    if not isinstance(agents_payload, dict):
        agents_payload = {}
    raw_list = agents_payload.get("list")
    current_list = list(raw_list) if isinstance(raw_list, list) else []
    desired_entries = build_autoclaw_agent_entries(
        host_state,
        worker_agent_id=worker_agent_id,
        operator_agent_id=operator_agent_id,
    )

    updated_list: list[Any] = []
    written_ids: list[str] = []
    remaining = dict(desired_entries)
    for entry in current_list:
        if not isinstance(entry, dict):
            updated_list.append(entry)
            continue
        raw_id = entry.get("id")
        if not isinstance(raw_id, str) or raw_id not in remaining:
            updated_list.append(entry)
            continue
        updated_list.append(remaining.pop(raw_id))
        written_ids.append(raw_id)
    for agent_id, entry in remaining.items():
        updated_list.append(entry)
        written_ids.append(agent_id)

    run_openclaw_cli(
        host_state,
        "config",
        "patch",
        "--stdin",
        input_text=json.dumps(
            {"agents": {"list": updated_list}},
            separators=(",", ":"),
        ),
        command_observer=command_observer,
        command_output_observer=command_output_observer,
    )
    return tuple(written_ids)


def set_openclaw_mcp_servers(
    host_state: OpenClawResolvedHostState,
    *,
    servers: dict[str, dict[str, Any]],
    command_observer: OpenClawCommandObserver | None = None,
    command_output_observer: OpenClawCommandOutputObserver | None = None,
) -> tuple[str, ...]:
    written: list[str] = []
    for name, server in servers.items():
        run_openclaw_cli(
            host_state,
            "mcp",
            "set",
            name,
            json.dumps(server, separators=(",", ":")),
            command_observer=command_observer,
            command_output_observer=command_output_observer,
        )
        written.append(name)
    return tuple(written)


def list_openclaw_agents(
    host_state: OpenClawResolvedHostState,
    *,
    command_observer: OpenClawCommandObserver | None = None,
    command_output_observer: OpenClawCommandOutputObserver | None = None,
) -> tuple[OpenClawAgentSummary, ...]:
    raw_output = run_openclaw_cli(
        host_state,
        "agents",
        "list",
        "--json",
        command_observer=command_observer,
        command_output_observer=command_output_observer,
    )
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("openclaw agents list --json returned invalid JSON") from exc
    if not isinstance(payload, list):
        raise RuntimeError("openclaw agents list --json returned a non-list payload")

    summaries: list[OpenClawAgentSummary] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        raw_id = entry.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        summaries.append(
            OpenClawAgentSummary(
                id=raw_id.strip(),
                is_default=bool(entry.get("isDefault")),
                name=entry.get("name") if isinstance(entry.get("name"), str) else None,
                workspace=entry.get("workspace")
                if isinstance(entry.get("workspace"), str)
                else None,
                agent_dir=entry.get("agentDir") if isinstance(entry.get("agentDir"), str) else None,
            )
        )
    return tuple(summaries)


def bootstrap_openclaw_agent(
    host_state: OpenClawResolvedHostState,
    *,
    agent_id: str,
    workspace_dir: Path,
    command_observer: OpenClawCommandObserver | None = None,
    command_output_observer: OpenClawCommandOutputObserver | None = None,
) -> OpenClawAgentSummary:
    run_openclaw_cli(
        host_state,
        "agents",
        "add",
        agent_id,
        "--workspace",
        str(workspace_dir),
        "--non-interactive",
        "--json",
        command_observer=command_observer,
        command_output_observer=command_output_observer,
    )
    return OpenClawAgentSummary(
        id=agent_id,
        is_default=False,
        workspace=str(workspace_dir),
    )


def resolved_gateway_bootstrap_values(
    *,
    settings: Settings,
    host_state: OpenClawResolvedHostState,
    gateway_token: str,
    gateway_port: int | None,
) -> tuple[str, int]:
    resolved_token = normalize_openclaw_secret(gateway_token) or normalize_openclaw_secret(
        settings.openclaw.gateway_token
    )
    if not resolved_token:
        raise RuntimeError("OpenClaw gateway token is required for setup")

    if gateway_port is not None:
        resolved_port = gateway_port
    else:
        host_base_url = host_base_url_from_config(host_state)
        if host_base_url is not None:
            resolved_port = int(host_base_url.rsplit(":", 1)[1])
        else:
            resolved_port = OPENCLAW_DEFAULT_GATEWAY_PORT
    return resolved_token, resolved_port


def patch_openclaw_gateway_settings(
    host_state: OpenClawResolvedHostState,
    *,
    gateway_port: int,
    gateway_token: str,
    command_observer: OpenClawCommandObserver | None = None,
    command_output_observer: OpenClawCommandOutputObserver | None = None,
) -> None:
    payload = {
        "gateway": {
            "port": gateway_port,
            "bind": "loopback",
            "auth": {
                "mode": "token",
                "token": gateway_token,
            },
        }
    }
    run_openclaw_cli(
        host_state,
        "config",
        "patch",
        "--stdin",
        input_text=json.dumps(payload, separators=(",", ":")),
        command_observer=command_observer,
        command_output_observer=command_output_observer,
    )


def gateway_bootstrap_needed(host_state: OpenClawResolvedHostState) -> bool:
    return host_state.reason in {
        "MISSING_GATEWAY_TOKEN",
        "MISSING_GATEWAY_PASSWORD",
        "NO_SUPPORTED_GATEWAY_AUTH",
    }


def build_autoclaw_agent_entries(
    host_state: OpenClawResolvedHostState,
    *,
    worker_agent_id: str,
    operator_agent_id: str,
) -> dict[str, dict[str, Any]]:
    current_entries = load_host_agent_entries_from_config(host_state)
    worker_entry = current_entries.get(worker_agent_id, {"id": worker_agent_id})
    operator_entry = current_entries.get(operator_agent_id, {"id": operator_agent_id})
    return {
        worker_agent_id: _merge_agent_patch(
            worker_entry,
            _worker_agent_patch(
                agent_id=worker_agent_id,
            ),
        ),
        operator_agent_id: _merge_agent_patch(
            operator_entry,
            _operator_agent_patch(
                agent_id=operator_agent_id,
            ),
        ),
    }


def host_base_url_from_config(host_state: OpenClawResolvedHostState) -> str | None:
    payload = load_openclaw_config_payload(Path(host_state.config_path))
    if not isinstance(payload, dict):
        return None
    gateway_payload = payload.get("gateway")
    if not isinstance(gateway_payload, dict):
        return None
    raw_port = gateway_payload.get("port")
    if not isinstance(raw_port, int):
        return None
    return f"http://127.0.0.1:{raw_port}"


def default_openclaw_agent_workspace(agent_id: str) -> Path:
    return OPENCLAW_AGENT_WORKSPACE_ROOT / agent_id


def default_openclaw_agent_dir(agent_id: str) -> Path:
    return OPENCLAW_AGENT_DIR_ROOT / agent_id / "agent"


def load_host_agent_entries_from_config(
    host_state: OpenClawResolvedHostState,
) -> dict[str, dict[str, Any]]:
    payload = load_openclaw_config_payload(Path(host_state.config_path))
    if not isinstance(payload, dict):
        return {}
    agents_payload = payload.get("agents")
    if not isinstance(agents_payload, dict):
        return {}
    raw_list = agents_payload.get("list")
    if not isinstance(raw_list, list):
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        raw_id = entry.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        entries[raw_id.strip()] = entry
    return entries


def run_openclaw_cli(
    host_state: OpenClawResolvedHostState,
    *args: str,
    input_text: str | None = None,
    command_observer: OpenClawCommandObserver | None = None,
    command_output_observer: OpenClawCommandOutputObserver | None = None,
) -> str:
    binary_path = host_state.binary_path
    if not binary_path:
        raise RuntimeError("OpenClaw binary path is unavailable")
    command = [binary_path, *args]
    binary_name = Path(binary_path).name.lower()
    if binary_name.startswith("python"):
        command = [binary_path, "-m", "autoclaw", *args]
    command_label = _openclaw_command_label(args)
    if command_observer is not None:
        command_observer(command_label)
    env = os.environ.copy()
    env["OPENCLAW_CONFIG_PATH"] = host_state.config_path
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        env=env,
        input=input_text,
        text=True,
    )
    if command_output_observer is not None:
        command_output_observer(command_label, result.returncode, result.stdout, result.stderr)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"{command_label} failed: {_redact_openclaw_command_output(detail)}")
    return result.stdout


def _openclaw_command_label(args: tuple[str, ...]) -> str:
    if args == ("config", "patch", "--stdin"):
        return "openclaw config patch --stdin"
    if len(args) >= 4 and args[0:2] == ("mcp", "set"):
        return f"openclaw mcp set {args[2]}"
    return " ".join(("openclaw", *args))


def _redact_openclaw_command_output(value: str) -> str:
    redacted = OPENCLAW_BEARER_PATTERN.sub(r"\1<redacted>", value)
    return OPENCLAW_SECRET_PATTERN.sub(r"\1<redacted>", redacted)


def _merge_agent_patch(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in patch.items():
        current = merged.get(key)
        if key == "deny" and isinstance(value, list):
            merged[key] = value
            continue
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = _merge_agent_patch(current, value)
            continue
        merged[key] = value
    return merged


def _worker_agent_patch(
    *,
    agent_id: str,
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "tools": {
            "profile": "full",
            "deny": list(WORKER_RUNTIME_TOOL_DENY),
            "exec": dict(OPENCLAW_EXEC_TOOL_SETTINGS),
        },
    }
    if agent_id == AUTOCLAW_WORKER_AGENT_ID:
        patch.update(
            {
                "name": AUTOCLAW_WORKER_AGENT_ID,
                "workspace": str(default_openclaw_agent_workspace(agent_id)),
                "agentDir": str(default_openclaw_agent_dir(agent_id)),
                "reasoningDefault": "on",
                "identity": {
                    "name": "AutoClaw Worker",
                    "theme": "quiet, exact, tool-first",
                },
                "sandbox": {"mode": "off"},
            }
        )
    return patch


def _operator_agent_patch(
    *,
    agent_id: str,
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "tools": {
            "profile": "full",
            "deny": [OPERATOR_NODE_TOOL_DENY],
            "exec": dict(OPENCLAW_EXEC_TOOL_SETTINGS),
        },
    }
    if agent_id == AUTOCLAW_OPERATOR_AGENT_ID:
        patch.update(
            {
                "name": AUTOCLAW_OPERATOR_AGENT_ID,
                "workspace": str(default_openclaw_agent_workspace(agent_id)),
                "agentDir": str(default_openclaw_agent_dir(agent_id)),
                "memorySearch": {"enabled": False},
                "sandbox": {"mode": "off"},
            }
        )
    return patch


__all__ = [
    "AUTOCLAW_NODE_MCP_SERVER_NAME",
    "AUTOCLAW_OPERATOR_AGENT_ID",
    "AUTOCLAW_OPERATOR_MCP_SERVER_NAME",
    "AUTOCLAW_WORKER_AGENT_ID",
    "OPENCLAW_DEFAULT_AGENT_ID",
    "OpenClawAgentSummary",
    "OpenClawCommandObserver",
    "OpenClawCommandOutputObserver",
    "bootstrap_openclaw_agent",
    "build_autoclaw_agent_entries",
    "build_autoclaw_mcp_servers",
    "default_openclaw_agent_workspace",
    "gateway_bootstrap_needed",
    "host_base_url_from_config",
    "list_openclaw_agents",
    "load_host_agent_entries_from_config",
    "load_host_agents_from_config",
    "load_host_mcp_servers_from_config",
    "patch_openclaw_gateway_settings",
    "resolved_gateway_bootstrap_values",
    "run_openclaw_cli",
    "set_openclaw_agent_profiles",
    "set_openclaw_mcp_servers",
]
