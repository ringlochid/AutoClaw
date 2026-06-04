from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from autoclaw.schemas.runtime.common import RuntimeSchemaText
from autoclaw.schemas.runtime.contracts import CheckpointKind, CheckpointOutcome
from autoclaw.schemas.runtime.refs import CheckpointFileRef


class CheckpointHandoffRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RuntimeSchemaText
    next_step: RuntimeSchemaText
    blockers: tuple[RuntimeSchemaText, ...] = ()
    risks: tuple[RuntimeSchemaText, ...] = ()


class ProducedArtifactClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["artifact"] = "artifact"
    slot: RuntimeSchemaText
    path: Path


class TransientSurfaceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    description: RuntimeSchemaText


class CheckpointWriteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint_kind: CheckpointKind
    outcome: CheckpointOutcome | None = None
    handoff: CheckpointHandoffRead
    produced_artifacts: tuple[ProducedArtifactClaim, ...] = ()
    transient_surfaces: tuple[TransientSurfaceWrite, ...] = ()
    task_memory_search_hints: tuple[RuntimeSchemaText, ...] = ()

    @model_validator(mode="after")
    def validate_checkpoint_kind(self) -> Self:
        if self.checkpoint_kind == CheckpointKind.PROGRESS and self.outcome is not None:
            raise ValueError("progress checkpoints must not declare a terminal outcome")
        if self.checkpoint_kind == CheckpointKind.TERMINAL and self.outcome is None:
            raise ValueError("terminal checkpoints require an outcome")
        artifact_slots = [artifact.slot for artifact in self.produced_artifacts]
        if len(artifact_slots) != len(set(artifact_slots)):
            raise ValueError("produced_artifacts must not repeat the same slot in one checkpoint")
        return self


class CheckpointWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint: CheckpointWriteBody


class CheckpointRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: RuntimeSchemaText
    checkpoint_id: RuntimeSchemaText
    checkpoint_ref: CheckpointFileRef
    latest_checkpoint_ref: CheckpointFileRef


__all__ = [
    "CheckpointHandoffRead",
    "CheckpointRead",
    "CheckpointWrite",
    "CheckpointWriteBody",
    "ProducedArtifactClaim",
    "TransientSurfaceWrite",
]
