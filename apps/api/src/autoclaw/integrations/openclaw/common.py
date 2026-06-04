from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from autoclaw.platform.file_entrypoints import load_yaml_mapping, resolved_input_path
from mcp.server.transport_security import TransportSecuritySettings

_DEFAULT_ALLOWED_HOSTS = (
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
)
_DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1",
    "http://127.0.0.1:*",
    "http://localhost",
    "http://localhost:*",
)


def default_transport_security(
    *,
    host: str,
    extra_hosts: Sequence[str] = (),
    extra_origins: Sequence[str] = (),
) -> TransportSecuritySettings:
    allowed_hosts = list(dict.fromkeys((*_DEFAULT_ALLOWED_HOSTS, host, f"{host}:*", *extra_hosts)))
    allowed_origins = list(
        dict.fromkeys(
            (
                *_DEFAULT_ALLOWED_ORIGINS,
                f"http://{host}",
                f"http://{host}:*",
                *extra_origins,
            )
        )
    )
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def resolved_path(path_value: str) -> Path:
    return resolved_input_path(path_value)


__all__ = [
    "default_transport_security",
    "load_yaml_mapping",
    "resolved_path",
]
