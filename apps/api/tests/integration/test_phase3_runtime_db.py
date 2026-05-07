from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from app import cli
from app.config import get_settings
from app.db import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    AttemptProducedRefModel,
    BudgetCounterModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime import (
    CheckpointKind,
    CheckpointOutcome,
    EgressBoundary,
    ParentRootToolName,
    accept_boundary,
    call_parent_tool,
    continue_runtime_flow,
    record_checkpoint,
    runtime_flow_read,
)
from app.runtime.projection import build_dispatch_prompt
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from app.schemas.runtime import (
    AddChildPayload,
    AssignChildPayload,
    AssignChildSuccess,
    AssignmentIntent,
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ChildNodeDraft,
    ChildNodePatch,
    ParentToolCall,
    ProducedArtifactClaim,
    ReleaseBlockedPayload,
    ReleaseGreenPayload,
    RemoveChildPayload,
    UpdateChildPayload,
)
from app.schemas.runtime import (
    BoundaryWrite as BoundaryWriteSchema,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.runtime_seed import (
    launch_seeded_runtime,
    task_compose_payload,
)


async def _prepare_runtime_db(tmp_path: Path) -> tuple[Path, Path]:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli._cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=None,
            host="127.0.0.1",
            port=8123,
            log_level="INFO",
            api_key="api-test-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=False,
            json=False,
        )
    )
    return config_path, data_dir


async def _continue_runtime(
    session: AsyncSession,
    *,
    task_id: str,
    expected_active_flow_revision_id: str,
) -> Any:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    assert flow is not None
    if flow.current_open_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        if (
            dispatch.fenced_at is None
            and dispatch.delivery_status == "accepted"
            and (
                dispatch.accepted_boundary is not None
                or dispatch.control_state == "abort_requested"
            )
        ):
            dispatch.delivery_status = "provider_completed"
    continued = await continue_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
    )
    await session.commit()
    return continued


def _root_blocked_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-blocked-release-review",
            "description": "Validate whole-flow blocked release semantics.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "investigate_blocker",
                        "role": "researcher",
                        "description": (
                            "Investigate the blocker and report whether work is blocked."
                        ),
                    }
                ],
            },
        }
    )


def _root_replan_publication_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-replan-publication-review",
            "description": "Validate same-attempt checkpoint and publication rebinding.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "decision_note",
                            "description": "Root decision note for the current turn.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "review_step",
                        "role": "researcher",
                        "description": "Review the current subtree state.",
                    }
                ],
            },
        }
    )


def _root_budget_rebind_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-budget-rebind-review",
            "description": "Validate child-assignment budget rebinding after structural adopt.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "implement_change",
                        "role": "researcher",
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
                    }
                ],
            },
        }
    )


async def test_phase3_structural_replan_and_assign_child_persist_lineage(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-lineage"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_lineage",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-lineage",
                )

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_phase3_lineage")
                )
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                initial_flow = await runtime_flow_read(session, "task_phase3_lineage")
                initial_revision_id = initial_flow.active_flow_revision_id
                assert initial_revision_id is not None

                initial_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == initial_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert initial_root_node is not None
                root_assignment_id = initial_root_node.current_assignment_id
                assert root_assignment_id is not None
                initial_root_assignment = await session.get(AssignmentModel, root_assignment_id)
                assert initial_root_assignment is not None
                initial_root_attempt_id = initial_root_assignment.current_attempt_id
                assert initial_root_attempt_id is not None
                initial_dispatch_id = flow.current_open_dispatch_id

                update_success = await call_parent_tool(
                    session,
                    "task_phase3_lineage",
                    ParentRootToolName.UPDATE_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.UPDATE_CHILD,
                        payload=UpdateChildPayload(
                            child_node_key="release_closure",
                            patch=ChildNodePatch(
                                description="Run the refreshed release closure check."
                            ),
                        ),
                        expected_structural_revision_id=initial_revision_id,
                    ),
                )
                await session.commit()

                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_phase3_lineage")
                )
                assert flow is not None
                updated_revision_id = update_success.flow.active_flow_revision_id
                assert updated_revision_id is not None
                updated_revision = await session.get(FlowRevisionModel, updated_revision_id)
                assert updated_revision is not None
                assert updated_revision.parent_flow_revision_id == initial_revision_id
                assert updated_revision.source_compiled_plan_id == flow.compiled_plan_id
                assert updated_revision.cause == "update_child"
                assert updated_revision.created_by_dispatch_id == flow.current_open_dispatch_id

                updated_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == updated_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert updated_root_node is not None
                assert updated_root_node.flow_id == flow.flow_id
                assert updated_root_node.flow_revision_id == updated_revision_id
                assert updated_root_node.current_assignment_id == root_assignment_id

                rebound_root_assignment = await session.get(AssignmentModel, root_assignment_id)
                assert rebound_root_assignment is not None
                assert rebound_root_assignment.flow_id == flow.flow_id
                assert rebound_root_assignment.flow_revision_id == updated_revision_id
                assert rebound_root_assignment.flow_node_id == updated_root_node.flow_node_id
                rebound_root_attempt = await session.get(AttemptModel, initial_root_attempt_id)
                assert rebound_root_attempt is not None
                assert rebound_root_attempt.flow_node_id == updated_root_node.flow_node_id
                rebound_root_dispatch = await session.get(DispatchTurnModel, initial_dispatch_id)
                assert rebound_root_dispatch is not None
                assert rebound_root_dispatch.flow_revision_id == updated_revision_id
                assert rebound_root_dispatch.flow_node_id == updated_root_node.flow_node_id

                add_success = await call_parent_tool(
                    session,
                    "task_phase3_lineage",
                    ParentRootToolName.ADD_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ADD_CHILD,
                        payload=AddChildPayload(
                            child=ChildNodeDraft.model_validate(
                                {
                                    "id": "qa_sweep",
                                    "role": "architect",
                                    "description": "Run a bounded QA sweep over the subtree.",
                                }
                            )
                        ),
                        expected_structural_revision_id=updated_revision_id,
                    ),
                )
                await session.commit()

                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_phase3_lineage")
                )
                assert flow is not None
                added_revision_id = add_success.flow.active_flow_revision_id
                assert added_revision_id is not None
                added_revision = await session.get(FlowRevisionModel, added_revision_id)
                assert added_revision is not None
                assert added_revision.parent_flow_revision_id == updated_revision_id
                assert added_revision.source_compiled_plan_id == flow.compiled_plan_id
                assert added_revision.cause == "add_child"
                assert added_revision.created_by_dispatch_id == flow.current_open_dispatch_id

                qa_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == added_revision_id,
                        FlowNodeModel.node_key == "qa_sweep",
                    )
                )
                assert qa_node is not None
                assert qa_node.flow_id == flow.flow_id
                assert qa_node.flow_revision_id == added_revision_id

                added_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == added_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert added_root_node is not None
                rebound_root_assignment = await session.get(AssignmentModel, root_assignment_id)
                assert rebound_root_assignment is not None
                assert rebound_root_assignment.flow_revision_id == added_revision_id
                assert rebound_root_assignment.flow_node_id == added_root_node.flow_node_id

                remove_success = await call_parent_tool(
                    session,
                    "task_phase3_lineage",
                    ParentRootToolName.REMOVE_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.REMOVE_CHILD,
                        payload=RemoveChildPayload(child_node_key="qa_sweep"),
                        expected_structural_revision_id=added_revision_id,
                    ),
                )
                await session.commit()

                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_phase3_lineage")
                )
                assert flow is not None
                removed_revision_id = remove_success.flow.active_flow_revision_id
                assert removed_revision_id is not None
                removed_revision = await session.get(FlowRevisionModel, removed_revision_id)
                assert removed_revision is not None
                assert removed_revision.parent_flow_revision_id == added_revision_id
                assert removed_revision.source_compiled_plan_id == flow.compiled_plan_id
                assert removed_revision.cause == "remove_child"
                assert removed_revision.created_by_dispatch_id == flow.current_open_dispatch_id

                removed_qa_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == removed_revision_id,
                        FlowNodeModel.node_key == "qa_sweep",
                    )
                )
                assert removed_qa_node is None

                removed_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == removed_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert removed_root_node is not None
                rebound_root_assignment = await session.get(AssignmentModel, root_assignment_id)
                assert rebound_root_assignment is not None
                assert rebound_root_assignment.flow_revision_id == removed_revision_id
                assert rebound_root_assignment.flow_node_id == removed_root_node.flow_node_id

                assign_success = await call_parent_tool(
                    session,
                    "task_phase3_lineage",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Stage the implementation subtree.",
                                instruction="Publish only the subtree assignment basis.",
                            ),
                        ),
                        expected_structural_revision_id=removed_revision_id,
                    ),
                )
                await session.commit()

                implementation_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == removed_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                assert implementation_node is not None

                assert isinstance(assign_success, AssignChildSuccess)
                staged_assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.assignment_key == assign_success.target_assignment_key
                    )
                )
                assert staged_assignment is not None
                assert staged_assignment.flow_id == flow.flow_id
                assert staged_assignment.flow_revision_id == removed_revision_id
                assert staged_assignment.flow_node_id == implementation_node.flow_node_id
                assert staged_assignment.created_by_dispatch_id == flow.current_open_dispatch_id
    finally:
        await dispose_db_engine()


