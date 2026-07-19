from __future__ import annotations

import asyncio
import getpass
import importlib.util
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from autoclaw.config import Settings
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.interfaces.cli.providers.configuration import product_status_for
from autoclaw.interfaces.cli.providers.contracts import (
    ProviderCheckOutcome,
    ProviderCheckSnapshot,
    ProviderDefinitionSnapshot,
    ProviderIdentityOutcome,
    ProviderIdentitySnapshot,
    ProviderStatusSnapshot,
)
from autoclaw.runtime.providers import (
    ProviderCheckAxisStatus,
    ProviderCheckResult,
    ProviderCheckStatus,
    ProviderResolutionError,
    provider_selection_from_kind,
    resolve_provider_route,
)

PROVIDER_ORDER = (ProviderKind.CODEX, ProviderKind.CLAUDE, ProviderKind.OPENCLAW)
PROVIDER_CHECK_TIMEOUT_SECONDS = 15.0
NativeCommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class _ProviderCheckBasis:
    kind: ProviderKind
    service_identity: str
    native_home: str
    limitations: tuple[str, ...]

    def snapshot(
        self,
        *,
        outcome: ProviderCheckOutcome,
        is_ready: bool | None,
        detail: str,
        authentication: ProviderCheckAxisStatus = ProviderCheckAxisStatus.NOT_CHECKED,
        reachability: ProviderCheckAxisStatus = ProviderCheckAxisStatus.NOT_CHECKED,
    ) -> ProviderCheckSnapshot:
        return ProviderCheckSnapshot(
            kind=self.kind,
            outcome=outcome,
            is_ready=is_ready,
            service_identity=self.service_identity,
            native_home=self.native_home,
            authentication=authentication,
            reachability=reachability,
            detail=detail,
            limitations=self.limitations,
        )


def collect_provider_check(
    settings: Settings,
    provider: ProviderKind,
) -> ProviderCheckSnapshot:
    status = collect_provider_status(settings, provider)
    basis = _ProviderCheckBasis(
        kind=provider,
        service_identity=status.service_identity,
        native_home=status.native_home,
        limitations=status.limitations,
    )
    if not status.is_configured:
        return basis.snapshot(
            outcome=ProviderCheckOutcome.NOT_CONFIGURED,
            is_ready=False,
            detail=f"provider '{provider.value}' is not enabled in AutoClaw config",
        )
    if not status.is_integration_available:
        return basis.snapshot(
            outcome=ProviderCheckOutcome.NOT_INSTALLED,
            is_ready=False,
            detail=f"provider integration '{provider.value}' is not locally available",
        )
    try:
        resolve_provider_route(
            provider=provider_selection_from_kind(provider),
            settings=settings,
            available_adapter_kinds=set(ProviderKind),
        )
    except ProviderResolutionError as exc:
        return basis.snapshot(
            outcome=ProviderCheckOutcome.INCOMPATIBLE,
            is_ready=False,
            detail=str(exc),
        )
    try:
        result = execute_provider_diagnostic(settings, provider)
    except TimeoutError:
        return basis.snapshot(
            outcome=ProviderCheckOutcome.UNREACHABLE,
            is_ready=False,
            detail="the bounded provider diagnostic timed out",
        )
    except Exception:
        return basis.snapshot(
            outcome=ProviderCheckOutcome.CHECK_FAILED,
            is_ready=False,
            detail="the bounded provider diagnostic failed",
        )
    return provider_check_snapshot(basis=basis, result=result)


def collect_provider_definitions() -> tuple[ProviderDefinitionSnapshot, ...]:
    return tuple(
        ProviderDefinitionSnapshot.model_validate(
            {
                "kind": provider,
                "integration": integration_name(provider),
                "product_status": product_status_for(provider),
                "integration_available": is_provider_integration_available(provider),
                "setup_owner": "user" if provider == ProviderKind.OPENCLAW else "autoclaw",
            }
        )
        for provider in PROVIDER_ORDER
    )


def collect_provider_statuses(
    settings: Settings,
    provider: ProviderKind | None = None,
) -> tuple[ProviderStatusSnapshot, ...]:
    selected = (provider,) if provider is not None else PROVIDER_ORDER
    return tuple(collect_provider_status(settings, item) for item in selected)


def collect_provider_status(
    settings: Settings,
    provider: ProviderKind,
) -> ProviderStatusSnapshot:
    configured = provider_is_enabled(settings, provider)
    return ProviderStatusSnapshot.model_validate(
        {
            "kind": provider,
            "product_status": product_status_for(provider),
            "integration_available": is_provider_integration_available(provider),
            "configured": configured,
            "is_default": settings.runtime.default_provider == provider,
            "configuration_fields_present": provider_fields_are_present(settings, provider),
            "service_identity": service_identity(),
            "native_home": str(provider_native_home(provider)),
            "route": provider_route_readback(settings, provider),
            "limitations": provider_limitations(provider),
        }
    )


