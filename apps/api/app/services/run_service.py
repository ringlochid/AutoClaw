from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.services.compiler_service import compile_published_workflow
from app.core.enums import AttemptStatus, CheckpointStatus, FlowNodeState, FlowStatus, RunStatus, TaskStatus
from app.db.models.runtime import Approval, Attempt, Flow, FlowNode, NodeCheckpoint, Run, Task
from app.schemas.runtime import (
    AttemptCreate,
    CheckpointWrite,
    FlowCreate,
    FlowNodeCreate,
    RunCreate,
    RunInspectResponse,
    RunStartFromWorkflowCreate,
    TaskCreate,
)


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


async def create_approval(session: AsyncSession, payload: Any) -> Approval:
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

    compiled_nodes = sorted(compiled_plan.nodes, key=lambda node: node.order_index)
    node_by_key: dict[str, FlowNode] = {}
    flow_nodes: list[FlowNode] = []
    for compiled_node in compiled_nodes:
        parent_flow_node_id = None
        if compiled_node.parent_node_key is not None:
            parent = node_by_key.get(compiled_node.parent_node_key)
            parent_flow_node_id = parent.id if parent is not None else None

        flow_node = FlowNode(
            flow=flow,
            compiled_plan_node_id=compiled_node.id,
            parent_flow_node_id=parent_flow_node_id,
            node_key=compiled_node.node_key,
            state=FlowNodeState.READY,
            iteration_index=compiled_node.order_index,
            status_payload={"mode": compiled_node.mode.value},
        )
        session.add(flow_node)
        await session.flush()
        node_by_key[compiled_node.node_key] = flow_node
        flow_nodes.append(flow_node)

    return task, run, attempt, flow, flow_nodes


async def get_run_with_relations(session: AsyncSession, run_id) -> Run | None:
    stmt = (
        select(Run)
        .options(
            selectinload(Run.attempts)
            .selectinload(Attempt.flows)
            .selectinload(Flow.nodes),
        )
        .where(Run.id == run_id)
    )
    return await session.scalar(stmt)


async def build_run_inspect_payload(
    session: AsyncSession,
    run_id,
) -> RunInspectResponse:
    run = await get_run_with_relations(session, run_id)
    if run is None:
        raise ValueError(f"No run found: {run_id}")

    attempts_payload: list[dict[str, Any]] = [
        {
            "id": attempt.id,
            "number": attempt.number,
            "status": attempt.status,
        }
        for attempt in sorted(run.attempts, key=lambda attempt: attempt.number)
    ]

    flows_payload: list[dict[str, Any]] = []
    node_count = 0
    for attempt in run.attempts:
        for flow in attempt.flows:
            node_payload = [
                {
                    "id": flow_node.id,
                    "node_key": flow_node.node_key,
                    "state": flow_node.state,
                    "iteration_index": flow_node.iteration_index,
                }
                for flow_node in sorted(flow.nodes, key=lambda node: node.iteration_index)
            ]
            node_count += len(node_payload)
            flows_payload.append(
                {
                    "id": flow.id,
                    "status": flow.status,
                    "nodes": node_payload,
                }
            )

    return RunInspectResponse(
        id=run.id,
        status=run.status,
        workflow_version_id=run.workflow_version_id,
        compiled_plan_id=run.compiled_plan_id,
        current_attempt_number=run.current_attempt_number,
        attempts=attempts_payload,
        flows=flows_payload,
        node_count=node_count,
    )


__all__ = [
    "create_task",
    "create_run",
    "create_attempt",
    "create_flow",
    "create_flow_node",
    "record_checkpoint",
    "start_run_from_workflow",
    "build_run_inspect_payload",
]