async def test_phase3_structural_replan_rebinds_same_attempt_publication_and_checkpoint_lineage(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-replan-publication"
    workflow_definition = _root_replan_publication_workflow()

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_replan_publication",
                    task_root=task_root,
                    task_compose=task_compose_payload(workflow_definition.id),
                    compiler_version="phase-3-replan-publication",
                    workflow_definition=workflow_definition,
                )

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_phase3_replan_publication")
                )
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                initial_dispatch_id = flow.current_open_dispatch_id

                initial_flow = await runtime_flow_read(session, "task_phase3_replan_publication")
                initial_revision_id = initial_flow.active_flow_revision_id
                assert initial_revision_id is not None
                initial_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == initial_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert initial_root_node is not None
                assert initial_root_node.current_assignment_id is not None
                initial_assignment = await session.get(
                    AssignmentModel,
                    initial_root_node.current_assignment_id,
                )
                assert initial_assignment is not None
                assert initial_assignment.current_attempt_id is not None
                initial_attempt_id = initial_assignment.current_attempt_id

                note_v1 = task_root / "workspace" / "decision-note-v1.md"
                note_v1.parent.mkdir(parents=True, exist_ok=True)
                note_v1.write_text("decision note v1", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_phase3_replan_publication",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.PROGRESS,
                            outcome=None,
                            handoff=CheckpointHandoffRead(
                                summary="Recorded the first root decision note.",
                                next_step="Refresh the child structure before finalizing.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(
                                    slot="decision_note",
                                    path=note_v1,
                                ),
                            ),
                        )
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                updated = await call_parent_tool(
                    session,
                    "task_phase3_replan_publication",
                    ParentRootToolName.UPDATE_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.UPDATE_CHILD,
                        payload=UpdateChildPayload(
                            child_node_key="review_step",
                            patch=ChildNodePatch(
                                description="Refresh the review step after progress evidence."
                            ),
                        ),
                        expected_structural_revision_id=initial_revision_id,
                    ),
                )
                await session.commit()
                updated_revision_id = updated.flow.active_flow_revision_id
                assert updated_revision_id is not None

            async with session_factory() as session:
                updated_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == updated_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert updated_root_node is not None
                rebound_attempt = await session.get(AttemptModel, initial_attempt_id)
                assert rebound_attempt is not None
                assert rebound_attempt.flow_node_id == updated_root_node.flow_node_id
                rebound_dispatch = await session.get(DispatchTurnModel, initial_dispatch_id)
                assert rebound_dispatch is not None
                assert rebound_dispatch.flow_revision_id == updated_revision_id
                assert rebound_dispatch.flow_node_id == updated_root_node.flow_node_id

                checkpoints = list(
                    await session.scalars(
                        select(AttemptCheckpointModel)
                        .where(AttemptCheckpointModel.attempt_id == initial_attempt_id)
                        .order_by(AttemptCheckpointModel.recorded_at.asc())
                    )
                )
                assert checkpoints
                assert {checkpoint.flow_node_id for checkpoint in checkpoints} == {
                    updated_root_node.flow_node_id
                }

                publication_v1 = await session.scalar(
                    select(ArtifactPublicationModel).where(
                        ArtifactPublicationModel.task_id == "task_phase3_replan_publication",
                        ArtifactPublicationModel.owner_node_key == "root",
                        ArtifactPublicationModel.slot == "decision_note",
                        ArtifactPublicationModel.version == 1,
                    )
                )
                assert publication_v1 is not None
                assert publication_v1.flow_node_id == updated_root_node.flow_node_id
                current_pointer = await session.scalar(
                    select(ArtifactCurrentPointerModel).where(
                        ArtifactCurrentPointerModel.task_id == "task_phase3_replan_publication",
                        ArtifactCurrentPointerModel.owner_node_key == "root",
                        ArtifactCurrentPointerModel.slot == "decision_note",
                    )
                )
                assert current_pointer is not None
                assert current_pointer.flow_node_id == updated_root_node.flow_node_id

                note_v2 = task_root / "workspace" / "decision-note-v2.md"
                note_v2.write_text("decision note v2", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_phase3_replan_publication",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.PROGRESS,
                            outcome=None,
                            handoff=CheckpointHandoffRead(
                                summary="Recorded the refreshed root decision note.",
                                next_step="Keep the current root attempt open.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(
                                    slot="decision_note",
                                    path=note_v2,
                                ),
                            ),
                        )
                    ),
                )
                await session.commit()

                publication_v2 = await session.scalar(
                    select(ArtifactPublicationModel).where(
                        ArtifactPublicationModel.task_id == "task_phase3_replan_publication",
                        ArtifactPublicationModel.owner_node_key == "root",
                        ArtifactPublicationModel.slot == "decision_note",
                        ArtifactPublicationModel.version == 2,
                    )
                )
                assert publication_v2 is not None
                assert publication_v2.flow_node_id == updated_root_node.flow_node_id
                refreshed_pointer = await session.scalar(
                    select(ArtifactCurrentPointerModel).where(
                        ArtifactCurrentPointerModel.task_id == "task_phase3_replan_publication",
                        ArtifactCurrentPointerModel.owner_node_key == "root",
                        ArtifactCurrentPointerModel.slot == "decision_note",
                    )
                )
                assert refreshed_pointer is not None
                assert refreshed_pointer.current_version == 2
                assert refreshed_pointer.flow_node_id == updated_root_node.flow_node_id
    finally:
        await dispose_db_engine()


