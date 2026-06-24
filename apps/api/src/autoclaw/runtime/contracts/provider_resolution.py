from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import ProviderLaunchFailureStage, ProviderName


class ProviderResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    requested_provider: ProviderName
    resolved_provider: ProviderName


class ProviderLaunchFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    code: Literal["provider_launch_failed"] = "provider_launch_failed"
    requested_provider: ProviderName
    attempted_provider: ProviderName
    stage: ProviderLaunchFailureStage
    message: RuntimeSchemaText


__all__ = [
    "ProviderLaunchFailure",
    "ProviderResolution",
]