def invoke_provider_identity_action(
    provider: ProviderKind,
    action: str,
    *,
    is_json_output: bool,
    command_runner: NativeCommandRunner | None = None,
) -> ProviderIdentitySnapshot:
    normalized_action = identity_action(action)
    identity = service_identity()
    native_home = str(provider_native_home(provider))
    if provider != ProviderKind.CODEX:
        return ProviderIdentitySnapshot(
            provider=provider,
            action=normalized_action,
            outcome=ProviderIdentityOutcome.USER_MANAGED,
            service_identity=identity,
            native_home=native_home,
            detail=provider_identity_owner_message(provider),
        )

    try:
        codex_binary = bundled_codex_path()
    except FileNotFoundError:
        return ProviderIdentitySnapshot(
            provider=provider,
            action=normalized_action,
            outcome=ProviderIdentityOutcome.NOT_INSTALLED,
            service_identity=identity,
            native_home=native_home,
            detail="the SDK-bundled Codex CLI is not available",
        )

    command = [str(codex_binary), normalized_action]
    completed = invoke_native_identity_command(
        command,
        is_json_output=is_json_output,
        command_runner=command_runner,
    )
    outcome = (
        ProviderIdentityOutcome.SUCCEEDED
        if completed.returncode == 0
        else ProviderIdentityOutcome.FAILED
    )
    return ProviderIdentitySnapshot(
        provider=provider,
        action=normalized_action,
        outcome=outcome,
        service_identity=identity,
        native_home=native_home,
        detail=(
            f"native Codex {normalized_action} completed"
            if completed.returncode == 0
            else f"native Codex {normalized_action} failed"
        ),
    )


def execute_provider_diagnostic(
    settings: Settings,
    provider: ProviderKind,
) -> ProviderCheckResult:
    """Run one explicit bounded non-agent adapter diagnostic."""

    from autoclaw.integrations.provider_registry import build_provider_adapter

    async def run() -> ProviderCheckResult:
        adapter = build_provider_adapter(provider, settings)
        async with asyncio.timeout(PROVIDER_CHECK_TIMEOUT_SECONDS):
            async with adapter.lifespan():
                return await adapter.read_availability()

    return asyncio.run(run())


def bundled_codex_path() -> Path:
    """Resolve the SDK-bundled CLI without loading it for passive commands."""

    from codex_cli_bin import bundled_codex_path as resolve_path  # type: ignore[import-untyped]

    return Path(resolve_path())


def provider_check_snapshot(
    *,
    basis: _ProviderCheckBasis,
    result: ProviderCheckResult,
) -> ProviderCheckSnapshot:
    if result.status in {ProviderCheckStatus.AVAILABLE, ProviderCheckStatus.LIMITED}:
        return basis.snapshot(
            outcome=ProviderCheckOutcome.READY,
            is_ready=True,
            detail=result.code,
            authentication=result.authentication,
            reachability=result.reachability,
        )

    code = result.code
    if "auth" in code:
        outcome = ProviderCheckOutcome.AUTHENTICATION_FAILED
    elif any(marker in code for marker in ("connection", "timeout", "unreachable")):
        outcome = ProviderCheckOutcome.UNREACHABLE
    elif any(marker in code for marker in ("incompatible", "rejected", "unsupported")):
        outcome = ProviderCheckOutcome.INCOMPATIBLE
    else:
        outcome = ProviderCheckOutcome.CHECK_FAILED
    return basis.snapshot(
        outcome=outcome,
        is_ready=False,
        detail=code,
        authentication=result.authentication,
        reachability=result.reachability,
    )


def identity_action(action: str) -> Literal["login", "logout"]:
    if action == "login":
        return "login"
    if action == "logout":
        return "logout"
    raise ValueError(f"unsupported provider identity action: {action}")


def invoke_native_identity_command(
    command: list[str],
    *,
    is_json_output: bool,
    command_runner: NativeCommandRunner | None,
) -> subprocess.CompletedProcess[str]:
    process_options: dict[str, object] = {"check": False, "text": True}
    if is_json_output:
        process_options.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if command_runner is not None:
        return command_runner(command, **process_options)
    if is_json_output:
        return subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return subprocess.run(command, check=False, text=True)


def integration_name(provider: ProviderKind) -> str:
    match provider:
        case ProviderKind.CODEX:
            return "Codex managed SDK/app-server"
        case ProviderKind.CLAUDE:
            return "Claude managed Agent SDK"
        case ProviderKind.OPENCLAW:
            return "OpenClaw external Gateway compatibility"


