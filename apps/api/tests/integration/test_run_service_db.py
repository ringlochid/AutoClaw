from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus, CheckpointStatus, DefinitionVersionStatus, WorkflowMode
from app.db.models.registry import WorkflowDefinition, WorkflowVersion
from app.db.models.runtime import CompiledPlan, CompiledPlanNode, Task
from app.schemas.runtime import (
    ApprovalCreate,
    AttemptCreate,
    CheckpointWrite,
    FlowCreate,
    FlowNodeCreate,
    RunCreate,
    TaskCreate,
)
from app.services.run_service import (
    create_approval,
    create_attempt,
    create_flow,
    create_flow_node,
    create_run,
    create_task,
    record_checkpoint,
)


async def test_run_service_round_trip_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    workflow_definition = WorkflowDefinition(key="default-bugfix", description="Default workflow")
    db_session.add(workflow_definition)
    await db_session.flush()

    workflow_version = WorkflowVersion(
        workflow_definition_id=workflow_definition.id,
        version=1,
        status=DefinitionVersionStatus.PUBLISHED,
        description="Published workflow",
        content={"id": "default-bugfix"},
    )
    db_session.add(workflow_version)
    await db_session.flush()

    compiled_plan = CompiledPlan(
        workflow_version_id=workflow_version.id,
        compiler_version="v0",
        plan_hash=f"test-plan-{uuid4()}",
        source_snapshot={"workflow": "default-bugfix"},
    )
    db_session.add(compiled_plan)
    await db_session.flush()

    compiled_plan_node = CompiledPlanNode(
        compiled_plan_id=compiled_plan.id,
        node_key="loop",
        mode=WorkflowMode.PERSISTENT_EXECUTE,
        order_index=0,
        skill_bindings=[],
    )
    db_session.add(compiled_plan_node)
    await db_session.flush()

    task = await create_task(
        db_session,
        TaskCreate(title="Initial kernel test", description="Round-trip task", input_payload={}),
    )
    run = await create_run(
        db_session,
        RunCreate(
            task_id=task.id,
            workflow_version_id=workflow_version.id,
            compiled_plan_id=compiled_plan.id,
        ),
    )
    attempt = await create_attempt(db_session, AttemptCreate(run_id=run.id, number=1))
    flow = await create_flow(
        db_session,
        FlowCreate(attempt_id=attempt.id, compiled_plan_id=compiled_plan.id),
    )
    flow_node = await create_flow_node(
        db_session,
        FlowNodeCreate(
            flow_id=flow.id,
            compiled_plan_node_id=compiled_plan_node.id,
            node_key="loop",
            status_payload={"phase": "execute"},
        ),
    )
    checkpoint = await record_checkpoint(
        db_session,
        CheckpointWrite(
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            sequence_no=1,
            status=CheckpointStatus.GREEN,
            summary="Task completed successfully",
            payload={"evidence": ["unit-test"]},
            recommended_next_action="continue",
        ),
    )
    approval = await create_approval(
        db_session,
        ApprovalCreate(
            run_id=run.id,
            attempt_id=attempt.id,
            flow_node_id=flow_node.id,
            reason="Need confirmation before sync",
            request_payload={"action": "sync"},
        ),
    )

    await db_session.commit()

    persisted_task = await db_session.scalar(select(Task).where(Task.id == task.id))

    assert persisted_task is not None
    assert persisted_task.title == "Initial kernel test"
    assert checkpoint.summary == "Task completed successfully"
    assert approval.status is ApprovalStatus.PENDING