async def test_phase3_structural_replan_uses_relational_parent_child_authority(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-relational-replan"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_relational_replan",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-relational-replan",
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(session, "task_phase3_relational_replan")
                await call_parent_tool(
                    session,
                    "task_phase3_relational_replan",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Open the implementation subtree.",
                                instruction="Dispatch only the implementation subtree.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_relational_replan",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_relational_replan",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_phase3_relational_replan")
                )
                assert flow is not None
                active_revision_id = flow.active_flow_revision_id
                assert active_revision_id is not None

                subtree_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == active_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == active_revision_id,
                        FlowNodeModel.node_key == "investigate_issue",
                    )
                )
                assert subtree_node is not None
                assert child_node is not None

                child_node.parent_node_key = "root"
                subtree_node.child_node_keys_json = ["shadow_only_child"]
                await session.commit()

            async with session_factory() as session:
                current_flow = await runtime_flow_read(session, "task_phase3_relational_replan")
                update_success = await call_parent_tool(
                    session,
                    "task_phase3_relational_replan",
                    ParentRootToolName.UPDATE_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.UPDATE_CHILD,
                        payload=UpdateChildPayload(
                            child_node_key="implement_change",
                            patch=ChildNodePatch(
                                description="Refresh the implementation step after shadow drift."
                            ),
                        ),
                        expected_structural_revision_id=current_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                updated_revision_id = update_success.flow.active_flow_revision_id
                assert updated_revision_id is not None

            async with session_factory() as session:
                updated_subtree_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == updated_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                updated_child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == updated_revision_id,
                        FlowNodeModel.node_key == "implement_change",
                    )
                )
                assert updated_subtree_node is not None
                assert updated_child_node is not None
                assert updated_child_node.parent_node_key == "implementation_subtree"
                assert "shadow_only_child" not in updated_subtree_node.child_node_keys_json

                relational_child_keys = list(
                    await session.scalars(
                        select(FlowNodeModel.node_key)
                        .where(
                            FlowNodeModel.flow_revision_id == updated_revision_id,
                            FlowNodeModel.parent_flow_node_id == updated_subtree_node.flow_node_id,
                        )
                        .order_by(FlowNodeModel.order_index.asc())
                    )
                )
                assert updated_subtree_node.child_node_keys_json == relational_child_keys
    finally:
        await dispose_db_engine()


async def test_phase3_assign_child_uses_relational_direct_child_authority(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-relational-assign-child"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_relational_assign_child",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-relational-assign-child",
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(
                    session,
                    "task_phase3_relational_assign_child",
                )
                await call_parent_tool(
                    session,
                    "task_phase3_relational_assign_child",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Open the implementation subtree.",
                                instruction="Dispatch only the implementation subtree.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_relational_assign_child",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_relational_assign_child",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(
                        FlowModel.task_id == "task_phase3_relational_assign_child"
                    )
                )
                assert flow is not None
                active_revision_id = flow.active_flow_revision_id
                assert active_revision_id is not None

                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == active_revision_id,
                        FlowNodeModel.node_key == "implement_change",
                    )
                )
                assert child_node is not None
                child_node.parent_node_key = "root"
                await session.commit()

            async with session_factory() as session:
                implementation_flow = await runtime_flow_read(
                    session,
                    "task_phase3_relational_assign_child",
                )
                assign_success = await call_parent_tool(
                    session,
                    "task_phase3_relational_assign_child",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_issue",
                            assignment_intent=AssignmentIntent(
                                summary="Investigate the scoped issue.",
                                instruction="Publish the investigation findings.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                assert isinstance(assign_success, AssignChildSuccess)
                await session.commit()

                assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.assignment_key == assign_success.target_assignment_key
                    )
                )
                assert assignment is not None
                assert assignment.node_key == "investigate_issue"
    finally:
        await dispose_db_engine()


async def test_phase3_assign_child_blocks_open_overwrite_and_supersedes_closed_assignment(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-assign-child-overwrite"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_assign_child_overwrite",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-assign-child-overwrite",
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(
                    session,
                    "task_phase3_assign_child_overwrite",
                )
                await call_parent_tool(
                    session,
                    "task_phase3_assign_child_overwrite",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Open the implementation subtree.",
                                instruction="Dispatch only the implementation subtree.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_assign_child_overwrite",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_assign_child_overwrite",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                implementation_flow = await runtime_flow_read(
                    session,
                    "task_phase3_assign_child_overwrite",
                )
                first_assign = await call_parent_tool(
                    session,
                    "task_phase3_assign_child_overwrite",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_issue",
                            assignment_intent=AssignmentIntent(
                                summary="Investigate the scoped issue.",
                                instruction="Publish the investigation findings.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                assert isinstance(first_assign, AssignChildSuccess)
                await session.commit()

                flow = await session.scalar(
                    select(FlowModel).where(
                        FlowModel.task_id == "task_phase3_assign_child_overwrite"
                    )
                )
                assert flow is not None
                dispatch_id = flow.current_open_dispatch_id
                assert dispatch_id is not None
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                dispatch.staged_child_assignment_id = None
                dispatch.staged_continuation_kind = None
                await session.commit()

                with pytest.raises(
                    ValueError,
                    match="assign_child cannot overwrite open child assignment",
                ):
                    await call_parent_tool(
                        session,
                        "task_phase3_assign_child_overwrite",
                        ParentRootToolName.ASSIGN_CHILD,
                        ParentToolCall(
                            tool_name=ParentRootToolName.ASSIGN_CHILD,
                            payload=AssignChildPayload(
                                child_node_key="investigate_issue",
                                assignment_intent=AssignmentIntent(
                                    summary="Retry the same child while it is still open.",
                                    instruction="This must be rejected.",
                                ),
                            ),
                            expected_structural_revision_id=(
                                implementation_flow.active_flow_revision_id
                            ),
                        ),
                    )

                first_assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.assignment_key == first_assign.target_assignment_key
                    )
                )
                assert first_assignment is not None
                first_attempt = await session.get(AttemptModel, first_assign.target_attempt_id)
                assert first_attempt is not None
                first_attempt.status = "succeeded"
                first_attempt.terminal_outcome = "green"
                first_attempt.closed_at = first_attempt.created_at
                await session.commit()

                second_assign = await call_parent_tool(
                    session,
                    "task_phase3_assign_child_overwrite",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_issue",
                            assignment_intent=AssignmentIntent(
                                summary="Stage a legal superseding child assignment.",
                                instruction="Publish the new investigation findings.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                assert isinstance(second_assign, AssignChildSuccess)
                await session.commit()

                assert second_assign.target_assignment_key != first_assign.target_assignment_key
                assert first_assignment.superseded_at is not None
    finally:
        await dispose_db_engine()


async def test_phase3_assign_child_rejects_missing_backing_current_artifact_file(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-assign-child-missing-backing-file"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_assign_child_missing_backing_file",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-assign-child-missing-backing-file",
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                )
                await call_parent_tool(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Open the implementation subtree.",
                                instruction="Dispatch only the implementation subtree.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_assign_child_missing_backing_file",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                implementation_flow = await runtime_flow_read(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                )
                investigate_success = await call_parent_tool(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_issue",
                            assignment_intent=AssignmentIntent(
                                summary="Investigate the scoped issue.",
                                instruction="Publish only the current findings report.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert investigate_success.target_node_key == "investigate_issue"

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_assign_child_missing_backing_file",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "investigate_issue"

                findings_source = task_root / "workspace" / "findings_report.md"
                findings_source.write_text("bounded findings", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Investigation completed.",
                                next_step="Parent should review the findings.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(
                                    slot="findings_report",
                                    path=findings_source,
                                ),
                            ),
                        )
                    ),
                )
                returned_parent = await accept_boundary(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                returned_parent = await _continue_runtime(
                    session,
                    task_id="task_phase3_assign_child_missing_backing_file",
                    expected_active_flow_revision_id=returned_parent.flow.active_flow_revision_id,
                )
                assert returned_parent.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                implementation_flow = await runtime_flow_read(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                )
                await call_parent_tool(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the scoped change.",
                                instruction="Publish the implementation evidence.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_assign_child_missing_backing_file",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implement_change"

                patch_source = task_root / "workspace" / "change_patch.diff"
                patch_source.write_text("diff --git a b", encoding="utf-8")
                verification_source = task_root / "workspace" / "verification_report.md"
                verification_source.write_text("verification ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Implementation completed.",
                                next_step=(
                                    "Parent should review the current patch "
                                    "and verification evidence."
                                ),
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_source),
                                ProducedArtifactClaim(
                                    slot="verification_report",
                                    path=verification_source,
                                ),
                            ),
                        )
                    ),
                )
                implemented = await accept_boundary(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                implemented = await _continue_runtime(
                    session,
                    task_id="task_phase3_assign_child_missing_backing_file",
                    expected_active_flow_revision_id=implemented.flow.active_flow_revision_id,
                )
                assert implemented.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                review_flow = await runtime_flow_read(
                    session,
                    "task_phase3_assign_child_missing_backing_file",
                )
                flow = await session.scalar(
                    select(FlowModel).where(
                        FlowModel.task_id == "task_phase3_assign_child_missing_backing_file"
                    )
                )
                assert flow is not None
                active_revision_id = flow.active_flow_revision_id
                assert active_revision_id is not None
                review_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == active_revision_id,
                        FlowNodeModel.node_key == "review_change",
                    )
                )
                assert review_node is not None
                assert review_node.consumes_json is not None
                artifact_selectors = cast(
                    list[dict[str, Any]],
                    review_node.consumes_json["artifacts"],
                )
                assert any(selector["slot"] == "change_patch" for selector in artifact_selectors)

                publication = await session.scalar(
                    select(ArtifactPublicationModel).where(
                        ArtifactPublicationModel.task_id
                        == "task_phase3_assign_child_missing_backing_file",
                        ArtifactPublicationModel.owner_node_key == "implement_change",
                        ArtifactPublicationModel.slot == "change_patch",
                        ArtifactPublicationModel.version == 1,
                    )
                )
                assert publication is not None
                artifact_path = Path(publication.path)
                assert await asyncio.to_thread(artifact_path.is_file)
                await asyncio.to_thread(artifact_path.unlink)

                with pytest.raises(
                    ValueError,
                    match="missing current artifact for slot 'change_patch'",
                ):
                    await call_parent_tool(
                        session,
                        "task_phase3_assign_child_missing_backing_file",
                        ParentRootToolName.ASSIGN_CHILD,
                        ParentToolCall(
                            tool_name=ParentRootToolName.ASSIGN_CHILD,
                            payload=AssignChildPayload(
                                child_node_key="review_change",
                                assignment_intent=AssignmentIntent(
                                    summary="Review the current implementation evidence.",
                                    instruction="Publish only the bounded review report.",
                                ),
                            ),
                            expected_structural_revision_id=review_flow.active_flow_revision_id,
                        ),
                    )
    finally:
        await dispose_db_engine()


