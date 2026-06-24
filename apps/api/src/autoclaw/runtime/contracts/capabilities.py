from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.contracts.primitives import CapabilityDecision


class HumanRequestCapabilitySet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    direction: CapabilityDecision = CapabilityDecision.DENY
    approval: CapabilityDecision = CapabilityDecision.DENY
    input: CapabilityDecision = CapabilityDecision.DENY
    review: CapabilityDecision = CapabilityDecision.DENY


class EffectiveCapabilitySet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    execution_scope: Literal["dispatch", "human_request_open", "command_run_start"]
    human_request: HumanRequestCapabilitySet = Field(default_factory=HumanRequestCapabilitySet)
    command_run: CapabilityDecision = CapabilityDecision.DENY


class CapabilityRejectionError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    code: Literal[OperationFailureCode.CAPABILITY_REJECTED] = (
        OperationFailureCode.CAPABILITY_REJECTED
    )
    capability: RuntimeSchemaText
    message: RuntimeSchemaText
    next_legal_action: RuntimeSchemaText | None = None


__all__ = [
    "CapabilityRejectionError",
    "EffectiveCapabilitySet",
    "HumanRequestCapabilitySet",
]
