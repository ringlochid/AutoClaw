from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.cli_commands.bootstrap import update_config_sections
from app.cli_commands.openclaw_support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli_support import coerce_path, command_env, print_json
from app.config import load_settings
from app.runtime.openclaw import build_openclaw_gateway_adapter
from app.runtime.openclaw.discovery import (
    OpenClawHostSupportStatus,
    OpenClawResolvedHostState,
)
from app.runtime.openclaw.host_setup import (
    AUTOCLAW_NODE_MCP_SERVER_NAME,
    AUTOCLAW_OPERATOR_AGENT_ID,
    AUTOCLAW_OPERATOR_MCP_SERVER_NAME,
    AUTOCLAW_WORKER_AGENT_ID,
    OpenClawAgentSummary,
    bootstrap_openclaw_agent,
    build_autoclaw_agent_entries,
    build_autoclaw_mcp_servers,
    default_openclaw_agent_workspace,
    gateway_bootstrap_needed,
    host_base_url_from_config,
    list_openclaw_agents,
    load_host_agent_entries_from_config,
    load_host_agents_from_config,
    load_host_mcp_servers_from_config,
    patch_openclaw_gateway_settings,
    resolved_gateway_bootstrap_values,
    set_openclaw_agent_profiles,
    set_openclaw_mcp_servers,
)
from app.runtime.openclaw.preflight import openclaw_preflight_report
from app.runtime.openclaw.wrapper_contract import (
    WRAPPER_CLIENT_MODE,
    WRAPPER_REQUIRED_ROLE,
    WRAPPER_REQUIRED_SCOPES,
    desired_mcp_surfaces,
    desired_wrapper_profile,
    desired_wrapper_state,
    load_wrapper_material,
    wrapper_state_path,
    write_wrapper_material,
)
from app.runtime.openclaw.wrapper_contract import (
    desired_operator_contract as build_desired_operator_contract,
)
from app.terminal.note import note
from app.terminal.prompts import SelectOption, select, text
from app.terminal.theme import accent, heading, rich_enabled, success, warn

_BOOTSTRAP_WORKER_SELECTION = "__bootstrap_autoclaw_worker__"
_BOOTSTRAP_OPERATOR_SELECTION = "__bootstrap_autoclaw_operator__"


@dataclass(frozen=True)
class OpenClawAgentSelection:
    worker_agent_id: str
    operator_agent_id: str
    bootstrapped_worker: bool
    bootstrapped_operator: bool
    available_agents: tuple[OpenClawAgentSummary, ...]


@dataclass(frozen=True)
class OpenClawIntegrationState:
    worker_agent_id: str
    operator_agent_id: str
    host_agents: tuple[OpenClawAgentSummary, ...]
    worker_agent_present: bool
    operator_agent_present: bool
    shared_agent_selection: bool
    agent_profile_drift: dict[str, bool]
    mcp_servers_present: dict[str, bool]
    mcp_server_drift: dict[str, bool]
    wrapper_state_present: bool
    wrapper_profile_present: bool
    wrapper_operator_contract_present: bool
    wrapper_mcp_surfaces_present: bool
    wrapper_state_drift: bool
    wrapper_material_drift: bool


@dataclass(frozen=True)
class WrapperStateResult:
    path: Path
    written: bool
    payload: dict[str, Any]
    material_paths: dict[str, Path]
    worker_agent_id: str
    operator_agent_id: str
    mcp_servers_written: tuple[str, ...]
    bootstrapped_worker: bool
    bootstrapped_operator: bool
    agent_profiles_written: tuple[str, ...]


async def _compatibility_payload(settings: Any) -> dict[str, Any] | None:
    adapter = build_openclaw_gateway_adapter(settings)
    compatibility = await adapter.check_compatibility()
    return compatibility.model_dump(mode="json")


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


def _default_agent_id(agents: tuple[OpenClawAgentSummary, ...]) -> str:
    for agent in agents:
        if agent.is_default:
            return agent.id
    return agents[0].id


def _preferred_agent_id(
    agents: tuple[OpenClawAgentSummary, ...],
    *preferred_ids: str,
) -> str:
    for preferred_id in preferred_ids:
        if preferred_id and _find_agent(agents, preferred_id) is not None:
            return preferred_id
    return _default_agent_id(agents)


