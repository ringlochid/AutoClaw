from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoclaw.runtime.openclaw.discovery import (
    OpenClawHostSupportStatus,
    OpenClawResolvedHostState,
)
from autoclaw.runtime.openclaw.host_setup import (
    OpenClawAgentSummary,
    build_autoclaw_agent_entries,
    build_autoclaw_mcp_servers,
    load_host_agent_entries_from_config,
    load_host_agents_from_config,
    load_host_mcp_servers_from_config,
)
from autoclaw.runtime.openclaw.wrapper_contract import (
    desired_mcp_surfaces,
    desired_wrapper_profile,
    desired_wrapper_state,
    load_wrapper_material,
)
from autoclaw.runtime.openclaw.wrapper_contract import (
    desired_operator_contract as build_desired_operator_contract,
)


@dataclass(frozen=True)
class OpenClawIntegrationState:
    worker_agent_id: str
    operator_agent_id: str
    host_agents: tuple[OpenClawAgentSummary, ...]
    is_worker_agent_present: bool
    is_operator_agent_present: bool
    is_shared_agent_selection: bool
    agent_profile_drift: dict[str, bool]
    mcp_servers_present: dict[str, bool]
    mcp_server_drift: dict[str, bool]
    is_wrapper_state_present: bool
    is_wrapper_profile_present: bool
    is_wrapper_operator_contract_present: bool
    is_wrapper_mcp_surfaces_present: bool
    is_wrapper_state_drift: bool
    is_wrapper_material_drift: bool


def build_host_state_payload(
    *,
    host_state: OpenClawResolvedHostState,
    integration_state: OpenClawIntegrationState,
    wrapper_path: Path,
    compatibility: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "ok": openclaw_integration_ok(host_state, integration_state, compatibility),
        "support_status": host_state.support_status,
        "reason": host_state.reason,
        "binary_found": host_state.binary_found,
        "binary_path": host_state.binary_path,
        "config_path": host_state.config_path,
        "config_exists": host_state.config_exists,
        "base_url": host_state.base_url,
        "ws_url": host_state.ws_url,
        "loopback": host_state.loopback,
        "auth_mode": host_state.auth_mode,
        "effective_auth": host_state.effective_auth,
        "token_available": host_state.token_available,
        "password_available": host_state.password_available,
        "unresolved_secret_ref_fields": list(host_state.unresolved_secret_ref_fields),
        "worker_agent_id": integration_state.worker_agent_id,
        "operator_agent_id": integration_state.operator_agent_id,
        "host_agents": [
            {
                "id": agent.id,
                "is_default": agent.is_default,
                "name": agent.name,
            }
            for agent in integration_state.host_agents
        ],
        "worker_agent_present": integration_state.is_worker_agent_present,
        "operator_agent_present": integration_state.is_operator_agent_present,
        "shared_agent_selection": integration_state.is_shared_agent_selection,
        "agent_profile_drift": integration_state.agent_profile_drift,
        "mcp_servers_present": integration_state.mcp_servers_present,
        "mcp_server_drift": integration_state.mcp_server_drift,
        "wrapper_state_path": str(wrapper_path),
        "wrapper_state_present": integration_state.is_wrapper_state_present,
        "wrapper_profile_present": integration_state.is_wrapper_profile_present,
        "wrapper_operator_contract_present": integration_state.is_wrapper_operator_contract_present,
        "wrapper_mcp_surfaces_present": integration_state.is_wrapper_mcp_surfaces_present,
        "wrapper_state_drift": integration_state.is_wrapper_state_drift,
        "wrapper_material_drift": integration_state.is_wrapper_material_drift,
        "compatibility": compatibility,
    }


