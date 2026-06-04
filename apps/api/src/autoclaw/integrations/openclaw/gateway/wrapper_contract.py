from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autoclaw.config import Settings
from autoclaw.integrations.openclaw.gateway.discovery import OpenClawResolvedHostState
from autoclaw.integrations.openclaw.gateway.host_setup import (
    AUTOCLAW_NODE_MCP_SERVER_NAME,
    AUTOCLAW_OPERATOR_MCP_SERVER_NAME,
)

WRAPPER_STATE_FILENAME = "wrapper-state.json"
WRAPPER_PROFILE_FILENAME = "autoclaw-worker.profile.json"
WRAPPER_OPERATOR_CONTRACT_FILENAME = "operator-contract.json"
WRAPPER_MCP_SURFACES_FILENAME = "mcp-surfaces.json"
WRAPPER_CLIENT_MODE = "webchat"
WRAPPER_REQUIRED_ROLE = "operator"
WRAPPER_REQUIRED_SCOPES = ("operator.read", "operator.write")


def desired_wrapper_state(
    *,
    settings: Settings,
    host_state: OpenClawResolvedHostState,
) -> dict[str, Any]:
    return {
        "agent_id": settings.openclaw.agent_id,
        "operator_agent_id": settings.openclaw.operator_agent_id,
        "base_url": host_state.base_url,
        "config_path": host_state.config_path,
        "binary_path": host_state.binary_path,
        "client_mode": WRAPPER_CLIENT_MODE,
        "required_role": WRAPPER_REQUIRED_ROLE,
        "required_scopes": list(WRAPPER_REQUIRED_SCOPES),
    }


def desired_wrapper_profile(
    *,
    settings: Settings,
    host_state: OpenClawResolvedHostState,
) -> dict[str, Any]:
    return {
        "agent_id": settings.openclaw.agent_id,
        "operator_agent_id": settings.openclaw.operator_agent_id,
        "session_transport": "openclaw-gateway",
        "channel": WRAPPER_CLIENT_MODE,
        "base_url": host_state.base_url,
        "ws_url": host_state.ws_url,
        "loopback": host_state.loopback,
    }


def desired_operator_contract(*, operator_agent_id: str | None = None) -> dict[str, Any]:
    payload = {
        "role": WRAPPER_REQUIRED_ROLE,
        "required_scopes": list(WRAPPER_REQUIRED_SCOPES),
        "client_mode": WRAPPER_CLIENT_MODE,
    }
    if operator_agent_id:
        payload["operator_agent_id"] = operator_agent_id
    return payload


def desired_mcp_surfaces() -> dict[str, Any]:
    return {
        "canonical_surfaces": ["operator MCP", "node MCP"],
        "wrapper_owned": ["operator-contract", "autoclaw-worker-profile"],
        "server_names": [AUTOCLAW_OPERATOR_MCP_SERVER_NAME, AUTOCLAW_NODE_MCP_SERVER_NAME],
    }


def load_wrapper_material(data_dir: Path) -> dict[str, dict[str, Any] | None]:
    return {
        "state": load_wrapper_state(wrapper_state_path(data_dir)),
        "profile": load_wrapper_state(wrapper_profile_path(data_dir)),
        "operator_contract": load_wrapper_state(wrapper_operator_contract_path(data_dir)),
        "mcp_surfaces": load_wrapper_state(wrapper_mcp_surfaces_path(data_dir)),
    }


def write_wrapper_material(
    *,
    data_dir: Path,
    state: dict[str, Any],
    profile: dict[str, Any],
    operator_contract: dict[str, Any],
    mcp_surfaces: dict[str, Any],
) -> dict[str, Path]:
    state_path = wrapper_state_path(data_dir)
    profile_path = wrapper_profile_path(data_dir)
    operator_contract_path = wrapper_operator_contract_path(data_dir)
    mcp_surfaces_path = wrapper_mcp_surfaces_path(data_dir)
    write_wrapper_state(state_path, state)
    write_wrapper_state(profile_path, profile)
    write_wrapper_state(operator_contract_path, operator_contract)
    write_wrapper_state(mcp_surfaces_path, mcp_surfaces)
    return {
        "state": state_path,
        "profile": profile_path,
        "operator_contract": operator_contract_path,
        "mcp_surfaces": mcp_surfaces_path,
    }


def wrapper_state_path(data_dir: Path) -> Path:
    return data_dir / "openclaw" / WRAPPER_STATE_FILENAME


def wrapper_profile_path(data_dir: Path) -> Path:
    return data_dir / "openclaw" / WRAPPER_PROFILE_FILENAME


def wrapper_operator_contract_path(data_dir: Path) -> Path:
    return data_dir / "openclaw" / WRAPPER_OPERATOR_CONTRACT_FILENAME


def wrapper_mcp_surfaces_path(data_dir: Path) -> Path:
    return data_dir / "openclaw" / WRAPPER_MCP_SURFACES_FILENAME


def load_wrapper_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_wrapper_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "WRAPPER_CLIENT_MODE",
    "WRAPPER_MCP_SURFACES_FILENAME",
    "WRAPPER_OPERATOR_CONTRACT_FILENAME",
    "WRAPPER_PROFILE_FILENAME",
    "WRAPPER_REQUIRED_ROLE",
    "WRAPPER_REQUIRED_SCOPES",
    "desired_mcp_surfaces",
    "desired_operator_contract",
    "desired_wrapper_profile",
    "desired_wrapper_state",
    "load_wrapper_material",
    "load_wrapper_state",
    "wrapper_mcp_surfaces_path",
    "wrapper_operator_contract_path",
    "wrapper_profile_path",
    "wrapper_state_path",
    "write_wrapper_material",
    "write_wrapper_state",
]
