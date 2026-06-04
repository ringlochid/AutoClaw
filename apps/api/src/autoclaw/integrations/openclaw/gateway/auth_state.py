from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field

from autoclaw.integrations.openclaw.gateway.protocol import OpenClawProtocolModel


class StoredDeviceToken(OpenClawProtocolModel):
    device_token: str
    role: str
    scopes: tuple[str, ...]


class StoredGatewayAuthState(OpenClawProtocolModel):
    stored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    primary_token: StoredDeviceToken | None = None
    bootstrap_tokens: tuple[StoredDeviceToken, ...] = ()


def load_gateway_auth_state(path: Path) -> StoredGatewayAuthState | None:
    if not path.is_file():
        return None
    return StoredGatewayAuthState.model_validate_json(path.read_text(encoding="utf-8"))


def save_gateway_auth_state(path: Path, state: StoredGatewayAuthState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = state.model_dump(mode="json", by_alias=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "StoredDeviceToken",
    "StoredGatewayAuthState",
    "load_gateway_auth_state",
    "save_gateway_auth_state",
]