def load_openclaw_integration_state(
    *,
    settings: Any,
    host_state: OpenClawResolvedHostState,
) -> OpenClawIntegrationState:
    host_agents = load_host_agents_from_config(host_state)
    host_agent_entries = load_host_agent_entries_from_config(host_state)
    actual_mcp_servers = load_host_mcp_servers_from_config(host_state)
    selected_operator_agent_id = settings.openclaw.operator_agent_id or settings.openclaw.agent_id
    is_shared_agent_selection = selected_operator_agent_id == settings.openclaw.agent_id
    desired_mcp_servers = build_autoclaw_mcp_servers(settings)
    desired_agent_entries = (
        build_autoclaw_agent_entries(
            host_state,
            worker_agent_id=settings.openclaw.agent_id,
            operator_agent_id=selected_operator_agent_id,
        )
        if not is_shared_agent_selection
        else {}
    )
    current_material = load_wrapper_material(settings.data_dir)
    current_state = current_material["state"]
    desired_state = desired_wrapper_state(settings=settings, host_state=host_state)
    desired_profile = desired_wrapper_profile(settings=settings, host_state=host_state)
    desired_operator_contract_payload = build_desired_operator_contract(
        operator_agent_id=settings.openclaw.operator_agent_id or None,
    )
    desired_surfaces = desired_mcp_surfaces()
    mcp_servers_present = {
        name: isinstance(actual_mcp_servers.get(name), dict) for name in desired_mcp_servers
    }
    mcp_server_drift = {
        name: actual_mcp_servers.get(name) != desired_server
        for name, desired_server in desired_mcp_servers.items()
    }
    agent_profile_drift = {
        settings.openclaw.agent_id: is_shared_agent_selection
        or host_agent_entries.get(settings.openclaw.agent_id)
        != desired_agent_entries.get(settings.openclaw.agent_id),
        selected_operator_agent_id: is_shared_agent_selection
        or host_agent_entries.get(selected_operator_agent_id)
        != desired_agent_entries.get(selected_operator_agent_id),
    }
    return OpenClawIntegrationState(
        worker_agent_id=settings.openclaw.agent_id,
        operator_agent_id=selected_operator_agent_id,
        host_agents=host_agents,
        is_worker_agent_present=_find_agent(host_agents, settings.openclaw.agent_id) is not None,
        is_operator_agent_present=_find_agent(
            host_agents,
            selected_operator_agent_id,
        )
        is not None,
        is_shared_agent_selection=is_shared_agent_selection,
        agent_profile_drift=agent_profile_drift,
        mcp_servers_present=mcp_servers_present,
        mcp_server_drift=mcp_server_drift,
        is_wrapper_state_present=current_material["state"] is not None,
        is_wrapper_profile_present=current_material["profile"] is not None,
        is_wrapper_operator_contract_present=current_material["operator_contract"] is not None,
        is_wrapper_mcp_surfaces_present=current_material["mcp_surfaces"] is not None,
        is_wrapper_state_drift=current_state != desired_state,
        is_wrapper_material_drift=(
            current_material["profile"] != desired_profile
            or current_material["operator_contract"] != desired_operator_contract_payload
            or current_material["mcp_surfaces"] != desired_surfaces
        ),
    )


def openclaw_integration_ok(
    host_state: OpenClawResolvedHostState,
    integration_state: OpenClawIntegrationState,
    compatibility: dict[str, Any] | None,
) -> bool:
    return (
        _support_ok(host_state)
        and compatibility is not None
        and integration_state.is_worker_agent_present
        and integration_state.is_operator_agent_present
        and not integration_state.is_shared_agent_selection
        and not any(integration_state.agent_profile_drift.values())
        and not integration_state.is_wrapper_state_drift
        and not integration_state.is_wrapper_material_drift
        and not any(integration_state.mcp_server_drift.values())
        and all(integration_state.mcp_servers_present.values())
    )


def _support_ok(host_state: OpenClawResolvedHostState) -> bool:
    return (
        host_state.binary_found and host_state.support_status == OpenClawHostSupportStatus.SUPPORTED
    )


def _find_agent(
    agents: tuple[OpenClawAgentSummary, ...],
    agent_id: str,
) -> OpenClawAgentSummary | None:
    for agent in agents:
        if agent.id == agent_id:
            return agent
    return None


__all__ = [
    "OpenClawIntegrationState",
    "build_host_state_payload",
    "load_openclaw_integration_state",
    "openclaw_integration_ok",
]
