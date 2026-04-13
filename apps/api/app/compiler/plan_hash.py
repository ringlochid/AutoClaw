import hashlib
import json

from app.schemas.compiler import NormalizedCompiledPlan


def compute_plan_hash(plan: NormalizedCompiledPlan) -> str:
    payload = json.dumps(
        plan.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
