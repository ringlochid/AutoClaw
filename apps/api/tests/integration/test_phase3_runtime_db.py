from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from app import cli
from app.config import get_settings
from app.db import RuntimeBase
from app.db.session import dispose_db_engine, get_async_engine, get_session_factory
from app.runtime import (
    AssignmentProjection,
    CheckpointKind,
    CheckpointOutcome,
    EgressBoundary,
    EvidenceKind,
    EvidenceRef,
    ParentRootToolName,
    RuntimeBootstrapInput,
    accept_boundary,
    call_parent_tool,
    persist_bootstrap_runtime,
    record_checkpoint,
    runtime_flow_read,
)
from app.runtime.contracts import ProduceRequirement
from app.schemas.runtime import (
    AddChildPayload,
    AssignChildPayload,
    AssignmentIntent,
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ChildNodeDraft,
    ParentToolCall,
    ProducedArtifactClaim,
    ReleaseGreenPayload,
    RemoveChildPayload,
)
from app.schemas.runtime import (
    BoundaryWrite as BoundaryWriteSchema,
)
from tests.helpers.runtime_seed import (
    compile_seeded_workflow,
    load_seeded_lookup,
    load_workflow_definition,
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


async def _create_runtime_schema() -> None:
    engine = get_async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(RuntimeBase.metadata.create_all)


async def test_phase3_parent_worker_flow_and_replan_state(tmp_path: Path) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            await _create_runtime_schema()
            session_factory = get_session_factory()
            workflow_definition = load_workflow_definition("normal_parent_first_release")
            compiled_plan = compile_seeded_workflow(workflow_definition, revision_no=7)
            lookup = load_seeded_lookup()

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    RuntimeBootstrapInput(
                        task_id="task_2026_0042",
                        active_flow_revision_id="flowrev_0001",
                        attempt_id="attempt.root.01",
                        assignment_key="root.assign-01",
                        dispatch_id="dispatch.root.01",
                        task_root=task_root,
                        task_compose=task_compose_payload("normal-parent-first-release"),
                        workflow_definition=workflow_definition,
                        compiled_plan=compiled_plan,
                        role_policy_lookup=lookup,
                    ),
                )
                await session.commit()

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
                assert yielded.flow.current_node_key == "implementation_subtree"
                previous_revision = yielded.flow.active_flow_revision_id

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
                assert worker_flow.flow.current_node_key == "investigate_issue"

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
                assert checkpoint.latest_checkpoint_ref.path.is_file()
                green = await accept_boundary(
                    session,
                    "task_2026_0042",
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                assert green.flow.current_node_key == "implementation_subtree"
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
                assert yielded.flow.current_node_key == "implement_change"

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
                assert implemented.flow.current_node_key == "implementation_subtree"

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
                assert yielded.flow.current_node_key == "review_change"

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
                assert reviewed.flow.current_node_key == "implementation_subtree"

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
                assert released_subtree.flow.current_node_key == "root"

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
                assert yielded.flow.current_node_key == "release_closure"

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
                assert closure_green.flow.current_node_key == "root"

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
                assert completed.flow.active_attempt_id == "attempt.root.01"
                assert (task_root / "_runtime" / "workflow-manifest.md").is_file()
    finally:
        await dispose_db_engine()


async def test_phase3_minimal_root_closure_remains_readable(tmp_path: Path) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            await _create_runtime_schema()
            session_factory = get_session_factory()
            workflow_definition = load_workflow_definition("minimal_implement_change")
            compiled_plan = compile_seeded_workflow(workflow_definition, revision_no=4)

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    RuntimeBootstrapInput(
                        task_id="task_2026_0045",
                        active_flow_revision_id="flowrev_0004",
                        attempt_id="attempt.root.01",
                        assignment_key="root.assign-01",
                        dispatch_id="dispatch.root.01",
                        task_root=task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        workflow_definition=workflow_definition,
                        compiled_plan=compiled_plan,
                        role_policy_lookup=load_seeded_lookup(),
                    ),
                )
                await session.commit()

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
                assert yielded.flow.current_node_key == "implement_change"

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
                assert returned_root.flow.current_node_key == "root"

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


async def test_phase3_retry_creates_new_attempt_with_checkpoint_consume_ref(
    tmp_path: Path,
) -> None:
    config_path, _data_dir = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            await _create_runtime_schema()
            session_factory = get_session_factory()
            workflow_definition = load_workflow_definition("minimal_implement_change")
            compiled_plan = compile_seeded_workflow(workflow_definition, revision_no=4)

            assignment = AssignmentProjection(
                assignment_key="implement_change.assign-01",
                node_key="implement_change",
                summary="Repair the auth-refresh bug.",
                instruction="Publish a bounded patch and retry-safe evidence.",
                criteria=(
                    EvidenceRef(
                        kind=EvidenceKind.CRITERIA,
                        slot="implement_change_delivery_criteria",
                        path=(
                            task_root
                            / "context"
                            / "criteria"
                            / "implement_change_delivery_criteria.md"
                        ),
                        description="Implementation delivery criteria.",
                    ),
                ),
                produces=(
                    ProduceRequirement(
                        slot="change_patch",
                        description="Patch for the bounded change.",
                        file_hint="change_patch.diff",
                    ),
                ),
            )

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    RuntimeBootstrapInput(
                        task_id="task_2026_0043",
                        active_flow_revision_id="flowrev_0002",
                        attempt_id="attempt.implement_change.01",
                        assignment_key=assignment.assignment_key,
                        dispatch_id="dispatch.implement_change.01",
                        task_root=task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        workflow_definition=workflow_definition,
                        compiled_plan=compiled_plan,
                        role_policy_lookup=load_seeded_lookup(),
                        current_node_key="implement_change",
                        owner_node_key="implement_change",
                        assignment=assignment,
                    ),
                )
                await session.commit()

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
                assert retry_boundary.flow.current_node_key == "implement_change"
                assert retry_boundary.flow.active_attempt_id is not None
                assert retry_boundary.flow.active_attempt_id != "attempt.implement_change.01"
                assignment_markdown = (
                    task_root
                    / "_runtime"
                    / "attempts"
                    / retry_boundary.flow.active_attempt_id
                    / "assignment.md"
                ).read_text(encoding="utf-8")
                assert "kind: checkpoint" in assignment_markdown
                assert "attempt.implement_change.01/latest-checkpoint.md" in assignment_markdown
    finally:
        await dispose_db_engine()
