from __future__ import annotations

import argparse
from importlib import resources
from typing import Any

from app.cli.commands.bootstrap import ensure_database_ready_with_legacy_sqlite_repair
from app.cli.commands.openclaw.support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli.commands.openclaw.wrapper import (
    WrapperStateResult,
    inspect_openclaw_integration,
    reconcile_openclaw_setup,
)
from app.cli.commands.service import DEFAULT_SERVICE_NAME, collect_service_status
from app.cli.terminal.theme import heading, muted, rich_enabled, success, warn
from app.cli_support import coerce_path, command_env, print_json
from app.config import load_settings
from app.db.session import ping_database, verify_database_schema
from app.paths import ensure_runtime_dirs


async def cmd_doctor(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    if not config_path.is_file():
        return _emit_missing_config_exit(args, str(config_path))

    preflight = collect_openclaw_preflight(config_path=config_path)
    if args.fix and preflight.host_state.support_status != "supported":
        return emit_openclaw_preflight_failure(
            command_name="AutoClaw doctor",
            args=args,
            openclaw_payload=preflight.payload,
            stopped_before="stopped before local and OpenClaw repair",
        )

    findings: list[dict[str, Any]] = []
    openclaw_payload = await inspect_openclaw_integration(config_path)
    findings.append(
        {
            "name": "openclaw_integration",
            "status": "ok" if openclaw_payload["ok"] else "warn",
            "detail": openclaw_payload,
        }
    )

    with command_env(config_path=config_path):
        settings = load_settings()
        args.config_path = config_path
        args.database_url = settings.database_url
        args.settings = settings
        await _collect_local_doctor_findings(args, findings)
        if args.fix:
            wrapper_repair_result: WrapperStateResult = await reconcile_openclaw_setup(
                config_path,
                is_non_interactive=True,
            )
            findings.append(
                {
                    "name": "openclaw_integration_fix",
                    "status": "ok",
                    "detail": {
                        "worker_agent_id": wrapper_repair_result.worker_agent_id,
                        "operator_agent_id": wrapper_repair_result.operator_agent_id,
                        "mcp_servers_written": list(wrapper_repair_result.mcp_servers_written),
                        "bootstrapped_worker": wrapper_repair_result.is_worker_bootstrapped,
                        "bootstrapped_operator": wrapper_repair_result.is_operator_bootstrapped,
                    },
                }
            )

    ok = not any(item["status"] == "error" for item in findings)
    payload = {"ok": ok, "findings": findings}
    if args.json:
        print_json(payload)
        return 0 if ok else 1

    is_rich = rich_enabled(args)
    label = success("ok", is_rich=is_rich) if ok else warn("attention needed", is_rich=is_rich)
    print(heading("AutoClaw doctor", is_rich=is_rich))
    print(f"status: {label}")
    for finding in findings:
        print(f"{finding['name']}: {muted(str(finding['status']), is_rich=is_rich)}")
    return 0 if ok else 1


def _emit_missing_config_exit(args: argparse.Namespace, config_path: str) -> int:
    payload = {
        "ok": False,
        "findings": [
            {
                "name": "config_path",
                "status": "error",
                "detail": f"missing config file: {config_path}",
            }
        ],
    }
    if args.json:
        print_json(payload)
    else:
        is_rich = rich_enabled(args)
        print(heading("AutoClaw doctor", is_rich=is_rich))
        print(warn(f"missing config file: {config_path}", is_rich=is_rich))
    return 1


async def _collect_local_doctor_findings(
    args: argparse.Namespace,
    findings: list[dict[str, Any]],
) -> None:
    ensure_runtime_dirs(config_dir=args.config_path.parent, data_dir=args.settings.data_dir)
    findings.append(
        {
            "name": "runtime_dirs",
            "status": "ok",
            "detail": str(args.settings.data_dir),
        }
    )
    await _collect_database_findings(args, findings)
    definitions_root = resources.files("app.resources").joinpath("definitions")
    findings.append(
        {
            "name": "packaged_resources",
            "status": "ok" if definitions_root.is_dir() else "error",
            "detail": str(definitions_root),
        }
    )
    service_status = collect_service_status(DEFAULT_SERVICE_NAME)
    if service_status is None:
        findings.append(
            {
                "name": "service_manager",
                "status": "warn",
                "detail": "managed service checks are unavailable on this platform",
            }
        )
        return
    findings.append(
        {
            "name": "service_manager",
            "status": "ok" if service_status.installed else "warn",
            "detail": service_status.to_payload(),
        }
    )


async def _collect_database_findings(
    args: argparse.Namespace,
    findings: list[dict[str, Any]],
) -> None:
    if args.fix:
        repair_result = await ensure_database_ready_with_legacy_sqlite_repair(args.database_url)
        repair_detail: dict[str, Any] = {"status": "applied db upgrade/seed repair"}
        if repair_result is not None:
            repair_detail.update(
                {
                    "backup_path": str(repair_result.backup_path),
                    "migrated_tables": list(repair_result.migrated_tables),
                    "skipped_tables": list(repair_result.skipped_tables),
                }
            )
        findings.append(
            {
                "name": "database_fix",
                "status": "ok",
                "detail": repair_detail,
            }
        )
        return
    await ping_database()
    await verify_database_schema()
    findings.append(
        {
            "name": "database",
            "status": "ok",
            "detail": args.database_url,
        }
    )


__all__ = ["cmd_doctor"]
