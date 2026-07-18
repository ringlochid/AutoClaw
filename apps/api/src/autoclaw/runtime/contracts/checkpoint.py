from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import CheckpointKind, CheckpointOutcome
from autoclaw.runtime.contracts.refs import CheckpointFileRef

_CHECKPOINT_SUMMARY_MAX_LENGTH = 2_048
_CHECKPOINT_NEXT_STEP_MAX_LENGTH = 1_024
_CHECKPOINT_LIST_ENTRY_MAX_LENGTH = 1_024
_CHECKPOINT_LIST_MAX_LENGTH = 16
_VAGUE_TEXT_FINGERPRINTS = frozenset(("", "todo", "tbd"))

_CheckpointSummaryText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=_CHECKPOINT_SUMMARY_MAX_LENGTH,
    ),
]
_CheckpointNextStepText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=_CHECKPOINT_NEXT_STEP_MAX_LENGTH,
    ),
]
_CheckpointListEntryText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=_CHECKPOINT_LIST_ENTRY_MAX_LENGTH,
    ),
]


class CheckpointHandoffRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: _CheckpointSummaryText
    next_step: _CheckpointNextStepText
    blockers: tuple[_CheckpointListEntryText, ...] = Field(
        default=(),
        max_length=_CHECKPOINT_LIST_MAX_LENGTH,
    )
    risks: tuple[_CheckpointListEntryText, ...] = Field(
        default=(),
        max_length=_CHECKPOINT_LIST_MAX_LENGTH,
    )

    @field_validator("summary", "next_step")
    @classmethod
    def reject_vague_scalar(cls, value: str) -> str:
        if _text_fingerprint(value) in _VAGUE_TEXT_FINGERPRINTS:
            raise ValueError("checkpoint handoff text must contain meaningful text")
        return value

    @field_validator("blockers", "risks")
    @classmethod
    def reject_vague_list_entries(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(_text_fingerprint(value) in _VAGUE_TEXT_FINGERPRINTS for value in values):
            raise ValueError("checkpoint handoff entries must contain meaningful text")
        return values


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


def _text_fingerprint(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


__all__ = [
    "CheckpointHandoffRead",
    "CheckpointRead",
    "CheckpointWrite",
    "CheckpointWriteBody",
    "ProducedArtifactClaim",
    "TransientSurfaceWrite",
]
