from __future__ import annotations

import argparse

from autoclaw.config import load_settings
from autoclaw.interfaces.cli.commands.config_view import redact_database_url
from autoclaw.interfaces.cli.providers import collect_provider_statuses
from autoclaw.interfaces.cli.providers.inspection import providers_payload
from autoclaw.interfaces.cli.support import coerce_path, command_env, print_json


def cmd_status(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
    providers = collect_provider_statuses(settings)
    payload = {
        "ok": True,
        "config": {
            "path": str(config_path),
            "exists": config_path.is_file(),
            "data_dir": str(settings.data_dir),
        },
        "database": {
            "configured_url": redact_database_url(settings.database_url),
            "schema": "not_checked",
        },
        "service": {"status": "not_checked"},
        "default_provider": (
            settings.runtime.default_provider.value
            if settings.runtime.default_provider is not None
            else None
        ),
        "providers": providers_payload(providers),
    }
    if args.json:
        print_json(payload)
    else:
        print("AutoClaw status")
        print(f"config: {config_path} ({'present' if config_path.is_file() else 'missing'})")
        print(f"data: {settings.data_dir}")
        default = payload["default_provider"] or "not configured"
        print(f"default provider: {default}")
        print("database schema: not_checked")
        print("service: not_checked")
        for provider in providers:
            configured = "configured" if provider.configured else "not configured"
            print(
                f"provider {provider.kind.value}: {configured}; "
                "authentication not_checked; reachability not_checked"
            )
    return 0


__all__ = ["cmd_status"]