async def test_phase3_parent_worker_flow_and_replan_state(tmp_path: Path) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_2026_0042",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-runtime-db",
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(session, "task_2026_0042")
                assign_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Start the implementation subtree.",
                                instruction="Stage the current implementation subtree only.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert assign_success.target_node_key == "implementation_subtree"
                with pytest.raises(
                    ValueError,
                    match="add_child is illegal after staging a child assignment",
                ):
                    await call_parent_tool(
                        session,
                        "task_2026_0042",
                        ParentRootToolName.ADD_CHILD,
                        ParentToolCall(
                            tool_name=ParentRootToolName.ADD_CHILD,
                            payload=AddChildPayload(
                                child=ChildNodeDraft.model_validate(
                                    {
                                        "id": "illegal_extra_child",
                                        "role": "architect",
                                        "description": "Should not stage after assign_child.",
                                    }
                                )
                            ),
                            expected_structural_revision_id=initial_flow.active_flow_revision_id,
                        ),
                    )

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implementation_subtree"
                previous_revision = yielded.active_flow_revision_id

                add_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.ADD_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ADD_CHILD,
                        payload=AddChildPayload(
                            child=ChildNodeDraft.model_validate(
                                {
                                    "id": "qa_sweep",
                                    "role": "architect",
                                    "description": "Run a bounded QA sweep over current evidence.",
                                    "consumes": {
                                        "artifacts": [
                                            {"slot": "change_patch"},
                                            {"slot": "verification_report"},
                                            {"slot": "review_report"},
                                        ]
                                    },
                                    "produces": {
                                        "artifacts": [
                                            {
                                                "slot": "qa_report",
                                                "description": "QA report for the subtree.",
                                                "file_hint": "qa_report.md",
                                            }
                                        ]
                                    },
                                }
                            )
                        ),
                        expected_structural_revision_id=previous_revision,
                    ),
                )
                await session.commit()
                assert add_success.flow.active_flow_revision_id != previous_revision
                assert "qa_sweep" in (task_root / "_runtime" / "workflow-manifest.md").read_text(
                    encoding="utf-8"
                )

                remove_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.REMOVE_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.REMOVE_CHILD,
                        payload=RemoveChildPayload(child_node_key="qa_sweep"),
                        expected_structural_revision_id=add_success.flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert remove_success.target_node_key == "qa_sweep"
                assert "qa_sweep" not in (
                    task_root / "_runtime" / "workflow-manifest.md"
                ).read_text(encoding="utf-8")

                investigate_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_issue",
                            assignment_intent=AssignmentIntent(
                                summary="Investigate the auth refresh regression.",
                                instruction="Publish only the current findings report.",
                            ),
                        ),
                        expected_structural_revision_id=remove_success.flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert investigate_success.target_node_key == "investigate_issue"

            async with session_factory() as session:
                worker_flow = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                worker_flow = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=worker_flow.flow.active_flow_revision_id,
                )
                assert worker_flow.current_node_key == "investigate_issue"

                findings_source = task_root / "workspace" / "findings_report.md"
                findings_source.write_text("bounded findings", encoding="utf-8")
                checkpoint = await record_checkpoint(
                    session,
                    "task_2026_0042",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Investigation completed.",
                                next_step="Parent should review the findings.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(
                                    slot="findings_report",
                                    path=findings_source,
                                ),
                            ),
                        )
                    ),
                )
                previous_attempt_id = worker_flow.active_attempt_id
                assert previous_attempt_id is not None
                green = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                green = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=green.flow.active_flow_revision_id,
                )
                assert checkpoint.latest_checkpoint_ref.path.is_file()
                assert green.current_node_key == "implementation_subtree"
                assert (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / "investigate_issue"
                    / "findings_report"
                    / "current.json"
                ).is_file()

            async with session_factory() as session:
                implementation_flow = await runtime_flow_read(session, "task_2026_0042")
                implement_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the scoped auth-refresh fix.",
                                instruction="Publish only the patch and verification report.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert implement_success.target_node_key == "implement_change"

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implement_change"

                patch_source = task_root / "workspace" / "change_patch.diff"
                patch_source.write_text("diff --git a b", encoding="utf-8")
                verification_source = task_root / "workspace" / "verification_report.md"
                verification_source.write_text("verification ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_2026_0042",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Implementation completed.",
                                next_step=(
                                    "Parent should review the current patch "
                                    "and verification evidence."
                                ),
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_source),
                                ProducedArtifactClaim(
                                    slot="verification_report",
                                    path=verification_source,
                                ),
                            ),
                        )
                    ),
                )
                implemented = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                implemented = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=implemented.flow.active_flow_revision_id,
                )
                assert implemented.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                implementation_flow = await runtime_flow_read(session, "task_2026_0042")
                review_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="review_change",
                            assignment_intent=AssignmentIntent(
                                summary="Review the current implementation evidence.",
                                instruction="Publish only the bounded review report.",
                            ),
                        ),
                        expected_structural_revision_id=implementation_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert review_success.target_node_key == "review_change"

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "review_change"

                review_source = task_root / "workspace" / "review_report.md"
                review_source.write_text("review ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_2026_0042",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Review completed.",
                                next_step="Parent can release the implementation subtree.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="review_report", path=review_source),
                            ),
                        )
                    ),
                )
                reviewed = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                reviewed = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=reviewed.flow.active_flow_revision_id,
                )
                assert reviewed.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                subtree_flow = await runtime_flow_read(session, "task_2026_0042")
                await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.RELEASE_GREEN,
                    ParentToolCall(
                        tool_name=ParentRootToolName.RELEASE_GREEN,
                        payload=ReleaseGreenPayload(),
                        expected_structural_revision_id=subtree_flow.active_flow_revision_id,
                    ),
                )
                await record_checkpoint(
                    session,
                    "task_2026_0042",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Implementation subtree is complete.",
                                next_step="Root should run the final release closure worker.",
                            ),
                        )
                    ),
                )
                released_subtree = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                released_subtree = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=released_subtree.flow.active_flow_revision_id,
                )
                assert released_subtree.current_node_key == "root"

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0042")
                with pytest.raises(
                    ValueError,
                    match="child node 'release_closure' has no current assignment",
                ):
                    await call_parent_tool(
                        session,
                        "task_2026_0042",
                        ParentRootToolName.RELEASE_GREEN,
                        ParentToolCall(
                            tool_name=ParentRootToolName.RELEASE_GREEN,
                            payload=ReleaseGreenPayload(),
                            expected_structural_revision_id=root_flow.active_flow_revision_id,
                        ),
                    )
                release_success = await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="release_closure",
                            assignment_intent=AssignmentIntent(
                                summary="Run the final release closure.",
                                instruction="Publish only the final closure report.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                assert release_success.target_node_key == "release_closure"

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "release_closure"

                closure_source = task_root / "workspace" / "closure_report.md"
                closure_source.write_text("closure ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_2026_0042",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Release closure completed.",
                                next_step="Root can make the final release decision.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="closure_report", path=closure_source),
                            ),
                        )
                    ),
                )
                closure_green = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                closure_green = await _continue_runtime(
                    session,
                    task_id="task_2026_0042",
                    expected_active_flow_revision_id=closure_green.flow.active_flow_revision_id,
                )
                assert closure_green.current_node_key == "root"

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0042")
                await call_parent_tool(
                    session,
                    "task_2026_0042",
                    ParentRootToolName.RELEASE_GREEN,
                    ParentToolCall(
                        tool_name=ParentRootToolName.RELEASE_GREEN,
                        payload=ReleaseGreenPayload(),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await record_checkpoint(
                    session,
                    "task_2026_0042",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Root verified release evidence and closed the flow.",
                                next_step="No further runtime work is required.",
                            ),
                        )
                    ),
                )
                completed = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                assert completed.flow.status.value == "succeeded"
                assert completed.flow.current_node_key == "root"
                assert completed.flow.active_attempt_id == "attempt.task_2026_0042.root.01"
                assert (task_root / "_runtime" / "workflow-manifest.md").is_file()
    finally:
        await dispose_db_engine()


