from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.cli_support import command_env, print_json
from app.config import Settings, load_settings
from app.runtime.openclaw.discovery import OpenClawResolvedHostState
from app.runtime.openclaw.preflight import openclaw_preflight_report
from app.terminal.theme import accent, heading, muted, rich_enabled, success, warn


@dataclass(frozen=True)
class OpenClawPreflightResult:
    settings: Settings
    host_state: OpenClawResolvedHostState
    payload: dict[str, Any]


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
    }


def collect_openclaw_preflight(
    *,
    config_path: Path,
    data_dir: Path | None = None,
    database_url: str | None = None,
    api_host: str | None = None,
    api_port: int | None = None,
    log_level: str | None = None,
    api_key: str | None = None,
    internal_api_key: str | None = None,
) -> OpenClawPreflightResult:
    with command_env(
        config_path=config_path,
        data_dir=data_dir,
        database_url=database_url,
        api_host=api_host,
        api_port=api_port,
        log_level=log_level,
        api_key=api_key,
        internal_api_key=internal_api_key,
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
        rich = rich_enabled(args)
        openclaw_mode = (
            f"loopback={openclaw_payload['loopback']}, "
            f"auth={openclaw_payload['effective_auth'] or 'unknown'}"
        )
        config_label = (
            success("present", rich=rich)
            if openclaw_payload["config_exists"]
            else warn("missing", rich=rich)
        )
        print(heading(command_name, rich=rich))
        print(warn("OpenClaw preflight failed", rich=rich))
        if openclaw_payload["reason"]:
            print(f"reason: {warn(str(openclaw_payload['reason']), rich=rich)}")
        print(muted(stopped_before, rich=rich))
        print(
            "openclaw: "
            f"{warn(openclaw_payload['support_status'], rich=rich)} "
            f"{muted(openclaw_mode, rich=rich)}"
        )
        print(f"openclaw base url: {accent(openclaw_payload['base_url'], rich=rich)}")
        print(
            "openclaw config: "
            f"{accent(openclaw_payload['config_path'], rich=rich)} "
            f"({config_label})"
        )
        print(
            "openclaw binary: "
            f"{accent(str(openclaw_payload['binary_path'] or 'not found'), rich=rich)}"
        )
    return 1


__all__ = [
    "OpenClawPreflightResult",
    "collect_openclaw_preflight",
    "emit_openclaw_preflight_failure",
    "openclaw_preflight_payload",
]