def is_provider_integration_available(provider: ProviderKind) -> bool:
    match provider:
        case ProviderKind.CODEX:
            return module_is_available("openai_codex")
        case ProviderKind.CLAUDE:
            return module_is_available("claude_agent_sdk")
        case ProviderKind.OPENCLAW:
            return shutil.which("openclaw") is not None


def module_is_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def service_identity() -> str:
    try:
        import pwd

        return pwd.getpwuid(os.geteuid()).pw_name
    except (AttributeError, ImportError, KeyError):
        pass
    return getpass.getuser()


def provider_native_home(provider: ProviderKind) -> Path:
    user_home = Path.home()
    match provider:
        case ProviderKind.CODEX:
            return Path(os.environ.get("CODEX_HOME", user_home / ".codex")).expanduser()
        case ProviderKind.CLAUDE:
            return Path(os.environ.get("CLAUDE_CONFIG_DIR", user_home / ".claude")).expanduser()
        case ProviderKind.OPENCLAW:
            return Path(os.environ.get("OPENCLAW_STATE_DIR", user_home / ".openclaw")).expanduser()


def provider_fields_are_present(settings: Settings, provider: ProviderKind) -> bool:
    match provider:
        case ProviderKind.CODEX | ProviderKind.CLAUDE:
            return provider_is_enabled(settings, provider)
        case ProviderKind.OPENCLAW:
            return bool(
                settings.openclaw.enabled
                and settings.openclaw.gateway_url.strip()
                and settings.openclaw.gateway_profile.strip()
            )


def provider_is_enabled(settings: Settings, provider: ProviderKind) -> bool:
    match provider:
        case ProviderKind.CODEX:
            return settings.codex.enabled
        case ProviderKind.CLAUDE:
            return settings.claude.enabled
        case ProviderKind.OPENCLAW:
            return settings.openclaw.enabled


def provider_route_readback(
    settings: Settings,
    provider: ProviderKind,
) -> dict[str, str | bool | None]:
    match provider:
        case ProviderKind.CODEX:
            return {
                "enabled": settings.codex.enabled,
                "model": settings.codex.model,
                "effort": settings.codex.effort,
            }
        case ProviderKind.CLAUDE:
            return {
                "enabled": settings.claude.enabled,
                "model": settings.claude.model,
                "effort": settings.claude.effort,
            }
        case ProviderKind.OPENCLAW:
            return {
                "enabled": settings.openclaw.enabled,
                "gateway_url": redact_url_userinfo(settings.openclaw.gateway_url),
                "gateway_profile": settings.openclaw.gateway_profile,
            }


def redact_url_userinfo(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "__AUTOCLAW_REDACTED__" if "@" in value else value
    if parsed.username is None and parsed.password is None:
        return value
    host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        return "__AUTOCLAW_REDACTED__"
    if port is not None:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def provider_limitations(provider: ProviderKind) -> tuple[str, ...]:
    if provider == ProviderKind.CODEX:
        return (
            "the pinned Codex app-server cannot enforce MCP-only provider-native "
            "access denied; that route is rejected before dispatch creation",
            "when network access is denied, the pinned Codex sandbox narrows full "
            "provider-native access to restricted with controller provenance",
        )
    if provider == ProviderKind.OPENCLAW:
        return (
            "experimental selectable lane",
            "OpenClaw configuration and compatibility MCP setup are user-managed",
            "an explicit native Gateway credential is required when gateway_url is set",
            "the ordinary Gateway CLI cannot transmit the dispatch cwd; only its local "
            "subprocess cwd is set",
        )
    return ()


def provider_identity_owner_message(provider: ProviderKind) -> str:
    if provider == ProviderKind.CLAUDE:
        return "Claude identity is user-managed through supported vendor-native configuration"
    return "OpenClaw Gateway identity is user-managed outside AutoClaw"


def providers_payload(
    snapshots: Sequence[
        ProviderDefinitionSnapshot | ProviderStatusSnapshot | ProviderCheckSnapshot
    ],
) -> list[dict[str, object]]:
    return [snapshot.model_dump(mode="json") for snapshot in snapshots]


__all__ = [
    "PROVIDER_ORDER",
    "collect_provider_check",
    "collect_provider_definitions",
    "collect_provider_status",
    "collect_provider_statuses",
    "execute_provider_diagnostic",
    "integration_name",
    "invoke_native_identity_command",
    "invoke_provider_identity_action",
    "is_provider_integration_available",
    "module_is_available",
    "provider_native_home",
    "providers_payload",
    "redact_url_userinfo",
    "service_identity",
]
