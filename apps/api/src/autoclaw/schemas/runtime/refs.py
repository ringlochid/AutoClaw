from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autoclaw.schemas.runtime.common import RuntimeSchemaText

type FixedRuntimeFileKind = Literal[
    "manifest",
    "assignment",
    "checkpoint",
    "artifact_index",
    "transient_index",
]

type SupportRuntimeFileKind = Literal[
    "delivery_state",
    "continuity_state",
    "watchdog_state",
    "provider_events",
]

type OperatorSupportSurfaceKind = (
    FixedRuntimeFileKind
    | SupportRuntimeFileKind
    | Literal["artifact", "criteria", "doc", "wiki", "transient"]
)

_FIXED_RUNTIME_FILE_KIND_BY_FILENAME: dict[str, FixedRuntimeFileKind] = {
    "workflow-manifest.json": "manifest",
    "workflow-manifest.md": "manifest",
    "assignment.json": "assignment",
    "assignment.md": "assignment",
    "latest-checkpoint.json": "checkpoint",
    "latest-checkpoint.md": "checkpoint",
    "artifact-index.json": "artifact_index",
    "transient-index.json": "transient_index",
}
_SUPPORT_RUNTIME_FILE_KIND_BY_FILENAME: dict[str, SupportRuntimeFileKind] = {
    "delivery-state.json": "delivery_state",
    "continuity-state.json": "continuity_state",
    "watchdog-state.json": "watchdog_state",
    "provider-events.ndjson": "provider_events",
}


class WorkflowManifestRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class AssignmentFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class CheckpointFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class ArtifactIndexRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class TransientIndexRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["artifact"] = "artifact"
    slot: RuntimeSchemaText
    version: int = Field(ge=1)
    path: Path
    description: RuntimeSchemaText


class CriteriaRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["criteria"] = "criteria"
    slot: RuntimeSchemaText
    path: Path
    description: RuntimeSchemaText


class DocRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["doc"] = "doc"
    path: Path
    description: RuntimeSchemaText


class WikiRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["wiki"] = "wiki"
    path: Path
    description: RuntimeSchemaText


class TransientRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["transient"] = "transient"
    path: Path
    description: RuntimeSchemaText


class CheckpointConsumeRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["checkpoint"] = "checkpoint"
    path: Path
    description: RuntimeSchemaText


type AssignmentConsumeRef = CheckpointConsumeRef | ArtifactRef | DocRef | WikiRef


class SupportRuntimeFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: SupportRuntimeFileKind = "delivery_state"
    path: Path
    description: RuntimeSchemaText

    @model_validator(mode="before")
    @classmethod
    def infer_kind(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            payload: Any = value.model_dump(mode="python")
        elif isinstance(value, dict):
            payload = dict(value)
        else:
            return value
        if payload.get("kind") is None:
            inferred_kind = _SUPPORT_RUNTIME_FILE_KIND_BY_FILENAME.get(
                Path(str(payload.get("path"))).name
            )
            if inferred_kind is not None:
                payload["kind"] = inferred_kind
        return payload

    @model_validator(mode="after")
    def validate_kind(self) -> "SupportRuntimeFileRef":
        inferred_kind = _SUPPORT_RUNTIME_FILE_KIND_BY_FILENAME.get(self.path.name)
        if inferred_kind is None:
            raise ValueError(f"unsupported observability path '{self.path.name}'")
        if self.kind != inferred_kind:
            raise ValueError(
                f"path '{self.path.name}' must use observability kind '{inferred_kind}'"
            )
        return self


class OperatorSupportSurfaceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: OperatorSupportSurfaceKind
    path: Path
    description: RuntimeSchemaText
    slot: RuntimeSchemaText | None = None
    version: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_ref_shapes(cls, value: Any) -> Any:
        return _operator_support_payload(value)

    @model_validator(mode="after")
    def validate_shape(self) -> "OperatorSupportSurfaceRef":
        if self.kind == "artifact":
            if self.slot is None or self.version is None:
                raise ValueError("artifact operator refs require slot and version")
            return self
        if self.kind == "criteria":
            if self.slot is None:
                raise ValueError("criteria operator refs require slot")
            if self.version is not None:
                raise ValueError("criteria operator refs must not set version")
            return self
        if self.slot is not None:
            raise ValueError("only artifact or criteria operator refs may set slot")
        if self.version is not None:
            raise ValueError("only artifact operator refs may set version")
        inferred_kind = _operator_support_file_kind(self.path)
        if inferred_kind is not None and self.kind != inferred_kind:
            raise ValueError(
                f"path '{self.path.name}' must use operator ref kind '{inferred_kind}'"
            )
        return self


def _operator_support_file_kind(
    raw_path: object,
) -> FixedRuntimeFileKind | SupportRuntimeFileKind | None:
    if raw_path is None:
        return None
    filename = Path(str(raw_path)).name
    return _FIXED_RUNTIME_FILE_KIND_BY_FILENAME.get(
        filename
    ) or _SUPPORT_RUNTIME_FILE_KIND_BY_FILENAME.get(filename)


def _operator_support_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        payload: Any = value.model_dump(mode="python")
    elif isinstance(value, dict):
        payload = dict(value)
    else:
        return value
    inferred_kind = _operator_support_file_kind(payload.get("path"))
    if inferred_kind is not None and payload.get("kind") is None:
        payload["kind"] = inferred_kind
    return payload


__all__ = [
    "ArtifactIndexRef",
    "ArtifactRef",
    "AssignmentConsumeRef",
    "AssignmentFileRef",
    "CheckpointConsumeRef",
    "CheckpointFileRef",
    "CriteriaRef",
    "DocRef",
    "OperatorSupportSurfaceKind",
    "OperatorSupportSurfaceRef",
    "SupportRuntimeFileKind",
    "SupportRuntimeFileRef",
    "TransientIndexRef",
    "TransientRef",
    "WikiRef",
    "WorkflowManifestRef",
]
