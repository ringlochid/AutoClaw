from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from app.compiler import MappingRolePolicyLookup, NormalizedCompiledPlan
from app.runtime.contract_models.primitives import (
    RuntimeText,
    TaskComposeInput,
    TaskIdentifier,
    TaskRootPaths,
)
from app.runtime.contract_models.projection import (
    AssignmentProjection,
    CheckpointProjection,
    ManifestProjection,
    StructuralEditPaletteProjection,
)
from app.runtime.contract_models.prompt import PersistedPromptRecord, RenderedPromptBundle
from app.schemas.definitions.workflow import WorkflowDefinitionInput


class RuntimeBootstrapProjectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: TaskIdentifier
    active_flow_revision_id: RuntimeText
    attempt_id: RuntimeText
    assignment_key: RuntimeText
    dispatch_id: RuntimeText
    task_root: Path
    task_compose: TaskComposeInput
    workflow_definition: WorkflowDefinitionInput
    compiled_plan: NormalizedCompiledPlan
    role_policy_lookup: MappingRolePolicyLookup
    structural_edit_palette: StructuralEditPaletteProjection | None = None
    current_node_key: RuntimeText = "root"
    owner_node_key: RuntimeText | None = None
    assignment: AssignmentProjection | None = None
    latest_checkpoint: CheckpointProjection | None = None

    @model_validator(mode="after")
    def validate_workflow_alignment(self) -> RuntimeBootstrapProjectionInput:
        if self.task_compose.workflow.key != self.compiled_plan.workflow_key:
            raise ValueError(
                "task compose workflow key "
                f"'{self.task_compose.workflow.key}' does not match compiled plan "
                f"workflow key '{self.compiled_plan.workflow_key}'"
            )
        if self.workflow_definition.id != self.compiled_plan.workflow_key:
            raise ValueError(
                "workflow definition id "
                f"'{self.workflow_definition.id}' does not match compiled plan "
                f"workflow key '{self.compiled_plan.workflow_key}'"
            )
        return self


class RuntimeBootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    paths: TaskRootPaths
    manifest: ManifestProjection
    assignment: AssignmentProjection
    latest_checkpoint: CheckpointProjection | None = None
    prompt_bundle: RenderedPromptBundle
    prompt_record: PersistedPromptRecord


class RuntimeLaunchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: TaskIdentifier
    task_root: Path
    task_compose: TaskComposeInput
    compiler_version: RuntimeText = "phase-3-runtime"


__all__ = [
    "RuntimeBootstrapProjectionInput",
    "RuntimeBootstrapResult",
    "RuntimeLaunchInput",
]
