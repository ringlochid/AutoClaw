from pydantic import BaseModel, ConfigDict

from autoclaw.schemas.runtime.contracts import EgressBoundary
from autoclaw.schemas.runtime.flow import RuntimeFlowRead
from autoclaw.schemas.runtime.refs import CheckpointFileRef


class BoundaryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boundary: EgressBoundary


class BoundaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted_boundary: EgressBoundary
    flow: RuntimeFlowRead
    latest_checkpoint_ref: CheckpointFileRef | None = None


__all__ = ["BoundaryRead", "BoundaryWrite"]