def _preferred_or_explicit_agent_id(
    agents: tuple[OpenClawAgentSummary, ...],
    *preferred_ids: str,
) -> str:
    for preferred_id in preferred_ids:
        if preferred_id:
            return preferred_id
    return _default_agent_id(agents)


def _first_nonmatching_agent_id(
    agents: tuple[OpenClawAgentSummary, ...],
    excluded_agent_id: str,
) -> str | None:
    for agent in agents:
        if agent.id != excluded_agent_id:
            return agent.id
    return None


def _agent_label(agent: OpenClawAgentSummary) -> str:
    default_suffix = " (default)" if agent.is_default else ""
    if agent.name and agent.name != agent.id:
        return f"{agent.id}{default_suffix} ({agent.name})"
    return f"{agent.id}{default_suffix}"


def _dedicated_worker_option() -> SelectOption:
    return SelectOption(
        _BOOTSTRAP_WORKER_SELECTION,
        f"Set {AUTOCLAW_WORKER_AGENT_ID}",
        "Create or refresh the dedicated AutoClaw worker profile and use it.",
    )


def _dedicated_operator_option() -> SelectOption:
    return SelectOption(
        _BOOTSTRAP_OPERATOR_SELECTION,
        f"Set {AUTOCLAW_OPERATOR_AGENT_ID}",
        "Create or refresh the dedicated AutoClaw operator profile and use it.",
    )


def _interactive_existing_agents(
    agents: tuple[OpenClawAgentSummary, ...],
) -> tuple[OpenClawAgentSummary, ...]:
    return tuple(
        agent
        for agent in agents
        if agent.id not in {AUTOCLAW_WORKER_AGENT_ID, AUTOCLAW_OPERATOR_AGENT_ID}
    )


def _select_worker_agent_interactively(
    *,
    agents: tuple[OpenClawAgentSummary, ...],
) -> str:
    existing_agents = _interactive_existing_agents(agents)
    options = [
        SelectOption(
            agent.id,
            _agent_label(agent),
            "Use an existing OpenClaw agent for AutoClaw worker dispatch.",
        )
        for agent in existing_agents
    ]
    options.append(_dedicated_worker_option())
    return select(
        "Select the OpenClaw worker agent for AutoClaw.",
        options=options,
        default_index=len(options) - 1,
        title="AutoClaw OpenClaw worker",
    )


def _select_operator_agent_interactively(
    *,
    agents: tuple[OpenClawAgentSummary, ...],
    worker_agent_id: str,
) -> str:
    rich = rich_enabled()
    existing_agents = _interactive_existing_agents(agents)
    options = [
        SelectOption(
            agent.id,
            _agent_label(agent),
            "Use this OpenClaw agent for operator-facing AutoClaw MCP access.",
        )
        for agent in existing_agents
    ]
    options.append(_dedicated_operator_option())
    while True:
        selection = select(
            "Select the OpenClaw operator agent for AutoClaw.",
            options=options,
            default_index=len(options) - 1,
            title="AutoClaw OpenClaw operator",
        )
        if selection != worker_agent_id:
            return selection
        note(
            (
                "Choose a different operator agent than the selected worker, "
                "or use the dedicated AutoClaw operator slot."
            ),
            "Invalid input",
            rich=rich,
        )


def _bootstrap_agent_workspace(agent_id: str) -> Path:
    return default_openclaw_agent_workspace(agent_id)


def _ensure_agent_present(
    host_state: OpenClawResolvedHostState,
    agents: tuple[OpenClawAgentSummary, ...],
    *,
    agent_id: str,
) -> tuple[tuple[OpenClawAgentSummary, ...], bool]:
    if _find_agent(agents, agent_id) is not None:
        return agents, False
    bootstrap_openclaw_agent(
        host_state,
        agent_id=agent_id,
        workspace_dir=_bootstrap_agent_workspace(agent_id),
    )
    return list_openclaw_agents(host_state), True


def _noninteractive_operator_agent_id(
    *,
    agents: tuple[OpenClawAgentSummary, ...],
    worker_agent_id: str,
    configured_operator_agent_id: str,
) -> str:
    if configured_operator_agent_id and configured_operator_agent_id != worker_agent_id:
        return configured_operator_agent_id
    if worker_agent_id != AUTOCLAW_OPERATOR_AGENT_ID:
        return AUTOCLAW_OPERATOR_AGENT_ID
    fallback = _first_nonmatching_agent_id(agents, worker_agent_id)
    return fallback or AUTOCLAW_WORKER_AGENT_ID


