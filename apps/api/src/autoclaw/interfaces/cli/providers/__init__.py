"""CLI-owned provider configuration and passive product readbacks."""

from autoclaw.interfaces.cli.providers.configuration import (
    ProviderConfigurationRequest,
    configure_provider,
    set_default_provider,
)
from autoclaw.interfaces.cli.providers.inspection import (
    collect_provider_check,
    collect_provider_definitions,
    collect_provider_statuses,
    invoke_provider_identity_action,
)

__all__ = [
    "ProviderConfigurationRequest",
    "collect_provider_check",
    "collect_provider_definitions",
    "collect_provider_statuses",
    "configure_provider",
    "invoke_provider_identity_action",
    "set_default_provider",
]
