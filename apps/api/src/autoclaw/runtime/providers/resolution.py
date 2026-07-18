from __future__ import annotations

from collections.abc import Collection
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import TypeAdapter, ValidationError, WebsocketUrl

from autoclaw.config import Settings
from autoclaw.definitions.contracts.workflow import ProviderKind, ProviderSelection
from autoclaw.runtime.contracts.provider_resolution import (
    ClaudeProviderRoute,
    CodexProviderRoute,
    OpenClawProviderRoute,
    ProviderResolution,
    ProviderSelectionBasis,
)

_WEBSOCKET_URL_ADAPTER = TypeAdapter(WebsocketUrl)


class ProviderResolutionErrorCode(StrEnum):
    DEFAULT_NOT_CONFIGURED = "provider_default_not_configured"
    PROVIDER_DISABLED = "provider_disabled"
    INVALID_CONFIGURATION = "provider_invalid_configuration"
    ADAPTER_UNAVAILABLE = "provider_adapter_unavailable"


class ProviderResolutionError(ValueError):
    def __init__(
        self,
        *,
        code: ProviderResolutionErrorCode,
        provider: ProviderKind | None,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider = provider


def resolve_provider_route(
    *,
    provider: ProviderSelection | None,
    settings: Settings,
    available_adapter_kinds: Collection[ProviderKind],
) -> ProviderResolution:
    selected_provider, selection_basis = _select_provider(provider, settings=settings)
    if not _provider_is_enabled(selected_provider, settings=settings):
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.PROVIDER_DISABLED,
            provider=selected_provider,
            message=f"provider '{selected_provider.value}' is disabled",
        )
    route = _build_provider_route(selected_provider, settings=settings)
    if selected_provider not in available_adapter_kinds:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.ADAPTER_UNAVAILABLE,
            provider=selected_provider,
            message=f"provider adapter '{selected_provider.value}' is unavailable",
        )

    return ProviderResolution(
        requested_provider=selected_provider,
        resolved_provider=selected_provider,
        selection_basis=selection_basis,
        route=route,
    )


def _select_provider(
    provider: ProviderSelection | None,
    *,
    settings: Settings,
) -> tuple[ProviderKind, ProviderSelectionBasis]:
    if provider is not None:
        return provider.kind, ProviderSelectionBasis.EXPLICIT
    if settings.runtime.default_provider is None:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.DEFAULT_NOT_CONFIGURED,
            provider=None,
            message="runtime.default_provider is not configured",
        )
    return settings.runtime.default_provider, ProviderSelectionBasis.DEFAULT


def _provider_is_enabled(provider: ProviderKind, *, settings: Settings) -> bool:
    match provider:
        case ProviderKind.CODEX:
            return settings.codex.enabled
        case ProviderKind.CLAUDE:
            return settings.claude.enabled
        case ProviderKind.OPENCLAW:
            return settings.openclaw.enabled


def _build_provider_route(
    provider: ProviderKind,
    *,
    settings: Settings,
) -> CodexProviderRoute | ClaudeProviderRoute | OpenClawProviderRoute:
    match provider:
        case ProviderKind.CODEX:
            return CodexProviderRoute(
                kind=ProviderKind.CODEX,
                model_override=_validate_optional_override(
                    settings.codex.model,
                    provider=ProviderKind.CODEX,
                    field_name="codex.model",
                ),
                effort_override=_validate_optional_override(
                    settings.codex.effort,
                    provider=ProviderKind.CODEX,
                    field_name="codex.effort",
                ),
            )
        case ProviderKind.CLAUDE:
            return ClaudeProviderRoute(
                kind=ProviderKind.CLAUDE,
                model_override=_validate_optional_override(
                    settings.claude.model,
                    provider=ProviderKind.CLAUDE,
                    field_name="claude.model",
                ),
                effort_override=_validate_optional_override(
                    settings.claude.effort,
                    provider=ProviderKind.CLAUDE,
                    field_name="claude.effort",
                ),
            )
        case ProviderKind.OPENCLAW:
            _validate_openclaw_gateway_url(settings.openclaw.gateway_url)
            return OpenClawProviderRoute(
                kind=ProviderKind.OPENCLAW,
                gateway_profile=_validate_required_value(
                    settings.openclaw.gateway_profile,
                    provider=ProviderKind.OPENCLAW,
                    field_name="openclaw.gateway_profile",
                ),
            )


def _validate_optional_override(
    value: str | None,
    *,
    provider: ProviderKind,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return _validate_required_value(value, provider=provider, field_name=field_name)


def _validate_required_value(
    value: str,
    *,
    provider: ProviderKind,
    field_name: str,
) -> str:
    if not value:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.INVALID_CONFIGURATION,
            provider=provider,
            message=f"{field_name} must not be blank when configured",
        )
    return value


def _validate_openclaw_gateway_url(value: str) -> None:
    try:
        raw_url = urlsplit(value)
    except ValueError as exc:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.INVALID_CONFIGURATION,
            provider=ProviderKind.OPENCLAW,
            message="openclaw.gateway_url must be a valid ws or wss URL",
        ) from exc
    if raw_url.scheme not in {"ws", "wss"} or not raw_url.netloc:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.INVALID_CONFIGURATION,
            provider=ProviderKind.OPENCLAW,
            message="openclaw.gateway_url must be an absolute ws or wss URL with a host",
        )
    try:
        parsed = _WEBSOCKET_URL_ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.INVALID_CONFIGURATION,
            provider=ProviderKind.OPENCLAW,
            message="openclaw.gateway_url must be a valid ws or wss URL",
        ) from exc
    if parsed.username is not None or parsed.password is not None:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.INVALID_CONFIGURATION,
            provider=ProviderKind.OPENCLAW,
            message="openclaw.gateway_url must not contain credentials",
        )
    if parsed.fragment:
        raise ProviderResolutionError(
            code=ProviderResolutionErrorCode.INVALID_CONFIGURATION,
            provider=ProviderKind.OPENCLAW,
            message="openclaw.gateway_url must not contain a fragment",
        )


__all__ = [
    "ProviderResolutionError",
    "ProviderResolutionErrorCode",
    "resolve_provider_route",
]
