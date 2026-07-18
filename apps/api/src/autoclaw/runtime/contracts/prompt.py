from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autoclaw.definitions.contracts.workflow import NodeKind
from autoclaw.runtime.contracts.capabilities import EffectiveCapabilitySet
from autoclaw.runtime.contracts.command_runs import CommandRunRecord
from autoclaw.runtime.contracts.human_requests import HumanRequestRead
from autoclaw.runtime.contracts.primitives import RuntimeText, TaskIdentifier
from autoclaw.runtime.contracts.projection import (
    AssignmentProjection,
    CheckpointProjection,
    ManifestProjection,
    ResolvedNodeContext,
)


class PromptFamily(StrEnum):
    WORKER_DISPATCH = "worker_dispatch_prompt"
    PARENT_ROOT_DISPATCH = "parent_root_dispatch_prompt"


class PromptSendMode(StrEnum):
    FULL_PROMPT = "full_prompt"


PROMPT_FAMILY_NODE_KINDS: dict[PromptFamily, tuple[NodeKind, ...]] = {
    PromptFamily.WORKER_DISPATCH: (NodeKind.WORKER,),
    PromptFamily.PARENT_ROOT_DISPATCH: (
        NodeKind.PARENT,
        NodeKind.ROOT,
    ),
}


class PromptRenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_family: PromptFamily
    send_mode: PromptSendMode
    task_id: TaskIdentifier
    current_node: ResolvedNodeContext
    manifest: ManifestProjection
    assignment: AssignmentProjection
    latest_checkpoint: CheckpointProjection | None = None
    human_request_continuation_context: HumanRequestRead | None = None
    command_run_continuation_context: CommandRunRecord | None = None
    effective_capabilities: EffectiveCapabilitySet = Field(default_factory=EffectiveCapabilitySet)

    @model_validator(mode="after")
    def validate_prompt_legality(self) -> PromptRenderRequest:
        validate_prompt_render_request(self)
        return self


class PromptTransportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    send_mode: PromptSendMode
    instructions_text: RuntimeText | None = None
    input_text: RuntimeText

    @model_validator(mode="after")
    def validate_transport_shape(self) -> PromptTransportRequest:
        if self.instructions_text is None:
            raise ValueError("full_prompt transport requests require instructions_text")
        return self


class RenderedPromptBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_family: PromptFamily
    send_mode: PromptSendMode
    instructions_text: RuntimeText | None = None
    input_text: RuntimeText
    full_markdown: RuntimeText
    content_hash: RuntimeText

    @model_validator(mode="after")
    def validate_bundle_shape(self) -> RenderedPromptBundle:
        if self.instructions_text is None:
            raise ValueError("full_prompt bundles require instructions_text")
        return self


class PersistedPromptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch_id: RuntimeText
    node_key: RuntimeText
    attempt_id: RuntimeText
    assignment_key: RuntimeText
    prompt_name: PromptFamily
    send_mode: PromptSendMode
    rendered_markdown_path: Path
    transport_request_path: Path
    content_hash: RuntimeText
    transport_request_hash: RuntimeText
    rendered_at: datetime
    transport_request: PromptTransportRequest

    @model_validator(mode="after")
    def validate_record_shape(self) -> PersistedPromptRecord:
        if self.transport_request.send_mode != self.send_mode:
            raise ValueError("persisted prompt record send_mode must match transport_request")
        return self


def validate_prompt_render_request(request: PromptRenderRequest) -> None:
    validate_prompt_family_for_node_kind(
        prompt_family=request.prompt_family,
        node_kind=request.current_node.node_kind,
    )
    if request.assignment.node_key != request.current_node.node_key:
        raise ValueError(
            f"assignment node_key '{request.assignment.node_key}' does not match current node "
            f"'{request.current_node.node_key}'"
        )
    if request.manifest.current_context.current_node_key != request.current_node.node_key:
        raise ValueError(
            "manifest current_context.current_node_key "
            f"'{request.manifest.current_context.current_node_key}' does not match current node "
            f"'{request.current_node.node_key}'"
        )


def validate_prompt_family_for_node_kind(
    prompt_family: PromptFamily,
    node_kind: NodeKind,
) -> None:
    allowed_node_kinds = PROMPT_FAMILY_NODE_KINDS[prompt_family]
    if node_kind in allowed_node_kinds:
        return
    expected_family = prompt_family_for_node_kind(node_kind)
    allowed_node_kind_values = ", ".join(kind.value for kind in allowed_node_kinds)
    raise ValueError(
        f"prompt_family '{prompt_family.value}' is illegal for node_kind "
        f"'{node_kind.value}'; expected '{expected_family.value}' for this node kind "
        f"and one of [{allowed_node_kind_values}] for the supplied prompt family"
    )


def prompt_family_for_node_kind(node_kind: NodeKind) -> PromptFamily:
    if node_kind == NodeKind.WORKER:
        return PromptFamily.WORKER_DISPATCH
    return PromptFamily.PARENT_ROOT_DISPATCH


__all__ = [
    "PROMPT_FAMILY_NODE_KINDS",
    "PersistedPromptRecord",
    "PromptFamily",
    "PromptRenderRequest",
    "PromptSendMode",
    "PromptTransportRequest",
    "RenderedPromptBundle",
    "prompt_family_for_node_kind",
    "validate_prompt_family_for_node_kind",
    "validate_prompt_render_request",
]
