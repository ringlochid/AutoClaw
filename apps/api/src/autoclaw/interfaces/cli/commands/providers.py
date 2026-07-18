from __future__ import annotations

import argparse
from typing import Any

from autoclaw.config import load_settings
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.interfaces.cli.providers import (
    ProviderConfigurationRequest,
    collect_provider_check,
    collect_provider_definitions,
    collect_provider_statuses,
    configure_provider,
    invoke_provider_identity_action,
    set_default_provider,
)
from autoclaw.interfaces.cli.providers.contracts import (
    ProviderConfigurationSnapshot,
    ProviderIdentityOutcome,
)
from autoclaw.interfaces.cli.providers.inspection import providers_payload
from autoclaw.interfaces.cli.support import coerce_path, command_env, print_json


def cmd_providers_list(args: argparse.Namespace) -> int:
    definitions = collect_provider_definitions()
    payload = {"ok": True, "providers": providers_payload(definitions)}
    if args.json:
        print_json(payload)
    else:
        print("AutoClaw provider integrations")
        for definition in definitions:
            availability = "available" if definition.integration_available else "unavailable"
            print(
                f"{definition.kind.value}: {definition.product_status.value}; "
                f"{availability}; setup owner: {definition.setup_owner}"
            )
    return 0


def cmd_providers_status(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
    provider = ProviderKind(args.provider) if args.provider is not None else None
    statuses = collect_provider_statuses(settings, provider)
    payload = {
        "ok": True,
        "config_path": str(config_path),
        "providers": providers_payload(statuses),
    }
    if args.json:
        print_json(payload)
    else:
        for status in statuses:
            configured = "configured" if status.configured else "not configured"
            default = "; default" if status.is_default else ""
            available = "available" if status.integration_available else "unavailable"
            print(
                f"{status.kind.value}: {configured}{default}; {available}; "
                f"{status.product_status.value}"
            )
            print(f"  identity: {status.service_identity}")
            print(f"  native home: {status.native_home}")
            print("  authentication: not_checked; reachability: not_checked")
    return 0


def cmd_providers_check(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    provider = ProviderKind(args.provider)
    with command_env(config_path=config_path):
        settings = load_settings()
    snapshot = collect_provider_check(settings, provider)
    payload = {"ok": snapshot.is_ready is not False, **snapshot.model_dump(mode="json")}
    if args.json:
        print_json(payload)
    else:
        print(f"provider check: {provider.value}")
        print(f"outcome: {snapshot.outcome.value}")
        print(f"detail: {snapshot.detail}")
        print(f"identity: {snapshot.service_identity}")
        print(f"native home: {snapshot.native_home}")
        print("authentication: not_checked; reachability: not_checked")
        for limitation in snapshot.limitations:
            print(f"limitation: {limitation}")
    return 1 if snapshot.is_ready is False else 0


def cmd_providers_configure(args: argparse.Namespace) -> int:
    request = provider_configuration_request_from_args(args)
    snapshot = configure_provider(coerce_path(args.config), request)
    emit_provider_configuration(snapshot, is_json_output=args.json)
    return 0


def cmd_providers_set_default(args: argparse.Namespace) -> int:
    snapshot = set_default_provider(
        coerce_path(args.config),
        ProviderKind(args.provider),
    )
    emit_provider_configuration(snapshot, is_json_output=args.json)
    return 0


def cmd_providers_identity(args: argparse.Namespace, action: str) -> int:
    snapshot = invoke_provider_identity_action(
        ProviderKind(args.provider),
        action,
        is_json_output=args.json,
    )
    payload = {
        "ok": snapshot.outcome == ProviderIdentityOutcome.SUCCEEDED,
        **snapshot.model_dump(mode="json"),
    }
    if args.json:
        print_json(payload)
    else:
        print(f"provider {action}: {snapshot.provider.value}")
        print(f"outcome: {snapshot.outcome.value}")
        print(f"detail: {snapshot.detail}")
        print(f"identity: {snapshot.service_identity}")
        print(f"native home: {snapshot.native_home}")
    return 0 if snapshot.outcome == ProviderIdentityOutcome.SUCCEEDED else 1


def cmd_setup(args: argparse.Namespace) -> int:
    if args.provider is None:
        guide_payload = {
            "ok": True,
            "configured_provider": None,
            "next_actions": [
                "autoclaw init",
                "autoclaw providers configure <provider>",
                "autoclaw providers status",
            ],
        }
        if args.json:
            print_json(guide_payload)
        else:
            print("AutoClaw setup is ready with zero configured providers.")
            print("Next: autoclaw providers configure <provider>")
        return 0

    request = provider_configuration_request_from_args(args)
    snapshot = configure_provider(coerce_path(args.config), request)
    setup_payload: dict[str, Any] = {
        "ok": True,
        "configured_provider": snapshot.provider.value,
        "configuration": snapshot.model_dump(mode="json"),
        "next_actions": ["autoclaw providers status", "autoclaw serve"],
    }
    if args.json:
        print_json(setup_payload)
    else:
        print(f"Configured provider: {snapshot.provider.value}")
        print(f"Default provider: {snapshot.default_provider.value}")
        print("Next: autoclaw providers status")
    return 0


def provider_configuration_request_from_args(
    args: argparse.Namespace,
) -> ProviderConfigurationRequest:
    return ProviderConfigurationRequest(
        provider=ProviderKind(args.provider),
        model=getattr(args, "model", None),
        effort=getattr(args, "effort", None),
        gateway_url=getattr(args, "gateway_url", None),
        gateway_profile=getattr(args, "gateway_profile", None),
    )


def emit_provider_configuration(
    snapshot: ProviderConfigurationSnapshot,
    *,
    is_json_output: bool,
) -> None:
    payload: dict[str, Any] = {"ok": True, **snapshot.model_dump(mode="json")}
    if is_json_output:
        print_json(payload)
        return
    print(f"Configured provider: {snapshot.provider.value}")
    print(f"Default provider: {snapshot.default_provider.value}")
    print(f"Default changed: {str(snapshot.default_changed).lower()}")
    if snapshot.product_status.value == "experimental":
        print("Product status: experimental selectable lane")


__all__ = [
    "cmd_providers_check",
    "cmd_providers_configure",
    "cmd_providers_identity",
    "cmd_providers_list",
    "cmd_providers_set_default",
    "cmd_providers_status",
    "cmd_setup",
    "emit_provider_configuration",
    "provider_configuration_request_from_args",
]
