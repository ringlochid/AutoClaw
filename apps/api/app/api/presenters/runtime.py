from __future__ import annotations

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
    ApprovalRead,
    CheckpointRead,
    CompiledPlanEdgeRead,
    CompiledPlanNodeRead,
    CompiledPlanRead,
    RunInspectAttemptRead,
    RunInspectFlowNodeRead,
    RunInspectFlowRead,
    RunInspectResponse,
    RunRead,
    RunStartResponse,
    TaskRead,
)


def to_task_read(task: Task) -> TaskRead:
    return TaskRead.model_validate(task)


def to_run_read(run: Run) -> RunRead:
    return RunRead.model_validate(run)


def to_checkpoint_read(checkpoint: NodeCheckpoint) -> CheckpointRead:
    return CheckpointRead.model_validate(checkpoint)


def to_approval_read(approval: Approval) -> ApprovalRead:
    return ApprovalRead.model_validate(approval)


def to_run_start_response(
    *,
    task: Task,
    run: Run,
    attempt: Attempt,
    flow: Flow,
    flow_nodes: list[FlowNode],
) -> RunStartResponse:
    first_flow_node = flow_nodes[0]
    return RunStartResponse(
        run_id=run.id,
        task_id=task.id,
        attempt_id=attempt.id,
        flow_id=flow.id,
        compiled_plan_id=run.compiled_plan_id,
        attempt_number=attempt.number,
        flow_node_count=len(flow_nodes),
        first_flow_node_id=first_flow_node.id,
    )


def to_run_inspect_response(run: Run) -> RunInspectResponse:
    attempts = [
        RunInspectAttemptRead(
            id=attempt.id,
            number=attempt.number,
            status=attempt.status,
        )
        for attempt in run.attempts
    ]

    flows: list[RunInspectFlowRead] = []
    node_count = 0
    for attempt in run.attempts:
        for flow in attempt.flows:
            nodes = [
                RunInspectFlowNodeRead(
                    id=flow_node.id,
                    node_key=flow_node.node_key,
                    state=flow_node.state,
                    iteration_index=flow_node.iteration_index,
                )
                for flow_node in flow.nodes
            ]
            node_count += len(nodes)
            flows.append(
                RunInspectFlowRead(
                    id=flow.id,
                    status=flow.status,
                    nodes=nodes,
                )
            )

    return RunInspectResponse(
        id=run.id,
        status=run.status,
        workflow_version_id=run.workflow_version_id,
        compiled_plan_id=run.compiled_plan_id,
        current_attempt_number=run.current_attempt_number,
        attempts=attempts,
        flows=flows,
        node_count=node_count,
    )


def to_compiled_plan_read(compiled_plan: CompiledPlan) -> CompiledPlanRead:
    nodes = [CompiledPlanNodeRead.model_validate(node) for node in compiled_plan.nodes]
    edges = [CompiledPlanEdgeRead.model_validate(edge) for edge in compiled_plan.edges]

    return CompiledPlanRead(
        id=compiled_plan.id,
        workflow_version_id=compiled_plan.workflow_version_id,
        compiler_version=compiled_plan.compiler_version,
        plan_hash=compiled_plan.plan_hash,
        source_snapshot=compiled_plan.source_snapshot,
        nodes=nodes,
        edges=edges,
    )