def _resolve_openclaw_agent_selection(
    *,
    config_path: Path,
    host_state: OpenClawResolvedHostState,
    non_interactive: bool,
) -> OpenClawAgentSelection:
    with command_env(config_path=config_path):
        settings = load_settings()

    available_agents = list_openclaw_agents(host_state)
    bootstrapped_worker = False
    bootstrapped_operator = False
    if not available_agents:
        bootstrap_openclaw_agent(
            host_state,
            agent_id=AUTOCLAW_WORKER_AGENT_ID,
            workspace_dir=_bootstrap_agent_workspace(AUTOCLAW_WORKER_AGENT_ID),
        )
        available_agents = list_openclaw_agents(host_state)
        bootstrapped_worker = True

    if non_interactive:
        selected_worker_agent_id = _preferred_or_explicit_agent_id(
            available_agents,
            settings.openclaw.agent_id,
            AUTOCLAW_WORKER_AGENT_ID,
        )
        if _find_agent(available_agents, selected_worker_agent_id) is None:
            bootstrap_openclaw_agent(
                host_state,
                agent_id=selected_worker_agent_id,
                workspace_dir=_bootstrap_agent_workspace(selected_worker_agent_id),
            )
            available_agents = list_openclaw_agents(host_state)
            bootstrapped_worker = True
        selected_operator_agent_id = _noninteractive_operator_agent_id(
            agents=available_agents,
            worker_agent_id=selected_worker_agent_id,
            configured_operator_agent_id=settings.openclaw.operator_agent_id,
        )
        if _find_agent(available_agents, selected_operator_agent_id) is None:
            bootstrap_openclaw_agent(
                host_state,
                agent_id=selected_operator_agent_id,
                workspace_dir=_bootstrap_agent_workspace(selected_operator_agent_id),
            )
            available_agents = list_openclaw_agents(host_state)
            bootstrapped_operator = True
        return OpenClawAgentSelection(
            worker_agent_id=selected_worker_agent_id,
            operator_agent_id=selected_operator_agent_id,
            bootstrapped_worker=bootstrapped_worker,
            bootstrapped_operator=bootstrapped_operator,
            available_agents=available_agents,
        )

    selected_worker_selection = _select_worker_agent_interactively(
        agents=available_agents,
    )
    if selected_worker_selection == _BOOTSTRAP_WORKER_SELECTION:
        available_agents, bootstrapped_worker = _ensure_agent_present(
            host_state,
            agent_id=AUTOCLAW_WORKER_AGENT_ID,
            agents=available_agents,
        )
        selected_worker_agent_id = AUTOCLAW_WORKER_AGENT_ID
    else:
        selected_worker_agent_id = selected_worker_selection

    selected_operator_selection = _select_operator_agent_interactively(
        agents=available_agents,
        worker_agent_id=selected_worker_agent_id,
    )
    if selected_operator_selection == _BOOTSTRAP_OPERATOR_SELECTION:
        available_agents, bootstrapped_operator = _ensure_agent_present(
            host_state,
            agent_id=AUTOCLAW_OPERATOR_AGENT_ID,
            agents=available_agents,
        )
        selected_operator_agent_id = AUTOCLAW_OPERATOR_AGENT_ID
    else:
        selected_operator_agent_id = selected_operator_selection
    return OpenClawAgentSelection(
        worker_agent_id=selected_worker_agent_id,
        operator_agent_id=selected_operator_agent_id,
        bootstrapped_worker=bootstrapped_worker,
        bootstrapped_operator=bootstrapped_operator,
        available_agents=available_agents,
    )