async def test_phase3_minimal_root_closure_remains_readable(tmp_path: Path) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_2026_0045",
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-3-runtime-db",
                )

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0045")
                await call_parent_tool(
                    session,
                    "task_2026_0045",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the bounded change.",
                                instruction="Publish the patch and verification evidence only.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0045",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0045",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implement_change"

                patch_source = task_root / "workspace" / "minimal_change_patch.diff"
                patch_source.write_text("diff --git c d", encoding="utf-8")
                verification_source = task_root / "workspace" / "minimal_verification_report.md"
                verification_source.write_text("minimal verification ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_2026_0045",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Minimal implementation completed.",
                                next_step=(
                                    "Root should verify the bounded change and close the flow."
                                ),
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_source),
                                ProducedArtifactClaim(
                                    slot="verification_report",
                                    path=verification_source,
                                ),
                            ),
                        )
                    ),
                )
                returned_root = await accept_boundary(
                    session,
                    "task_2026_0045",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                returned_root = await _continue_runtime(
                    session,
                    task_id="task_2026_0045",
                    expected_active_flow_revision_id=returned_root.flow.active_flow_revision_id,
                )
                assert returned_root.current_node_key == "root"

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0045")
                await call_parent_tool(
                    session,
                    "task_2026_0045",
                    ParentRootToolName.RELEASE_GREEN,
                    ParentToolCall(
                        tool_name=ParentRootToolName.RELEASE_GREEN,
                        payload=ReleaseGreenPayload(),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await record_checkpoint(
                    session,
                    "task_2026_0045",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Root verified the minimal bounded evidence.",
                                next_step="Close the flow.",
                            ),
                        )
                    ),
                )
                completed = await accept_boundary(
                    session,
                    "task_2026_0045",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                assert completed.flow.status.value == "succeeded"
                assert completed.flow.current_node_key == "root"
                reread = await runtime_flow_read(session, "task_2026_0045")
                assert reread.status.value == "succeeded"
                assert reread.current_node_key == "root"
    finally:
        await dispose_db_engine()


async def test_phase3_release_precondition_is_dispatch_local_not_continuation_state(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_2026_0046",
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-3-runtime-db",
                )

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0046")
                await call_parent_tool(
                    session,
                    "task_2026_0046",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the bounded change.",
                                instruction="Publish the patch and verification evidence only.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0046",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0046",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implement_change"

            async with session_factory() as session:
                patch_source = task_root / "workspace" / "dispatch_local_patch.diff"
                patch_source.write_text("diff --git e f", encoding="utf-8")
                verification_source = task_root / "workspace" / "dispatch_local_verification.md"
                verification_source.write_text("dispatch local verification ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_2026_0046",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Minimal implementation completed.",
                                next_step=(
                                    "Root should verify the bounded change and close the flow."
                                ),
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_source),
                                ProducedArtifactClaim(
                                    slot="verification_report",
                                    path=verification_source,
                                ),
                            ),
                        )
                    ),
                )
                returned_root = await accept_boundary(
                    session,
                    "task_2026_0046",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                returned_root = await _continue_runtime(
                    session,
                    task_id="task_2026_0046",
                    expected_active_flow_revision_id=returned_root.flow.active_flow_revision_id,
                )
                assert returned_root.current_node_key == "root"

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0046")
                child_assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.task_id == "task_2026_0046",
                        AssignmentModel.node_key != "root",
                    )
                )
                assert child_assignment is not None
                child_assignment.consumes_json = [
                    *child_assignment.consumes_json,
                    {
                        "kind": "criteria",
                        "slot": "stale_release_green_basis",
                        "path": str(task_root / "context" / "criteria" / "stale-release-green.md"),
                        "description": (
                            "Injected stale evidence to prove release currentness revalidation."
                        ),
                    },
                ]
                with pytest.raises(ValueError, match="current surfaced evidence"):
                    await call_parent_tool(
                        session,
                        "task_2026_0046",
                        ParentRootToolName.RELEASE_GREEN,
                        ParentToolCall(
                            tool_name=ParentRootToolName.RELEASE_GREEN,
                            payload=ReleaseGreenPayload(),
                            expected_structural_revision_id=root_flow.active_flow_revision_id,
                        ),
                    )
                child_assignment.consumes_json = child_assignment.consumes_json[:-1]
                await call_parent_tool(
                    session,
                    "task_2026_0046",
                    ParentRootToolName.RELEASE_GREEN,
                    ParentToolCall(
                        tool_name=ParentRootToolName.RELEASE_GREEN,
                        payload=ReleaseGreenPayload(),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                dispatch = await session.scalar(
                    select(DispatchTurnModel)
                    .where(
                        DispatchTurnModel.task_id == "task_2026_0046",
                        DispatchTurnModel.node_key == "root",
                        DispatchTurnModel.closed_at.is_(None),
                    )
                    .order_by(DispatchTurnModel.rendered_at.desc())
                )
                assert dispatch is not None
                assert dispatch.staged_continuation_kind is None
                assert dispatch.release_precondition_kind == "release_green"
                root_dispatch_id = dispatch.dispatch_id
                await session.commit()

            async with session_factory() as session:
                await record_checkpoint(
                    session,
                    "task_2026_0046",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Root verified the minimal bounded evidence.",
                                next_step="Close the flow.",
                            ),
                        )
                    ),
                )
                completed = await accept_boundary(
                    session,
                    "task_2026_0046",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                closed_dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
                assert closed_dispatch is not None
                descendant_refs = closed_dispatch.release_precondition_descendant_refs_json
                assert descendant_refs is not None
                assert any(
                    ref["kind"] == "checkpoint" and "implement_change" in str(ref["path"])
                    for ref in descendant_refs
                )
                assert any(
                    ref["kind"] == "artifact" and ref.get("slot") == "change_patch"
                    for ref in descendant_refs
                )
                assert any(
                    ref["kind"] == "artifact" and ref.get("slot") == "verification_report"
                    for ref in descendant_refs
                )
                assert completed.flow.status.value == "succeeded"
    finally:
        await dispose_db_engine()


async def test_phase3_record_checkpoint_defers_artifact_and_projection_files_until_commit(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_2026_0047",
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-3-runtime-db",
                )

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0047")
                assign = await call_parent_tool(
                    session,
                    "task_2026_0047",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the bounded change.",
                                instruction="Publish the patch and verification evidence only.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                assert isinstance(assign, AssignChildSuccess)
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0047",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0047",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                attempt_id = yielded.active_attempt_id
                assert attempt_id is not None

            async with session_factory() as session:
                patch_v1 = task_root / "workspace" / "change_patch_v1.diff"
                patch_v1.write_text("diff --git g h", encoding="utf-8")
                patch_v2 = task_root / "workspace" / "change_patch_v2.diff"
                patch_v2.write_text("diff --git g h v2", encoding="utf-8")
                verification_source = task_root / "workspace" / "verification_v1.md"
                verification_source.write_text("verification ok", encoding="utf-8")

                await record_checkpoint(
                    session,
                    "task_2026_0047",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.PROGRESS,
                            handoff=CheckpointHandoffRead(
                                summary="Published an initial patch draft.",
                                next_step="Finish verification and publish the final patch.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_v1),
                            ),
                        )
                    ),
                )
                patch_v1_destination = (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / "implement_change"
                    / "change_patch"
                    / "change_patch.v01.diff"
                )
                assert not patch_v1_destination.exists()

                await record_checkpoint(
                    session,
                    "task_2026_0047",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Published the final patch and verification note.",
                                next_step="Return to root for release review.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_v2),
                                ProducedArtifactClaim(
                                    slot="verification_report",
                                    path=verification_source,
                                ),
                            ),
                        )
                    ),
                )
                patch_v2_destination = (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / "implement_change"
                    / "change_patch"
                    / "change_patch.v02.diff"
                )
                verification_destination = (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / "implement_change"
                    / "verification_report"
                    / "verification_report.v01.md"
                )
                assert not patch_v2_destination.exists()
                assert not verification_destination.exists()

                checkpoints = list(
                    await session.scalars(
                        select(AttemptCheckpointModel)
                        .where(AttemptCheckpointModel.attempt_id == attempt_id)
                        .order_by(
                            AttemptCheckpointModel.recorded_at.asc(),
                            AttemptCheckpointModel.checkpoint_id.asc(),
                        )
                    )
                )
                assert len(checkpoints) == 2
                latest_checkpoint = checkpoints[-1]
                assert latest_checkpoint.produced_artifact_claims_json == [
                    {"kind": "artifact", "slot": "change_patch", "path": str(patch_v2)},
                    {
                        "kind": "artifact",
                        "slot": "verification_report",
                        "path": str(verification_source),
                    },
                ]
                assert [ref["slot"] for ref in latest_checkpoint.produced_artifacts_json] == [
                    "change_patch",
                    "verification_report",
                ]
                assert [ref["version"] for ref in latest_checkpoint.produced_artifacts_json] == [
                    2,
                    1,
                ]
                worker_assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.assignment_key == assign.target_assignment_key
                    )
                )
                assert worker_assignment is not None

                final_patch_publication = await session.scalar(
                    select(ArtifactPublicationModel).where(
                        ArtifactPublicationModel.task_id == "task_2026_0047",
                        ArtifactPublicationModel.flow_node_id == worker_assignment.flow_node_id,
                        ArtifactPublicationModel.owner_node_key == "implement_change",
                        ArtifactPublicationModel.slot == "change_patch",
                        ArtifactPublicationModel.version == 2,
                    )
                )
                assert final_patch_publication is not None
                assert final_patch_publication.supersedes_version == 1
                assert final_patch_publication.supersedes_path == str(patch_v1_destination)

                current_pointer = await session.scalar(
                    select(ArtifactCurrentPointerModel).where(
                        ArtifactCurrentPointerModel.task_id == "task_2026_0047",
                        ArtifactCurrentPointerModel.owner_node_key == "implement_change",
                        ArtifactCurrentPointerModel.slot == "change_patch",
                    )
                )
                assert current_pointer is not None
                assert current_pointer.flow_node_id == worker_assignment.flow_node_id
                assert current_pointer.current_path == str(patch_v2_destination)
                assert current_pointer.supersedes_path == str(patch_v1_destination)

                produced_ref = await session.scalar(
                    select(AttemptProducedRefModel).where(
                        AttemptProducedRefModel.attempt_id == attempt_id,
                        AttemptProducedRefModel.slot == "change_patch",
                        AttemptProducedRefModel.version == 2,
                    )
                )
                assert produced_ref is not None
                assert produced_ref.owner_node_key == "implement_change"
                assert produced_ref.assignment_key == assign.target_assignment_key
                assert produced_ref.became_current is True

                latest_checkpoint_projection = (
                    task_root / "_runtime" / "attempts" / attempt_id / "latest-checkpoint.md"
                )
                assert not latest_checkpoint_projection.exists()

                await accept_boundary(
                    session,
                    "task_2026_0047",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                assert patch_v1_destination.is_file()
                assert patch_v2_destination.is_file()
                assert verification_destination.is_file()
                assert latest_checkpoint_projection.is_file()
                assert (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / "implement_change"
                    / "change_patch"
                    / "current.json"
                ).is_file()
    finally:
        await dispose_db_engine()


async def test_phase3_record_checkpoint_rejects_second_terminal_checkpoint_on_open_attempt(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-single-terminal-checkpoint"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_single_terminal_checkpoint",
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-3-runtime-db",
                )

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_single_terminal_checkpoint")
                await call_parent_tool(
                    session,
                    "task_single_terminal_checkpoint",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the bounded change.",
                                instruction="Publish the final patch only once.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_single_terminal_checkpoint",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                await _continue_runtime(
                    session,
                    task_id="task_single_terminal_checkpoint",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )

            async with session_factory() as session:
                await record_checkpoint(
                    session,
                    "task_single_terminal_checkpoint",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Published the final bounded result.",
                                next_step="Return to the parent review node.",
                            ),
                        )
                    ),
                )
                with pytest.raises(
                    ValueError,
                    match="attempt already has a terminal checkpoint",
                ):
                    await record_checkpoint(
                        session,
                        "task_single_terminal_checkpoint",
                        CheckpointWrite(
                            checkpoint=CheckpointWriteBody(
                                checkpoint_kind=CheckpointKind.TERMINAL,
                                outcome=CheckpointOutcome.GREEN,
                                handoff=CheckpointHandoffRead(
                                    summary="Tried to overwrite the terminal handoff.",
                                    next_step="This should be rejected.",
                                ),
                            )
                        ),
                    )
    finally:
        await dispose_db_engine()


