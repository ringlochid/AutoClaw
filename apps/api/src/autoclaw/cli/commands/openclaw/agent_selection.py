from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autoclaw.cli.support import command_env
from autoclaw.cli.terminal.note import note
from autoclaw.cli.terminal.prompts import SelectOption, select
from autoclaw.cli.terminal.theme import rich_enabled
from autoclaw.config import load_settings
from autoclaw.runtime.openclaw.discovery import OpenClawResolvedHostState
from autoclaw.runtime.openclaw.host_setup import (
    AUTOCLAW_OPERATOR_AGENT_ID,
    AUTOCLAW_WORKER_AGENT_ID,
    OpenClawAgentSummary,
    bootstrap_openclaw_agent,
    default_openclaw_agent_workspace,
    list_openclaw_agents,
)

_BOOTSTRAP_WORKER_SELECTION = "__bootstrap_autoclaw_worker__"
_BOOTSTRAP_OPERATOR_SELECTION = "__bootstrap_autoclaw_operator__"


@dataclass(frozen=True)
class OpenClawAgentSelection:
    worker_agent_id: str
    operator_agent_id: str
    is_worker_bootstrapped: bool
    is_operator_bootstrapped: bool
    available_agents: tuple[OpenClawAgentSummary, ...]


def resolve_openclaw_agent_selection(
    *,
    config_path: Path,
    host_state: OpenClawResolvedHostState,
    is_non_interactive: bool,
) -> OpenClawAgentSelection:
    return _resolve_openclaw_agent_selection(
        config_path=config_path,
        host_state=host_state,
        is_non_interactive=is_non_interactive,
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
    is_rich = rich_enabled()
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
            is_rich=is_rich,
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


def _resolve_noninteractive_selection(
    *,
    host_state: OpenClawResolvedHostState,
    available_agents: tuple[OpenClawAgentSummary, ...],
    configured_worker_agent_id: str,
    configured_operator_agent_id: str,
) -> OpenClawAgentSelection:
    selected_worker_agent_id = _preferred_or_explicit_agent_id(
        available_agents,
        configured_worker_agent_id,
        AUTOCLAW_WORKER_AGENT_ID,
    )
    bootstrapped_worker = False
    bootstrapped_operator = False
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
        configured_operator_agent_id=configured_operator_agent_id,
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
        is_worker_bootstrapped=bootstrapped_worker,
        is_operator_bootstrapped=bootstrapped_operator,
        available_agents=available_agents,
    )


def _resolve_interactive_selection(
    *,
    host_state: OpenClawResolvedHostState,
    available_agents: tuple[OpenClawAgentSummary, ...],
) -> OpenClawAgentSelection:
    selected_worker_selection = _select_worker_agent_interactively(
        agents=available_agents,
    )
    bootstrapped_worker = False
    bootstrapped_operator = False
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
        is_worker_bootstrapped=bootstrapped_worker,
        is_operator_bootstrapped=bootstrapped_operator,
        available_agents=available_agents,
    )


def _resolve_openclaw_agent_selection(
    *,
    config_path: Path,
    host_state: OpenClawResolvedHostState,
    is_non_interactive: bool,
) -> OpenClawAgentSelection:
    with command_env(config_path=config_path):
        settings = load_settings()

    available_agents = list_openclaw_agents(host_state)
    if not available_agents:
        bootstrap_openclaw_agent(
            host_state,
            agent_id=AUTOCLAW_WORKER_AGENT_ID,
            workspace_dir=_bootstrap_agent_workspace(AUTOCLAW_WORKER_AGENT_ID),
        )
        available_agents = list_openclaw_agents(host_state)

    if is_non_interactive:
        return _resolve_noninteractive_selection(
            host_state=host_state,
            available_agents=available_agents,
            configured_worker_agent_id=settings.openclaw.agent_id,
            configured_operator_agent_id=settings.openclaw.operator_agent_id,
        )
    return _resolve_interactive_selection(
        host_state=host_state,
        available_agents=available_agents,
    )


__all__ = [
    "OpenClawAgentSelection",
    "resolve_openclaw_agent_selection",
]