def _load_integration_state(
    *,
    settings: Any,
    host_state: OpenClawResolvedHostState,
) -> OpenClawIntegrationState:
    host_agents = load_host_agents_from_config(host_state)
    host_agent_entries = load_host_agent_entries_from_config(host_state)
    actual_mcp_servers = load_host_mcp_servers_from_config(host_state)
    selected_operator_agent_id = settings.openclaw.operator_agent_id or settings.openclaw.agent_id
    shared_agent_selection = selected_operator_agent_id == settings.openclaw.agent_id
    desired_mcp_servers = build_autoclaw_mcp_servers(settings)
    desired_agent_entries = (
        build_autoclaw_agent_entries(
            host_state,
            worker_agent_id=settings.openclaw.agent_id,
            operator_agent_id=selected_operator_agent_id,
        )
        if not shared_agent_selection
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
        settings.openclaw.agent_id: shared_agent_selection
        or host_agent_entries.get(settings.openclaw.agent_id)
        != desired_agent_entries.get(settings.openclaw.agent_id),
        selected_operator_agent_id: shared_agent_selection
        or host_agent_entries.get(selected_operator_agent_id)
        != desired_agent_entries.get(selected_operator_agent_id),
    }
    return OpenClawIntegrationState(
        worker_agent_id=settings.openclaw.agent_id,
        operator_agent_id=selected_operator_agent_id,
        host_agents=host_agents,
        worker_agent_present=_find_agent(host_agents, settings.openclaw.agent_id) is not None,
        operator_agent_present=_find_agent(
            host_agents,
            selected_operator_agent_id,
        )
        is not None,
        shared_agent_selection=shared_agent_selection,
        agent_profile_drift=agent_profile_drift,
        mcp_servers_present=mcp_servers_present,
        mcp_server_drift=mcp_server_drift,
        wrapper_state_present=current_material["state"] is not None,
        wrapper_profile_present=current_material["profile"] is not None,
        wrapper_operator_contract_present=current_material["operator_contract"] is not None,
        wrapper_mcp_surfaces_present=current_material["mcp_surfaces"] is not None,
        wrapper_state_drift=current_state != desired_state,
        wrapper_material_drift=(
            current_material["profile"] != desired_profile
            or current_material["operator_contract"] != desired_operator_contract_payload
            or current_material["mcp_surfaces"] != desired_surfaces
        ),
    )


def _integration_ok(
    host_state: OpenClawResolvedHostState,
    integration_state: OpenClawIntegrationState,
    compatibility: dict[str, Any] | None,
) -> bool:
    return (
        _support_ok(host_state)
        and compatibility is not None
        and integration_state.worker_agent_present
        and integration_state.operator_agent_present
        and not integration_state.shared_agent_selection
        and not any(integration_state.agent_profile_drift.values())
        and not integration_state.wrapper_state_drift
        and not integration_state.wrapper_material_drift
        and not any(integration_state.mcp_server_drift.values())
        and all(integration_state.mcp_servers_present.values())
    )


def _host_state_payload(
    *,
    host_state: OpenClawResolvedHostState,
    integration_state: OpenClawIntegrationState,
    wrapper_path: Path,
    compatibility: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "ok": _integration_ok(host_state, integration_state, compatibility),
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
        "worker_agent_present": integration_state.worker_agent_present,
        "operator_agent_present": integration_state.operator_agent_present,
        "shared_agent_selection": integration_state.shared_agent_selection,
        "agent_profile_drift": integration_state.agent_profile_drift,
        "mcp_servers_present": integration_state.mcp_servers_present,
        "mcp_server_drift": integration_state.mcp_server_drift,
        "wrapper_state_path": str(wrapper_path),
        "wrapper_state_present": integration_state.wrapper_state_present,
        "wrapper_profile_present": integration_state.wrapper_profile_present,
        "wrapper_operator_contract_present": integration_state.wrapper_operator_contract_present,
        "wrapper_mcp_surfaces_present": integration_state.wrapper_mcp_surfaces_present,
        "wrapper_state_drift": integration_state.wrapper_state_drift,
        "wrapper_material_drift": integration_state.wrapper_material_drift,
        "compatibility": compatibility,
    }


def _resolve_gateway_port_from_url(base_url: str) -> int | None:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
    except ValueError:
        return None
    return parsed.port


def _effective_openclaw_base_url(gateway_port: int | None) -> str | None:
    if gateway_port is None:
        return None
    return f"http://127.0.0.1:{gateway_port}"


def _persist_openclaw_base_url(
    config_path: Path,
    *,
    openclaw_base_url: str | None,
) -> None:
    if openclaw_base_url is None:
        return
    update_config_sections(
        config_path,
        section_updates={"openclaw": {"base_url": openclaw_base_url}},
    )