async def test_phase3_retry_creates_new_attempt_with_checkpoint_consume_ref(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_2026_0043",
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-3-runtime-db",
                )

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_2026_0043")
                await call_parent_tool(
                    session,
                    "task_2026_0043",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Repair the auth-refresh bug.",
                                instruction="Publish a bounded patch and retry-safe evidence.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_2026_0043",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_2026_0043",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implement_change"

            async with session_factory() as session:
                patch_source = task_root / "workspace" / "change_patch.diff"
                patch_source.write_text("diff --git a b", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_2026_0043",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.RETRY,
                            handoff=CheckpointHandoffRead(
                                summary="Retry is required after a partial patch.",
                                next_step=(
                                    "Retry the same assignment with the prior checkpoint in view."
                                ),
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(
                                    slot="change_patch",
                                    path=patch_source,
                                ),
                            ),
                        )
                    ),
                )
                retry_boundary = await accept_boundary(
                    session,
                    "task_2026_0043",
                    BoundaryWriteSchema(boundary=EgressBoundary.RETRY),
                )
                await session.commit()
                retry_boundary = await _continue_runtime(
                    session,
                    task_id="task_2026_0043",
                    expected_active_flow_revision_id=retry_boundary.flow.active_flow_revision_id,
                )
                assert retry_boundary.current_node_key == "implement_change"
                assert retry_boundary.active_attempt_id is not None
                previous_attempt_id = "attempt.task_2026_0043.implement_change.01"
                assert retry_boundary.active_attempt_id != previous_attempt_id
                retry_dispatch = await session.scalar(
                    select(DispatchTurnModel)
                    .where(
                        DispatchTurnModel.task_id == "task_2026_0043",
                        DispatchTurnModel.node_key == "implement_change",
                        DispatchTurnModel.closed_at.is_(None),
                    )
                    .order_by(DispatchTurnModel.rendered_at.desc())
                )
                assert retry_dispatch is not None
                retry_prompt = await asyncio.to_thread(
                    Path(retry_dispatch.prompt_path).read_text,
                    encoding="utf-8",
                )
                assert "## Consumed Durable Refs" in retry_prompt
                assert f"{previous_attempt_id}/latest-checkpoint.md" in retry_prompt
    finally:
        await dispose_db_engine()


