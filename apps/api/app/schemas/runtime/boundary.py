from pydantic import BaseModel, ConfigDict

from app.runtime.contracts import EgressBoundary
from app.schemas.runtime.flow import RuntimeFlowRead
from app.schemas.runtime.refs import CheckpointFileRef


class BoundaryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boundary: EgressBoundary


class BoundaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted_boundary: EgressBoundary
    flow: RuntimeFlowRead
    latest_checkpoint_ref: CheckpointFileRef | None = None


__all__ = ["BoundaryRead", "BoundaryWrite"]