def _interactive_gateway_bootstrap_values(
    *,
    settings: Any,
    host_state: OpenClawResolvedHostState,
) -> tuple[str, int]:
    default_port = (
        _resolve_gateway_port_from_url(settings.openclaw.base_url)
        or _resolve_gateway_port_from_url(host_base_url_from_config(host_state) or "")
        or 18789
    )
    gateway_port = int(
        text(
            "OpenClaw gateway port",
            default=str(default_port),
            hint="AutoClaw can patch the local OpenClaw gateway config to token-auth on loopback.",
        )
    )
    gateway_token = text(
        "OpenClaw gateway token",
        default=settings.openclaw.gateway_token or None,
        sensitive=True,
    )
    return gateway_token, gateway_port


def bootstrap_openclaw_gateway_access(
    *,
    config_path: Path,
    non_interactive: bool,
    gateway_token: str | None = None,
    gateway_port: int | None = None,
    openclaw_base_url: str | None = None,
) -> OpenClawResolvedHostState:
    with command_env(config_path=config_path, openclaw_base_url=openclaw_base_url):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
    if not gateway_bootstrap_needed(host_state):
        return host_state

    if non_interactive:
        if gateway_token is None and not settings.openclaw.gateway_token:
            raise RuntimeError(
                "OpenClaw gateway token is required for non-interactive gateway bootstrap"
            )
        resolved_token, resolved_port = resolved_gateway_bootstrap_values(
            settings=settings,
            host_state=host_state,
            gateway_token=gateway_token or settings.openclaw.gateway_token,
            gateway_port=gateway_port,
        )
    else:
        resolved_token, resolved_port = _interactive_gateway_bootstrap_values(
            settings=settings,
            host_state=host_state,
        )

    patch_openclaw_gateway_settings(
        host_state,
        gateway_port=resolved_port,
        gateway_token=resolved_token,
    )
    update_config_sections(
        config_path,
        section_updates={
            "openclaw": {
                "base_url": f"http://127.0.0.1:{resolved_port}",
                "gateway_token": resolved_token,
                "config_path": host_state.config_path,
                "binary_path": host_state.binary_path,
            }
        },
    )
    with command_env(config_path=config_path):
        refreshed_settings = load_settings()
        return openclaw_preflight_report(refreshed_settings.openclaw)


def _openclaw_config_updates(
    *,
    settings: Any,
    host_state: OpenClawResolvedHostState,
    selection: OpenClawAgentSelection,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "base_url": settings.openclaw.base_url,
        "timeout_ms": settings.openclaw.timeout_ms,
        "agent_id": selection.worker_agent_id,
        "operator_agent_id": selection.operator_agent_id,
    }
    if settings.openclaw.binary_path:
        payload["binary_path"] = settings.openclaw.binary_path
    elif host_state.binary_found and host_state.binary_path:
        payload["binary_path"] = host_state.binary_path
    if settings.openclaw.config_path:
        payload["config_path"] = settings.openclaw.config_path
    elif host_state.config_path:
        payload["config_path"] = host_state.config_path
    for key in ("gateway_token", "gateway_password"):
        value = getattr(settings.openclaw, key, "")
        if value:
            payload[key] = value
    return payload


def _print_host_state(payload: dict[str, Any], *, rich: bool) -> None:
    support = payload["support_status"]
    label = success(support, rich=rich) if payload["ok"] else warn(support, rich=rich)
    print(heading("AutoClaw openclaw check", rich=rich))
    print(f"support: {label}")
    if payload["reason"]:
        print(f"reason: {warn(str(payload['reason']), rich=rich)}")
    print(f"binary: {accent(str(payload['binary_path'] or 'not found'), rich=rich)}")
    print(f"config: {accent(str(payload['config_path']), rich=rich)}")
    print(f"base url: {accent(str(payload['base_url']), rich=rich)}")
    print(f"worker agent: {payload['worker_agent_id']}")
    print(f"operator agent: {payload['operator_agent_id']}")
    operator_present = payload["mcp_servers_present"][AUTOCLAW_OPERATOR_MCP_SERVER_NAME]
    node_present = payload["mcp_servers_present"][AUTOCLAW_NODE_MCP_SERVER_NAME]
    print(
        "mcp servers: "
        f"{AUTOCLAW_OPERATOR_MCP_SERVER_NAME}={operator_present}, "
        f"{AUTOCLAW_NODE_MCP_SERVER_NAME}={node_present}"
    )
    print(f"agent profile drift: {payload['agent_profile_drift']}")
    print(f"wrapper state: {payload['wrapper_state_path']}")
    if payload["shared_agent_selection"]:
        print(warn("worker and operator must use separate OpenClaw agents", rich=rich))


