from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import AttemptStatus, FlowNodeState, FlowStatus, RunStatus, TaskStatus
from app.db.models.runtime import (
    Approval,
    Attempt,
    CompiledPlan,
    Flow,
    FlowNode,
    NodeCheckpoint,
    Run,
    Task,
)
from app.schemas.runtime import (
    ApprovalCreate,
    ApprovalResolve,
    AttemptCreate,
    CheckpointWrite,
    FlowCreate,
    FlowNodeCreate,
    RunCreate,
    RunStartFromWorkflowCreate,
    TaskCreate,
)
from app.services.compiler_service import compile_published_workflow


async def create_task(session: AsyncSession, payload: TaskCreate) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        input_payload=payload.input_payload,
        status=TaskStatus.PENDING,
    )
    session.add(task)
    await session.flush()
    return task


async def create_run(session: AsyncSession, payload: RunCreate) -> Run:
    run = Run(
        task_id=payload.task_id,
        workflow_version_id=payload.workflow_version_id,
        compiled_plan_id=payload.compiled_plan_id,
        status=RunStatus.PENDING,
        current_attempt_number=0,
    )
    session.add(run)
    await session.flush()
    return run


async def create_attempt(session: AsyncSession, payload: AttemptCreate) -> Attempt:
    attempt = Attempt(
        run_id=payload.run_id,
        number=payload.number,
        retry_of_attempt_id=payload.retry_of_attempt_id,
        status=AttemptStatus.PENDING,
    )
    session.add(attempt)
    await session.flush()
    return attempt


async def create_flow(session: AsyncSession, payload: FlowCreate) -> Flow:
    flow = Flow(
        attempt_id=payload.attempt_id,
        compiled_plan_id=payload.compiled_plan_id,
        status=FlowStatus.PENDING,
    )
    session.add(flow)
    await session.flush()
    return flow


async def create_flow_node(session: AsyncSession, payload: FlowNodeCreate) -> FlowNode:
    flow_node = FlowNode(
        flow_id=payload.flow_id,
        compiled_plan_node_id=payload.compiled_plan_node_id,
        parent_flow_node_id=payload.parent_flow_node_id,
        node_key=payload.node_key,
        state=FlowNodeState.READY,
        iteration_index=payload.iteration_index,
        status_payload=payload.status_payload,
    )
    session.add(flow_node)
    await session.flush()
    return flow_node


async def create_flow_nodes_for_compiled_plan(
    session: AsyncSession,
    *,
    flow: Flow,
    compiled_plan: CompiledPlan,
) -> list[FlowNode]:
    node_by_key: dict[str, FlowNode] = {}
    flow_nodes: list[FlowNode] = []

    for compiled_node in compiled_plan.nodes:
        parent_flow_node_id = None
        if compiled_node.parent_node_key is not None:
            parent = node_by_key.get(compiled_node.parent_node_key)
            parent_flow_node_id = parent.id if parent is not None else None

        flow_node = await create_flow_node(
            session,
            FlowNodeCreate(
                flow_id=flow.id,
                compiled_plan_node_id=compiled_node.id,
                parent_flow_node_id=parent_flow_node_id,
                node_key=compiled_node.node_key,
                iteration_index=compiled_node.order_index,
                status_payload={"mode": compiled_node.mode.value},
            ),
        )
        node_by_key[compiled_node.node_key] = flow_node
        flow_nodes.append(flow_node)

    return flow_nodes


async def record_checkpoint(session: AsyncSession, payload: CheckpointWrite) -> NodeCheckpoint:
    checkpoint = NodeCheckpoint(
        flow_id=payload.flow_id,
        flow_node_id=payload.flow_node_id,
        sequence_no=payload.sequence_no,
        status=payload.status,
        summary=payload.summary,
        payload=payload.payload,
        failure_signature=payload.failure_signature,
        recommended_next_action=payload.recommended_next_action,
    )
    session.add(checkpoint)
    await session.flush()
    return checkpoint


async def create_approval(session: AsyncSession, payload: ApprovalCreate) -> Approval:
    approval = Approval(
        run_id=payload.run_id,
        attempt_id=payload.attempt_id,
        flow_node_id=payload.flow_node_id,
        reason=payload.reason,
        request_payload=payload.request_payload,
    )
    session.add(approval)
    await session.flush()
    return approval


async def get_approval(session: AsyncSession, approval_id: UUID) -> Approval | None:
    return cast(
        Approval | None,
        await session.scalar(select(Approval).where(Approval.id == approval_id)),
    )


async def resolve_approval(
    session: AsyncSession,
    approval_id: UUID,
    payload: ApprovalResolve,
) -> Approval:
    approval = await get_approval(session, approval_id)
    if approval is None:
        raise ValueError(f"No approval found: {approval_id}")

    approval.status = payload.status
    approval.resolution_payload = payload.resolution_payload
    await session.flush()
    return approval


async def start_run_from_workflow(
    session: AsyncSession,
    *,
    workflow_key: str,
    payload: RunStartFromWorkflowCreate,
) -> tuple[Task, Run, Attempt, Flow, list[FlowNode]]:
    compiled_plan = await compile_published_workflow(session, workflow_key)

    task = await create_task(session, payload.task)
    run = await create_run(
        session,
        RunCreate(
            task_id=task.id,
            workflow_version_id=compiled_plan.workflow_version_id,
            compiled_plan_id=compiled_plan.id,
        ),
    )

    attempt_number = payload.attempt_number or 1
    attempt = await create_attempt(
        session,
        AttemptCreate(run_id=run.id, number=attempt_number, retry_of_attempt_id=None),
    )
    run.current_attempt_number = attempt_number
    run.status = RunStatus.RUNNING
    attempt.status = AttemptStatus.RUNNING

    flow = await create_flow(
        session,
        FlowCreate(
            attempt_id=attempt.id,
            compiled_plan_id=compiled_plan.id,
        ),
    )
    flow.status = FlowStatus.RUNNING

    flow_nodes = await create_flow_nodes_for_compiled_plan(
        session,
        flow=flow,
        compiled_plan=compiled_plan,
    )
    return task, run, attempt, flow, flow_nodes


async def get_run_with_relations(session: AsyncSession, run_id: UUID) -> Run | None:
    stmt = (
        select(Run)
        .options(
            selectinload(Run.attempts).selectinload(Attempt.flows).selectinload(Flow.nodes),
            selectinload(Run.approvals),
        )
        .where(Run.id == run_id)
    )
    return cast(Run | None, await session.scalar(stmt))


async def list_run_checkpoints(session: AsyncSession, run_id: UUID) -> list[NodeCheckpoint]:
    result = await session.scalars(
        select(NodeCheckpoint)
        .join(Flow, NodeCheckpoint.flow_id == Flow.id)
        .join(Attempt, Flow.attempt_id == Attempt.id)
        .where(Attempt.run_id == run_id)
        .order_by(NodeCheckpoint.sequence_no.asc(), NodeCheckpoint.created_at.asc())
    )
    return list(result.all())


__all__ = [
    "create_approval",
    "create_attempt",
    "create_flow",
    "create_flow_node",
    "create_flow_nodes_for_compiled_plan",
    "create_run",
    "create_task",
    "get_approval",
    "get_run_with_relations",
    "list_run_checkpoints",
    "record_checkpoint",
    "resolve_approval",
    "start_run_from_workflow",
]
