from __future__ import annotations

from pathlib import Path

from app.db import ArtifactCurrentPointerModel
from app.db.models.runtime import RuntimeEffectModel
from app.runtime.effects.keys import (
    RuntimeEffectKind,
    effect_priority,
    file_copy_effect_key,
    runtime_effect_dedupe_key,
    runtime_effect_id,
)
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from sqlalchemy import select
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


async def stage_pending_runtime_effect(
    *,
    session: AsyncSession,
    task_id: str,
    key: tuple[str, ...],
    effect_kind: RuntimeEffectKind,
    payload: dict[str, object],
) -> None:
    from app.db.models.runtime.common import utcnow

    now = utcnow()
    dedupe_key = runtime_effect_dedupe_key(key)
    row = await session.scalar(
        select(RuntimeEffectModel).where(RuntimeEffectModel.dedupe_key == dedupe_key)
    )
    if row is None:
        session.add(
            RuntimeEffectModel(
                runtime_effect_id=runtime_effect_id(key),
                task_id=task_id,
                dedupe_key=dedupe_key,
                effect_kind=effect_kind,
                payload_json=payload,
                priority=effect_priority(effect_kind),
                requested_revision=1,
                processed_revision=0,
                attempt_count=0,
                effect_state="pending",
                available_at=now,
                last_error=None,
                created_at=now,
                updated_at=now,
            )
        )
        return
    row.task_id = task_id
    row.effect_kind = effect_kind
    row.payload_json = payload
    row.priority = effect_priority(effect_kind)
    row.requested_revision += 1
    row.effect_state = "pending"
    row.available_at = now
    row.completed_at = None
    row.failed_at = None
    row.last_error = None
    row.updated_at = now


async def stage_pending_file_copy_effect(
    *,
    pointer: ArtifactCurrentPointerModel,
    session: AsyncSession,
) -> None:
    await stage_pending_runtime_effect(
        session=session,
        task_id=pointer.task_id,
        key=file_copy_effect_key(Path(pointer.current_path)),
        effect_kind="file_copy",
        payload={
            "source_path": pointer.current_path,
            "destination_path": pointer.current_path,
        },
    )


__all__ = [
    "artifact_handoff_workflow",
    "stage_pending_file_copy_effect",
    "stage_pending_runtime_effect",
]