async def inspect_openclaw_integration(config_path: Path) -> dict[str, Any]:
    with command_env(config_path=config_path):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
        wrapper_path = wrapper_state_path(settings.data_dir)
        compatibility = None
        if _support_ok(host_state):
            compatibility = await _compatibility_payload(settings)
        integration_state = _load_integration_state(settings=settings, host_state=host_state)
    return _host_state_payload(
        host_state=host_state,
        integration_state=integration_state,
        wrapper_path=wrapper_path,
        compatibility=compatibility,
    )


async def cmd_openclaw_check(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    payload = await inspect_openclaw_integration(config_path)
    if args.json:
        print_json(payload)
    else:
        _print_host_state(payload, rich=rich_enabled(args))
    return 0 if payload["ok"] else 1


async def reconcile_openclaw_setup(
    config_path: Path,
    *,
    non_interactive: bool,
    openclaw_base_url: str | None = None,
    openclaw_gateway_token: str | None = None,
) -> WrapperStateResult:
    with command_env(
        config_path=config_path,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=openclaw_gateway_token,
    ):
        initial_settings = load_settings()
        host_state = openclaw_preflight_report(initial_settings.openclaw)
        if not _support_ok(host_state):
            raise RuntimeError(host_state.reason or "unsupported OpenClaw host state")

    selection = _resolve_openclaw_agent_selection(
        config_path=config_path,
        host_state=host_state,
        non_interactive=non_interactive,
    )
    update_config_sections(
        config_path,
        section_updates={
            "openclaw": _openclaw_config_updates(
                settings=initial_settings,
                host_state=host_state,
                selection=selection,
            )
        },
    )

    with command_env(
        config_path=config_path,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=openclaw_gateway_token,
    ):
        settings = load_settings()
        desired_servers = build_autoclaw_mcp_servers(settings)
        agent_profiles_written = set_openclaw_agent_profiles(
            host_state,
            worker_agent_id=selection.worker_agent_id,
            operator_agent_id=selection.operator_agent_id,
        )
        mcp_servers_written = set_openclaw_mcp_servers(
            host_state,
            servers=desired_servers,
        )
        payload = desired_wrapper_state(settings=settings, host_state=host_state)
        paths = write_wrapper_material(
            data_dir=settings.data_dir,
            state=payload,
            profile=desired_wrapper_profile(settings=settings, host_state=host_state),
            operator_contract=build_desired_operator_contract(
                operator_agent_id=settings.openclaw.operator_agent_id or None,
            ),
            mcp_surfaces=desired_mcp_surfaces(),
        )
    return WrapperStateResult(
        path=paths["state"],
        written=True,
        payload=payload,
        material_paths=paths,
        worker_agent_id=selection.worker_agent_id,
        operator_agent_id=selection.operator_agent_id,
        mcp_servers_written=mcp_servers_written,
        bootstrapped_worker=selection.bootstrapped_worker,
        bootstrapped_operator=selection.bootstrapped_operator,
        agent_profiles_written=agent_profiles_written,
    )


async def write_wrapper_defaults(config_path: Path) -> WrapperStateResult:
    return await reconcile_openclaw_setup(config_path, non_interactive=True)


async def cmd_openclaw_setup(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    effective_base_url = _effective_openclaw_base_url(
        getattr(args, "openclaw_gateway_port", None)
    )
    bootstrap_openclaw_gateway_access(
        config_path=config_path,
        non_interactive=bool(getattr(args, "non_interactive", False)),
        gateway_token=getattr(args, "openclaw_gateway_token", None),
        gateway_port=getattr(args, "openclaw_gateway_port", None),
        openclaw_base_url=effective_base_url,
    )
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    if preflight.host_state.support_status != "supported":
        return emit_openclaw_preflight_failure(
            command_name="AutoClaw openclaw setup",
            args=args,
            openclaw_payload=preflight.payload,
            stopped_before="stopped before wrapper setup",
        )
    _persist_openclaw_base_url(
        config_path,
        openclaw_base_url=effective_base_url,
    )
    result = await reconcile_openclaw_setup(
        config_path,
        non_interactive=bool(getattr(args, "non_interactive", False)),
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    payload = {
        "ok": True,
        "path": str(result.path),
        "written": result.written,
        "state": result.payload,
        "worker_agent_id": result.worker_agent_id,
        "operator_agent_id": result.operator_agent_id,
        "bootstrapped_worker": result.bootstrapped_worker,
        "bootstrapped_operator": result.bootstrapped_operator,
        "agent_profiles_written": list(result.agent_profiles_written),
        "mcp_servers_written": list(result.mcp_servers_written),
        "material_paths": {key: str(value) for key, value in result.material_paths.items()},
    }
    if args.json:
        print_json(payload)
    else:
        rich = rich_enabled(args)
        print(heading("AutoClaw openclaw setup", rich=rich))
        print(f"worker agent: {accent(result.worker_agent_id, rich=rich)}")
        print(f"operator agent: {accent(result.operator_agent_id, rich=rich)}")
        print(f"wrote wrapper state: {accent(str(result.path), rich=rich)}")
    return 0


async def cmd_openclaw_doctor(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    effective_base_url = _effective_openclaw_base_url(
        getattr(args, "openclaw_gateway_port", None)
    )
    fixed = False
    if args.fix:
        bootstrap_openclaw_gateway_access(
            config_path=config_path,
            non_interactive=True,
            gateway_token=getattr(args, "openclaw_gateway_token", None),
            gateway_port=getattr(args, "openclaw_gateway_port", None),
            openclaw_base_url=effective_base_url,
        )
        preflight = collect_openclaw_preflight(
            config_path=config_path,
            openclaw_base_url=effective_base_url,
            openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
        )
        if preflight.host_state.support_status != "supported":
            return emit_openclaw_preflight_failure(
                command_name="AutoClaw openclaw doctor",
                args=args,
                openclaw_payload=preflight.payload,
                stopped_before="stopped before wrapper repair",
            )
        _persist_openclaw_base_url(
            config_path,
            openclaw_base_url=effective_base_url,
        )
        await reconcile_openclaw_setup(
            config_path,
            non_interactive=True,
            openclaw_base_url=effective_base_url,
            openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
        )
        fixed = True
    with command_env(
        config_path=config_path,
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    ):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
        state_path = wrapper_state_path(settings.data_dir)
        integration_state = _load_integration_state(settings=settings, host_state=host_state)
    ok = _integration_ok(host_state, integration_state, compatibility={})
    payload = {
        "ok": ok,
        "support_status": host_state.support_status,
        "reason": host_state.reason,
        "path": str(state_path),
        "worker_agent_id": integration_state.worker_agent_id,
        "operator_agent_id": integration_state.operator_agent_id,
        "worker_agent_present": integration_state.worker_agent_present,
        "operator_agent_present": integration_state.operator_agent_present,
        "shared_agent_selection": integration_state.shared_agent_selection,
        "agent_profile_drift": integration_state.agent_profile_drift,
        "mcp_server_drift": integration_state.mcp_server_drift,
        "wrapper_state_drift": integration_state.wrapper_state_drift,
        "wrapper_material_drift": integration_state.wrapper_material_drift,
        "fixed": fixed,
    }
    if args.json:
        print_json(payload)
    else:
        rich = rich_enabled(args)
        label = success("ok", rich=rich) if ok else warn("attention needed", rich=rich)
        print(heading("AutoClaw openclaw doctor", rich=rich))
        print(f"status: {label}")
        print(f"path: {accent(str(state_path), rich=rich)}")
        print(f"worker agent: {integration_state.worker_agent_id}")
        print(f"operator agent: {integration_state.operator_agent_id}")
        print(f"agent profile drift: {integration_state.agent_profile_drift}")
        print(f"wrapper drift: {integration_state.wrapper_state_drift}")
        print(f"material drift: {integration_state.wrapper_material_drift}")
        print(f"mcp drift: {any(integration_state.mcp_server_drift.values())}")
        if payload["reason"]:
            print(f"reason: {warn(str(payload['reason']), rich=rich)}")
    return 0 if ok else 1


__all__ = [
    "WRAPPER_CLIENT_MODE",
    "WRAPPER_REQUIRED_ROLE",
    "WRAPPER_REQUIRED_SCOPES",
    "cmd_openclaw_check",
    "cmd_openclaw_doctor",
    "cmd_openclaw_setup",
    "desired_wrapper_state",
    "inspect_openclaw_integration",
    "reconcile_openclaw_setup",
    "wrapper_state_path",
    "write_wrapper_defaults",
]
