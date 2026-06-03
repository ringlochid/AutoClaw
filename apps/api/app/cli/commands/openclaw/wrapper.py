from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.cli.commands.bootstrap import update_config_sections
from app.cli.commands.openclaw.agent_selection import (
    OpenClawAgentSelection,
    resolve_openclaw_agent_selection,
)
from app.cli.commands.openclaw.gateway_bootstrap import (
    bootstrap_openclaw_gateway_access,
    build_effective_openclaw_base_url,
    persist_openclaw_base_url,
)
from app.cli.commands.openclaw.integration_state import (
    build_host_state_payload,
    load_openclaw_integration_state,
    openclaw_integration_ok,
)
from app.cli.commands.openclaw.support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli.terminal.theme import accent, heading, rich_enabled, success, warn
from app.cli_support import coerce_path, command_env, print_json
from app.config import load_settings
from app.runtime.openclaw import build_openclaw_gateway_adapter
from app.runtime.openclaw.discovery import (
    OpenClawHostSupportStatus,
    OpenClawResolvedHostState,
)
from app.runtime.openclaw.host_setup import (
    AUTOCLAW_NODE_MCP_SERVER_NAME,
    AUTOCLAW_OPERATOR_MCP_SERVER_NAME,
    build_autoclaw_mcp_servers,
    set_openclaw_agent_profiles,
    set_openclaw_mcp_servers,
)
from app.runtime.openclaw.preflight import openclaw_preflight_report
from app.runtime.openclaw.wrapper_contract import (
    desired_mcp_surfaces,
    desired_wrapper_profile,
    desired_wrapper_state,
    wrapper_state_path,
    write_wrapper_material,
)
from app.runtime.openclaw.wrapper_contract import (
    desired_operator_contract as build_desired_operator_contract,
)


@dataclass(frozen=True)
class WrapperStateResult:
    path: Path
    is_written: bool
    payload: dict[str, Any]
    material_paths: dict[str, Path]
    worker_agent_id: str
    operator_agent_id: str
    mcp_servers_written: tuple[str, ...]
    is_worker_bootstrapped: bool
    is_operator_bootstrapped: bool
    agent_profiles_written: tuple[str, ...]


async def cmd_openclaw_doctor(args: argparse.Namespace) -> int:
    return await _cmd_openclaw_doctor(args)


async def cmd_openclaw_setup(args: argparse.Namespace) -> int:
    return await _cmd_openclaw_setup(args)


async def cmd_openclaw_check(args: argparse.Namespace) -> int:
    return await _cmd_openclaw_check(args)


async def inspect_openclaw_integration(config_path: Path) -> dict[str, Any]:
    return await _inspect_openclaw_integration(config_path)


async def write_wrapper_defaults(config_path: Path) -> WrapperStateResult:
    return await _write_wrapper_defaults(config_path)


async def reconcile_openclaw_setup(
    config_path: Path,
    *,
    is_non_interactive: bool,
    openclaw_base_url: str | None = None,
    openclaw_gateway_token: str | None = None,
) -> WrapperStateResult:
    return await _reconcile_openclaw_setup(
        config_path,
        is_non_interactive=is_non_interactive,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=openclaw_gateway_token,
    )


async def _compatibility_payload(settings: Any) -> dict[str, Any] | None:
    adapter = build_openclaw_gateway_adapter(settings)
    compatibility = await adapter.check_compatibility()
    return compatibility.model_dump(mode="json")


def _support_ok(host_state: OpenClawResolvedHostState) -> bool:
    return (
        host_state.binary_found and host_state.support_status == OpenClawHostSupportStatus.SUPPORTED
    )


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


def _print_host_state(payload: dict[str, Any], *, is_rich: bool) -> None:
    support = payload["support_status"]
    label = (
        success(support, is_rich=is_rich)
        if payload["ok"]
        else warn(support, is_rich=is_rich)
    )
    print(heading("AutoClaw openclaw check", is_rich=is_rich))
    print(f"support: {label}")
    if payload["reason"]:
        print(f"reason: {warn(str(payload['reason']), is_rich=is_rich)}")
    print(f"binary: {accent(str(payload['binary_path'] or 'not found'), is_rich=is_rich)}")
    print(f"config: {accent(str(payload['config_path']), is_rich=is_rich)}")
    print(f"base url: {accent(str(payload['base_url']), is_rich=is_rich)}")
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
        print(warn("worker and operator must use separate OpenClaw agents", is_rich=is_rich))


