from __future__ import annotations

from autoclaw.definitions.contracts.workflow import WorkflowDefinitionFile
from autoclaw.persistence import ArtifactCurrentPointerModel
from sqlalchemy.ext.asyncio import AsyncSession


def artifact_handoff_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "artifact-handoff-review",
            "description": "Validate assign_child against controller-backed artifact truth.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "implement_change",
                        "role": "engineer",
                        "description": "Implement the bounded change.",
                        "produces": {
                            "artifacts": [
                                {
                                    "slot": "change_patch",
                                    "description": "Bounded code patch for the task.",
                                },
                                {
                                    "slot": "verification_report",
                                    "description": "Verification report for the patch.",
                                },
                            ]
                        },
                    },
                    {
                        "id": "review_change",
                        "role": "researcher",
                        "description": "Review the current implementation evidence.",
                        "consumes": {
                            "artifacts": [
                                {"slot": "change_patch"},
                                {"slot": "verification_report"},
                            ]
                        },
                    },
                ],
            },
        }
    )


async def current_artifact_pointer(
    *,
    session: AsyncSession,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> ArtifactCurrentPointerModel | None:
    return await session.get(
        ArtifactCurrentPointerModel,
        f"artifact-current-pointer.{task_id}.{owner_node_key}.{slot}",
    )


__all__ = [
    "artifact_handoff_workflow",
    "current_artifact_pointer",
]
