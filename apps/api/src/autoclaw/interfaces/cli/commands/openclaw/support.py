from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoclaw.config import Settings, load_settings
from autoclaw.integrations.openclaw.gateway.discovery import OpenClawResolvedHostState
from autoclaw.integrations.openclaw.gateway.preflight import openclaw_preflight_report
from autoclaw.interfaces.cli.support import command_env, print_json
from autoclaw.interfaces.cli.terminal.theme import (
    accent,
    heading,
    muted,
    rich_enabled,
    success,
    warn,
)


@dataclass(frozen=True)
class OpenClawPreflightResult:
    settings: Settings
    host_state: OpenClawResolvedHostState
    payload: dict[str, Any]


def collect_openclaw_preflight(
    *,
    config_path: Path,
    data_dir: Path | None = None,
    database_url: str | None = None,
    api_host: str | None = None,
    api_port: int | None = None,
    log_level: str | None = None,
    api_key: str | None = None,
    openclaw_base_url: str | None = None,
    openclaw_gateway_token: str | None = None,
) -> OpenClawPreflightResult:
    with command_env(
        config_path=config_path,
        data_dir=data_dir,
        database_url=database_url,
        api_host=api_host,
        api_port=api_port,
        log_level=log_level,
        api_key=api_key,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=openclaw_gateway_token,
    ):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
    return OpenClawPreflightResult(
        settings=settings,
        host_state=host_state,
        payload=openclaw_preflight_payload(host_state),
    )


def emit_openclaw_preflight_failure(
    *,
    command_name: str,
    args: argparse.Namespace,
    openclaw_payload: dict[str, Any],
    stopped_before: str,
    payload_extra: dict[str, Any] | None = None,
) -> int:
    payload = {"ok": False, **(payload_extra or {}), "openclaw": openclaw_payload}
    if getattr(args, "json", False):
        print_json(payload)
    else:
        is_rich = rich_enabled(args)
        openclaw_mode = (
            f"loopback={openclaw_payload['loopback']}, "
            f"auth={openclaw_payload['effective_auth'] or 'unknown'}"
        )
        config_label = (
            success("present", is_rich=is_rich)
            if openclaw_payload["config_exists"]
            else warn("missing", is_rich=is_rich)
        )
        print(heading(command_name, is_rich=is_rich))
        print(warn("OpenClaw preflight failed", is_rich=is_rich))
        if openclaw_payload["reason"]:
            print(f"reason: {warn(str(openclaw_payload['reason']), is_rich=is_rich)}")
        if openclaw_payload["config_error"]:
            print(f"config error: {warn(str(openclaw_payload['config_error']), is_rich=is_rich)}")
        print(muted(stopped_before, is_rich=is_rich))
        print(
            "openclaw: "
            f"{warn(openclaw_payload['support_status'], is_rich=is_rich)} "
            f"{muted(openclaw_mode, is_rich=is_rich)}"
        )
        print(f"openclaw base url: {accent(openclaw_payload['base_url'], is_rich=is_rich)}")
        print(
            "openclaw config: "
            f"{accent(openclaw_payload['config_path'], is_rich=is_rich)} "
            f"({config_label})"
        )
        print(
            "openclaw binary: "
            f"{accent(str(openclaw_payload['binary_path'] or 'not found'), is_rich=is_rich)}"
        )
    return 1


def openclaw_preflight_payload(host_state: OpenClawResolvedHostState) -> dict[str, Any]:
    return {
        "support_status": host_state.support_status,
        "reason": host_state.reason,
        "base_url": host_state.base_url,
        "loopback": host_state.loopback,
        "auth_mode": host_state.auth_mode,
        "effective_auth": host_state.effective_auth,
        "binary_found": host_state.binary_found,
        "binary_path": host_state.binary_path,
        "config_path": host_state.config_path,
        "config_exists": host_state.config_exists,
        "config_error": host_state.config_error,
    }


__all__ = [
    "OpenClawPreflightResult",
    "collect_openclaw_preflight",
    "emit_openclaw_preflight_failure",
    "openclaw_preflight_payload",
]
