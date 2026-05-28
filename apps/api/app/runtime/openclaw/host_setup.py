from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings
from app.runtime.openclaw.discovery import OpenClawResolvedHostState, load_openclaw_config_payload

AUTOCLAW_NODE_MCP_SERVER_NAME = "autoclaw-node"
AUTOCLAW_OPERATOR_MCP_SERVER_NAME = "autoclaw-operator"
AUTOCLAW_OPERATOR_AGENT_ID = "autoclaw-operator"
OPENCLAW_DEFAULT_AGENT_ID = "main"
OPENCLAW_AGENT_WORKSPACE_ROOT = Path.home() / ".openclaw" / "workspaces"
OPENCLAW_AGENT_DIR_ROOT = Path.home() / ".openclaw" / "agents"
WORKER_OPERATOR_TOOL_DENY = f"{AUTOCLAW_OPERATOR_MCP_SERVER_NAME}__*"
OPERATOR_NODE_TOOL_DENY = f"{AUTOCLAW_NODE_MCP_SERVER_NAME}__*"


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


def run_openclaw_cli(
    host_state: OpenClawResolvedHostState,
    *args: str,
    input_text: str | None = None,
) -> str:
    binary_path = host_state.binary_path
    if not binary_path:
        raise RuntimeError("OpenClaw binary path is unavailable")
    env = os.environ.copy()
    env["OPENCLAW_CONFIG_PATH"] = host_state.config_path
    result = subprocess.run(
        [binary_path, *args],
        capture_output=True,
        check=False,
        env=env,
        input=input_text,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"openclaw {' '.join(args)} failed: {detail}")
    return result.stdout


def list_openclaw_agents(host_state: OpenClawResolvedHostState) -> tuple[OpenClawAgentSummary, ...]:
    raw_output = run_openclaw_cli(host_state, "agents", "list", "--json")
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
    )
    return OpenClawAgentSummary(
        id=agent_id,
        is_default=False,
        workspace=str(workspace_dir),
    )


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


def _merged_string_list(existing: object, required: list[str]) -> list[str]:
    values: list[str] = []
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, str) and item not in values:
                values.append(item)
    for item in required:
        if item not in values:
            values.append(item)
    return values


def _merge_agent_patch(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in patch.items():
        current = merged.get(key)
        if key == "deny" and isinstance(value, list):
            merged[key] = _merged_string_list(current, value)
            continue
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = _merge_agent_patch(current, value)
            continue
        merged[key] = value
    return merged


def _worker_agent_patch(
    *,
    agent_id: str,
    current_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "sandbox": {"mode": "off"},
        "tools": {
            "profile": "full",
            "deny": [WORKER_OPERATOR_TOOL_DENY],
            "exec": {
                "host": "gateway",
                "security": "full",
                "ask": "off",
                "backgroundMs": 30000,
                "timeoutSec": 3600,
            },
        },
    }
    if not current_entry or not isinstance(current_entry.get("workspace"), str):
        patch["workspace"] = str(default_openclaw_agent_workspace(agent_id))
    if not current_entry or not isinstance(current_entry.get("agentDir"), str):
        patch["agentDir"] = str(default_openclaw_agent_dir(agent_id))
    if agent_id == "autoclaw-worker":
        patch.update(
            {
                "name": "autoclaw-worker",
                "thinkingDefault": "low",
                "reasoningDefault": "on",
                "identity": {
                    "name": "AutoClaw Worker",
                    "theme": "quiet, exact, tool-first",
                },
            }
        )
    return patch


def _operator_agent_patch(
    *,
    agent_id: str,
    current_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "memorySearch": {"enabled": False},
        "sandbox": {"mode": "off"},
        "tools": {
            "profile": "full",
            "deny": [OPERATOR_NODE_TOOL_DENY],
        },
    }
    if not current_entry or not isinstance(current_entry.get("workspace"), str):
        patch["workspace"] = str(default_openclaw_agent_workspace(agent_id))
    if not current_entry or not isinstance(current_entry.get("agentDir"), str):
        patch["agentDir"] = str(default_openclaw_agent_dir(agent_id))
    if agent_id == AUTOCLAW_OPERATOR_AGENT_ID:
        patch["name"] = AUTOCLAW_OPERATOR_AGENT_ID
    return patch


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
                current_entry=current_entries.get(worker_agent_id),
            ),
        ),
        operator_agent_id: _merge_agent_patch(
            operator_entry,
            _operator_agent_patch(
                agent_id=operator_agent_id,
                current_entry=current_entries.get(operator_agent_id),
            ),
        ),
    }


def set_openclaw_agent_profiles(
    host_state: OpenClawResolvedHostState,
    *,
    worker_agent_id: str,
    operator_agent_id: str,
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
    )
    return tuple(written_ids)


def set_openclaw_mcp_servers(
    host_state: OpenClawResolvedHostState,
    *,
    servers: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    written: list[str] = []
    for name, server in servers.items():
        run_openclaw_cli(
            host_state,
            "mcp",
            "set",
            name,
            json.dumps(server, separators=(",", ":")),
        )
        written.append(name)
    return tuple(written)


__all__ = [
    "AUTOCLAW_NODE_MCP_SERVER_NAME",
    "AUTOCLAW_OPERATOR_AGENT_ID",
    "AUTOCLAW_OPERATOR_MCP_SERVER_NAME",
    "OPENCLAW_DEFAULT_AGENT_ID",
    "OpenClawAgentSummary",
    "bootstrap_openclaw_agent",
    "build_autoclaw_agent_entries",
    "build_autoclaw_mcp_servers",
    "default_openclaw_agent_workspace",
    "list_openclaw_agents",
    "load_host_agent_entries_from_config",
    "load_host_agents_from_config",
    "load_host_mcp_servers_from_config",
    "run_openclaw_cli",
    "set_openclaw_agent_profiles",
    "set_openclaw_mcp_servers",
]