async def _inspect_openclaw_integration(config_path: Path) -> dict[str, Any]:
    with command_env(config_path=config_path):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
        wrapper_path = wrapper_state_path(settings.data_dir)
        compatibility = None
        if _support_ok(host_state):
            compatibility = await _compatibility_payload(settings)
        integration_state = load_openclaw_integration_state(
            settings=settings,
            host_state=host_state,
        )
    return build_host_state_payload(
        host_state=host_state,
        integration_state=integration_state,
        wrapper_path=wrapper_path,
        compatibility=compatibility,
    )


async def _cmd_openclaw_check(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    payload = await inspect_openclaw_integration(config_path)
    if args.json:
        print_json(payload)
    else:
        _print_host_state(payload, is_rich=rich_enabled(args))
    return 0 if payload["ok"] else 1


async def _reconcile_openclaw_setup(
    config_path: Path,
    *,
    is_non_interactive: bool,
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

    selection = resolve_openclaw_agent_selection(
        config_path=config_path,
        host_state=host_state,
        is_non_interactive=is_non_interactive,
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
        is_written=True,
        payload=payload,
        material_paths=paths,
        worker_agent_id=selection.worker_agent_id,
        operator_agent_id=selection.operator_agent_id,
        mcp_servers_written=mcp_servers_written,
        is_worker_bootstrapped=selection.is_worker_bootstrapped,
        is_operator_bootstrapped=selection.is_operator_bootstrapped,
        agent_profiles_written=agent_profiles_written,
    )


async def _write_wrapper_defaults(config_path: Path) -> WrapperStateResult:
    return await reconcile_openclaw_setup(config_path, is_non_interactive=True)


async def _apply_openclaw_doctor_fix(
    args: argparse.Namespace,
    *,
    config_path: Path,
    openclaw_base_url: str | None,
) -> bool:
    bootstrap_openclaw_gateway_access(
        config_path=config_path,
        is_non_interactive=True,
        gateway_token=getattr(args, "openclaw_gateway_token", None),
        gateway_port=getattr(args, "openclaw_gateway_port", None),
        openclaw_base_url=openclaw_base_url,
    )
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    if preflight.host_state.support_status != "supported":
        raise RuntimeError(preflight.payload["reason"] or "unsupported OpenClaw host state")
    persist_openclaw_base_url(
        config_path,
        openclaw_base_url=openclaw_base_url,
    )
    await reconcile_openclaw_setup(
        config_path,
        is_non_interactive=True,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    return True


def _build_openclaw_doctor_payload(
    *,
    fixed: bool,
    host_state: OpenClawResolvedHostState,
    integration_state: Any,
    state_path: Path,
) -> dict[str, Any]:
    ok = openclaw_integration_ok(host_state, integration_state, compatibility={})
    return {
        "ok": ok,
        "support_status": host_state.support_status,
        "reason": host_state.reason,
        "path": str(state_path),
        "worker_agent_id": integration_state.worker_agent_id,
        "operator_agent_id": integration_state.operator_agent_id,
        "worker_agent_present": integration_state.is_worker_agent_present,
        "operator_agent_present": integration_state.is_operator_agent_present,
        "shared_agent_selection": integration_state.is_shared_agent_selection,
        "agent_profile_drift": integration_state.agent_profile_drift,
        "mcp_server_drift": integration_state.mcp_server_drift,
        "wrapper_state_drift": integration_state.is_wrapper_state_drift,
        "wrapper_material_drift": integration_state.is_wrapper_material_drift,
        "fixed": fixed,
    }


def _print_openclaw_doctor_payload(
    payload: dict[str, Any],
    *,
    is_rich: bool,
    state_path: Path,
    integration_state: Any,
) -> None:
    label = (
        success("ok", is_rich=is_rich)
        if payload["ok"]
        else warn("attention needed", is_rich=is_rich)
    )
    print(heading("AutoClaw openclaw doctor", is_rich=is_rich))
    print(f"status: {label}")
    print(f"path: {accent(str(state_path), is_rich=is_rich)}")
    print(f"worker agent: {integration_state.worker_agent_id}")
    print(f"operator agent: {integration_state.operator_agent_id}")
    print(f"agent profile drift: {integration_state.agent_profile_drift}")
    print(f"wrapper drift: {integration_state.is_wrapper_state_drift}")
    print(f"material drift: {integration_state.is_wrapper_material_drift}")
    print(f"mcp drift: {any(integration_state.mcp_server_drift.values())}")
    if payload["reason"]:
        print(f"reason: {warn(str(payload['reason']), is_rich=is_rich)}")


async def _cmd_openclaw_setup(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    effective_base_url = build_effective_openclaw_base_url(
        getattr(args, "openclaw_gateway_port", None)
    )
    bootstrap_openclaw_gateway_access(
        config_path=config_path,
        is_non_interactive=bool(getattr(args, "non_interactive", False)),
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
    persist_openclaw_base_url(
        config_path,
        openclaw_base_url=effective_base_url,
    )
    result = await reconcile_openclaw_setup(
        config_path,
        is_non_interactive=bool(getattr(args, "non_interactive", False)),
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    payload = {
        "ok": True,
        "path": str(result.path),
        "written": result.is_written,
        "state": result.payload,
        "worker_agent_id": result.worker_agent_id,
        "operator_agent_id": result.operator_agent_id,
        "bootstrapped_worker": result.is_worker_bootstrapped,
        "bootstrapped_operator": result.is_operator_bootstrapped,
        "agent_profiles_written": list(result.agent_profiles_written),
        "mcp_servers_written": list(result.mcp_servers_written),
        "material_paths": {key: str(value) for key, value in result.material_paths.items()},
    }
    if args.json:
        print_json(payload)
    else:
        is_rich = rich_enabled(args)
        print(heading("AutoClaw openclaw setup", is_rich=is_rich))
        print(f"worker agent: {accent(result.worker_agent_id, is_rich=is_rich)}")
        print(f"operator agent: {accent(result.operator_agent_id, is_rich=is_rich)}")
        print(f"wrote wrapper state: {accent(str(result.path), is_rich=is_rich)}")
    return 0


async def _cmd_openclaw_doctor(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    effective_base_url = build_effective_openclaw_base_url(
        getattr(args, "openclaw_gateway_port", None)
    )
    fixed = False
    if args.fix:
        try:
            fixed = await _apply_openclaw_doctor_fix(
                args,
                config_path=config_path,
                openclaw_base_url=effective_base_url,
            )
        except RuntimeError:
            preflight = collect_openclaw_preflight(
                config_path=config_path,
                openclaw_base_url=effective_base_url,
                openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
            )
            return emit_openclaw_preflight_failure(
                command_name="AutoClaw openclaw doctor",
                args=args,
                openclaw_payload=preflight.payload,
                stopped_before="stopped before wrapper repair",
            )
    with command_env(
        config_path=config_path,
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    ):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
        state_path = wrapper_state_path(settings.data_dir)
        integration_state = load_openclaw_integration_state(
            settings=settings,
            host_state=host_state,
        )
    payload = _build_openclaw_doctor_payload(
        fixed=fixed,
        host_state=host_state,
        integration_state=integration_state,
        state_path=state_path,
    )
    if args.json:
        print_json(payload)
    else:
        _print_openclaw_doctor_payload(
            payload,
            is_rich=rich_enabled(args),
            state_path=state_path,
            integration_state=integration_state,
        )
    return 0 if payload["ok"] else 1


__all__ = [
    "WrapperStateResult",
    "bootstrap_openclaw_gateway_access",
    "cmd_openclaw_check",
    "cmd_openclaw_doctor",
    "cmd_openclaw_setup",
    "inspect_openclaw_integration",
    "reconcile_openclaw_setup",
    "write_wrapper_defaults",
]