async def test_phase3_rerenders_historical_dispatch_from_dispatch_lineage(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-rerender"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_rerender_history",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-rerender-history",
                )
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_rerender_history")
                )
                assert flow is not None
                root_dispatch_id = flow.current_open_dispatch_id
                assert root_dispatch_id is not None

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(session, "task_rerender_history")
                await call_parent_tool(
                    session,
                    "task_rerender_history",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Stage only the unique child review path.",
                                instruction="Do not mutate the historical root prompt.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_rerender_history",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                assert yielded.flow.current_node_key == "root"

            async with session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
                assert dispatch is not None
                bundle, record = await build_dispatch_prompt(
                    session,
                    "task_rerender_history",
                    dispatch,
                )
                assert record.node_key == "root"
                assert "Investigate and fix the auth refresh regression." in bundle.full_markdown
                assert "Stage only the unique child review path." not in bundle.full_markdown
    finally:
        await dispose_db_engine()


async def test_phase3_rerenders_historical_parent_dispatch_without_later_child_checkpoint(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-rerender-child-checkpoint"
    workflow_definition = _root_blocked_workflow()

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_rerender_child_checkpoint",
                    task_root=task_root,
                    task_compose=task_compose_payload(workflow_definition.id),
                    compiler_version="phase-3-rerender-child-checkpoint",
                    workflow_definition=workflow_definition,
                )
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_rerender_child_checkpoint")
                )
                assert flow is not None
                root_dispatch_id = flow.current_open_dispatch_id
                assert root_dispatch_id is not None

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(session, "task_rerender_child_checkpoint")
                await call_parent_tool(
                    session,
                    "task_rerender_child_checkpoint",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_blocker",
                            assignment_intent=AssignmentIntent(
                                summary="Investigate the blocker.",
                                instruction="Return blocked truth if the worker is blocked.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_rerender_child_checkpoint",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_rerender_child_checkpoint",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                child_attempt_id = yielded.active_attempt_id
                assert child_attempt_id is not None

            async with session_factory() as session:
                await record_checkpoint(
                    session,
                    "task_rerender_child_checkpoint",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.BLOCKED,
                            handoff=CheckpointHandoffRead(
                                summary="The worker is blocked.",
                                next_step="Root must decide whether the whole flow is blocked.",
                            ),
                        )
                    ),
                )
                await accept_boundary(
                    session,
                    "task_rerender_child_checkpoint",
                    BoundaryWriteSchema(boundary=EgressBoundary.BLOCKED),
                )
                await session.commit()

            async with session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
                assert dispatch is not None
                bundle, record = await build_dispatch_prompt(
                    session,
                    "task_rerender_child_checkpoint",
                    dispatch,
                )
                assert record.node_key == "root"
                assert child_attempt_id not in bundle.full_markdown
                assert "The worker is blocked." not in bundle.full_markdown
    finally:
        await dispose_db_engine()


async def test_phase3_parent_prompt_uses_relational_child_authority_when_shadows_drift(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-relational-prompt"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_relational_prompt",
                    task_root=task_root,
                    task_compose=task_compose_payload("normal-parent-first-release"),
                    compiler_version="phase-3-relational-prompt",
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(session, "task_relational_prompt")
                await call_parent_tool(
                    session,
                    "task_relational_prompt",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implementation_subtree",
                            assignment_intent=AssignmentIntent(
                                summary="Open the implementation subtree.",
                                instruction="Dispatch only the implementation subtree.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_relational_prompt",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_relational_prompt",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                parent_flow = await runtime_flow_read(session, "task_relational_prompt")
                await call_parent_tool(
                    session,
                    "task_relational_prompt",
                    ParentRootToolName.ADD_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ADD_CHILD,
                        payload=AddChildPayload(
                            child=ChildNodeDraft.model_validate(
                                {
                                    "id": "qa_sweep",
                                    "role": "architect",
                                    "description": "Run a bounded QA sweep over the subtree.",
                                }
                            )
                        ),
                        expected_structural_revision_id=parent_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                parent_flow = await runtime_flow_read(session, "task_relational_prompt")
                await call_parent_tool(
                    session,
                    "task_relational_prompt",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="qa_sweep",
                            assignment_intent=AssignmentIntent(
                                summary="Run the bounded QA sweep.",
                                instruction="Return the QA result to the parent subtree.",
                            ),
                        ),
                        expected_structural_revision_id=parent_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_relational_prompt",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_relational_prompt",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                child_attempt_id = yielded.active_attempt_id
                assert child_attempt_id is not None
                assert yielded.current_node_key == "qa_sweep"

            async with session_factory() as session:
                await record_checkpoint(
                    session,
                    "task_relational_prompt",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="QA sweep completed.",
                                next_step="Parent should review the QA result.",
                            ),
                        )
                    ),
                )
                returned_parent = await accept_boundary(
                    session,
                    "task_relational_prompt",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                returned_parent = await _continue_runtime(
                    session,
                    task_id="task_relational_prompt",
                    expected_active_flow_revision_id=returned_parent.flow.active_flow_revision_id,
                )
                assert returned_parent.current_node_key == "implementation_subtree"

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_relational_prompt")
                )
                assert flow is not None
                active_revision_id = flow.active_flow_revision_id
                assert active_revision_id is not None

                root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == active_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == active_revision_id,
                        FlowNodeModel.node_key == "qa_sweep",
                    )
                )
                assert root_node is not None
                assert child_node is not None

                child_node.parent_node_key = "root"
                root_node.child_node_keys_json = ["shadow_only_child"]
                await session.commit()

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_relational_prompt")
                )
                assert flow is not None
                dispatch_id = flow.current_open_dispatch_id
                assert dispatch_id is not None
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                bundle, record = await build_dispatch_prompt(
                    session,
                    "task_relational_prompt",
                    dispatch,
                )
                assert record.node_key == "implementation_subtree"
                assert f"{child_attempt_id}/latest-checkpoint.md" in bundle.full_markdown
                assert "QA sweep completed." in bundle.full_markdown
    finally:
        await dispose_db_engine()


