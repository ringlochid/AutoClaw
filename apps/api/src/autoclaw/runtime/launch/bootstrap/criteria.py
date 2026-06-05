from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.compiler import NormalizedCompiledNode
from autoclaw.persistence.models import AssignmentCriteriaRefModel, AssignmentModel
from autoclaw.runtime.contracts import TaskRootPaths
from autoclaw.runtime.ids import assignment_criteria_ref_id
from autoclaw.runtime.task_root import criteria_file_path


def build_node_criteria_json(
    *,
    paths: TaskRootPaths,
    node: NormalizedCompiledNode,
) -> list[dict[str, Any]]:
    return [
        criteria.model_dump(mode="json")
        | {
            "version": 1,
            "path": str(criteria_file_path(paths=paths, slot=criteria.slot, version=1)),
        }
        for criteria in node.criteria
    ]


def stage_assignment_criteria_refs(
    session: AsyncSession,
    assignment: AssignmentModel,
) -> None:
    for index, criteria in enumerate(assignment.criteria_json, start=1):
        slot = str(criteria["slot"])
        session.add(
            AssignmentCriteriaRefModel(
                assignment_criteria_ref_id=assignment_criteria_ref_id(
                    assignment.assignment_id,
                    slot,
                ),
                assignment_id=assignment.assignment_id,
                slot=slot,
                path=str(criteria["path"]),
                description=str(criteria["description"]),
                version=criteria.get("version"),
                order_index=index,
            )
        )
