from __future__ import annotations

from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BudgetCounterModel, PolicyRevisionModel
from app.runtime.control.clock import utc_now


async def consume_assignment_budget(
    session: AsyncSession,
    *,
    budget_family: str,
    limit_field: str,
    policy_key: str | None,
    policy_revision_no: int | None,
    flow_id: str,
    flow_node_id: str,
    assignment_id: str,
    attempt_id: str | None,
) -> None:
    initial_limit = await _policy_budget_limit(
        session,
        policy_key=policy_key,
        policy_revision_no=policy_revision_no,
        limit_field=limit_field,
    )
    if initial_limit is None:
        return

    budget_counter = await session.get(
        BudgetCounterModel,
        _budget_counter_id(
            budget_family=budget_family,
            assignment_id=assignment_id,
        ),
    )
    if budget_counter is None:
        budget_counter = BudgetCounterModel(
            budget_counter_id=_budget_counter_id(
                budget_family=budget_family,
                assignment_id=assignment_id,
            ),
            budget_family=budget_family,
            scope_kind="assignment",
            flow_id=flow_id,
            flow_node_id=flow_node_id,
            assignment_id=assignment_id,
            attempt_id=attempt_id,
            initial_limit=initial_limit,
            remaining=initial_limit,
            exhausted_at=utc_now() if initial_limit == 0 else None,
        )
        session.add(budget_counter)
        await session.flush()

    budget_counter.flow_id = flow_id
    budget_counter.flow_node_id = flow_node_id
    budget_counter.assignment_id = assignment_id
    budget_counter.attempt_id = attempt_id

    if budget_counter.remaining <= 0:
        budget_counter.exhausted_at = budget_counter.exhausted_at or utc_now()
        raise ValueError(f"{budget_family.replace('_', ' ')} budget exhausted for this path")

    budget_counter.remaining -= 1
    budget_counter.lock_version += 1
    budget_counter.updated_at = utc_now()
    if budget_counter.remaining == 0:
        budget_counter.exhausted_at = budget_counter.updated_at


def _json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


async def _policy_budget_limit(
    session: AsyncSession,
    *,
    policy_key: str | None,
    policy_revision_no: int | None,
    limit_field: str,
) -> int | None:
    if policy_key is None or policy_revision_no is None:
        return None
    policy_revision = await session.scalar(
        select(PolicyRevisionModel).where(
            PolicyRevisionModel.policy_key == policy_key,
            PolicyRevisionModel.revision_no == policy_revision_no,
        )
    )
    if policy_revision is None:
        raise ValueError(
            f"missing policy revision '{policy_key}@{policy_revision_no}' for budget validation"
        )
    budget_spec = _json_mapping(policy_revision.content_json).get("budget_spec")
    if not isinstance(budget_spec, dict):
        return None
    value = budget_spec.get(limit_field)
    return int(value) if isinstance(value, int) else None


def _budget_counter_id(*, budget_family: str, assignment_id: str) -> str:
    return f"budget.{budget_family}.{assignment_id}"