async def test_phase3_structural_replan_rebinds_child_assignment_budget_counter(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-budget-rebind"
    workflow_definition = _root_budget_rebind_workflow()

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_phase3_budget_rebind",
                    task_root=task_root,
                    task_compose=task_compose_payload(workflow_definition.id),
                    compiler_version="phase-3-budget-rebind",
                    workflow_definition=workflow_definition,
                )

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_phase3_budget_rebind")
                await call_parent_tool(
                    session,
                    "task_phase3_budget_rebind",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="implement_change",
                            assignment_intent=AssignmentIntent(
                                summary="Implement the bounded change.",
                                instruction="Publish the patch and verification evidence only.",
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_phase3_budget_rebind",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_phase3_budget_rebind",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "implement_change"

            async with session_factory() as session:
                patch_source = task_root / "workspace" / "budget-rebind-patch.diff"
                patch_source.write_text("diff --git budget rebind", encoding="utf-8")
                verification_source = task_root / "workspace" / "budget-rebind-verification.md"
                verification_source.write_text("budget rebind verification ok", encoding="utf-8")
                await record_checkpoint(
                    session,
                    "task_phase3_budget_rebind",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.GREEN,
                            handoff=CheckpointHandoffRead(
                                summary="Minimal implementation completed.",
                                next_step="Return to root for structural refresh.",
                            ),
                            produced_artifacts=(
                                ProducedArtifactClaim(slot="change_patch", path=patch_source),
                                ProducedArtifactClaim(
                                    slot="verification_report",
                                    path=verification_source,
                                ),
                            ),
                        )
                    ),
                )
                returned_root = await accept_boundary(
                    session,
                    "task_phase3_budget_rebind",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                returned_root = await _continue_runtime(
                    session,
                    task_id="task_phase3_budget_rebind",
                    expected_active_flow_revision_id=returned_root.flow.active_flow_revision_id,
                )
                assert returned_root.current_node_key == "root"

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_phase3_budget_rebind")
                root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == root_flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert root_node is not None
                assert root_node.current_assignment_id is not None
                root_assignment = await session.get(
                    AssignmentModel, root_node.current_assignment_id
                )
                assert root_assignment is not None
                budget_counter = await session.get(
                    BudgetCounterModel,
                    f"budget.child_assignment.{root_assignment.assignment_id}",
                )
                assert budget_counter is not None
                assert budget_counter.flow_node_id == root_node.flow_node_id

                updated = await call_parent_tool(
                    session,
                    "task_phase3_budget_rebind",
                    ParentRootToolName.UPDATE_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.UPDATE_CHILD,
                        payload=UpdateChildPayload(
                            child_node_key="implement_change",
                            patch=ChildNodePatch(
                                description="Refresh the implementation step after child return."
                            ),
                        ),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()
                updated_root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == updated.flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert updated_root_node is not None

                rebound_budget_counter = await session.get(
                    BudgetCounterModel,
                    f"budget.child_assignment.{root_assignment.assignment_id}",
                )
                assert rebound_budget_counter is not None
                assert rebound_budget_counter.flow_node_id == updated_root_node.flow_node_id
    finally:
        await dispose_db_engine()


async def test_phase3_release_blocked_requires_current_root_and_whole_flow_blocked_basis(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-blocked"
    workflow_definition = _root_blocked_workflow()

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id="task_root_blocked",
                    task_root=task_root,
                    task_compose=task_compose_payload(workflow_definition.id),
                    compiler_version="phase-3-root-blocked",
                    workflow_definition=workflow_definition,
                )

            async with session_factory() as session:
                initial_flow = await runtime_flow_read(session, "task_root_blocked")
                await call_parent_tool(
                    session,
                    "task_root_blocked",
                    ParentRootToolName.ASSIGN_CHILD,
                    ParentToolCall(
                        tool_name=ParentRootToolName.ASSIGN_CHILD,
                        payload=AssignChildPayload(
                            child_node_key="investigate_blocker",
                            assignment_intent=AssignmentIntent(
                                summary="Investigate the blocker.",
                                instruction="Decide whether the whole flow is blocked.",
                            ),
                        ),
                        expected_structural_revision_id=initial_flow.active_flow_revision_id,
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                yielded = await accept_boundary(
                    session,
                    "task_root_blocked",
                    BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
                )
                await session.commit()
                yielded = await _continue_runtime(
                    session,
                    task_id="task_root_blocked",
                    expected_active_flow_revision_id=yielded.flow.active_flow_revision_id,
                )
                assert yielded.current_node_key == "investigate_blocker"

            async with session_factory() as session:
                await record_checkpoint(
                    session,
                    "task_root_blocked",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.BLOCKED,
                            handoff=CheckpointHandoffRead(
                                summary="The worker is blocked.",
                                next_step="Root must decide whether the whole flow is blocked.",
                            ),
                        )
                    ),
                )
                blocked = await accept_boundary(
                    session,
                    "task_root_blocked",
                    BoundaryWriteSchema(boundary=EgressBoundary.BLOCKED),
                )
                await session.commit()
                blocked = await _continue_runtime(
                    session,
                    task_id="task_root_blocked",
                    expected_active_flow_revision_id=blocked.flow.active_flow_revision_id,
                )
                assert blocked.current_node_key == "root"

            async with session_factory() as session:
                root_flow = await runtime_flow_read(session, "task_root_blocked")
                with pytest.raises(
                    ValueError,
                    match="current root basis to be terminal-blocked",
                ):
                    await call_parent_tool(
                        session,
                        "task_root_blocked",
                        ParentRootToolName.RELEASE_BLOCKED,
                        ParentToolCall(
                            tool_name=ParentRootToolName.RELEASE_BLOCKED,
                            payload=ReleaseBlockedPayload(),
                            expected_structural_revision_id=root_flow.active_flow_revision_id,
                        ),
                    )

                await record_checkpoint(
                    session,
                    "task_root_blocked",
                    CheckpointWrite(
                        checkpoint=CheckpointWriteBody(
                            checkpoint_kind=CheckpointKind.TERMINAL,
                            outcome=CheckpointOutcome.BLOCKED,
                            handoff=CheckpointHandoffRead(
                                summary="Root confirms the whole flow is blocked.",
                                next_step="Close the root dispatch as blocked.",
                            ),
                        )
                    ),
                )
                child_assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.task_id == "task_root_blocked",
                        AssignmentModel.node_key == "investigate_blocker",
                    )
                )
                assert child_assignment is not None
                child_assignment.consumes_json = [
                    *child_assignment.consumes_json,
                    {
                        "kind": "criteria",
                        "slot": "stale_root_blocked_basis",
                        "path": str(task_root / "context" / "criteria" / "stale-root-blocked.md"),
                        "description": "Injected stale evidence to prove currentness revalidation.",
                    },
                ]
                with pytest.raises(ValueError, match="current surfaced evidence"):
                    await call_parent_tool(
                        session,
                        "task_root_blocked",
                        ParentRootToolName.RELEASE_BLOCKED,
                        ParentToolCall(
                            tool_name=ParentRootToolName.RELEASE_BLOCKED,
                            payload=ReleaseBlockedPayload(),
                            expected_structural_revision_id=root_flow.active_flow_revision_id,
                        ),
                    )
                child_assignment.consumes_json = child_assignment.consumes_json[:-1]
                await call_parent_tool(
                    session,
                    "task_root_blocked",
                    ParentRootToolName.RELEASE_BLOCKED,
                    ParentToolCall(
                        tool_name=ParentRootToolName.RELEASE_BLOCKED,
                        payload=ReleaseBlockedPayload(),
                        expected_structural_revision_id=root_flow.active_flow_revision_id,
                    ),
                )
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_root_blocked")
                )
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                root_dispatch_id = flow.current_open_dispatch_id
                closed = await accept_boundary(
                    session,
                    "task_root_blocked",
                    BoundaryWriteSchema(boundary=EgressBoundary.BLOCKED),
                )
                await session.commit()
                closed_dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
                assert closed_dispatch is not None
                descendant_refs = closed_dispatch.release_precondition_descendant_refs_json
                assert descendant_refs is not None
                assert any(
                    ref["kind"] == "checkpoint" and "investigate_blocker" in str(ref["path"])
                    for ref in descendant_refs
                )
                assert closed.flow.status == "blocked"
    finally:
        await dispose_db_engine()
