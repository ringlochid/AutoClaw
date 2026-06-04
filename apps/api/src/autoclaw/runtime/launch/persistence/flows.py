from __future__ import annotations

from autoclaw.compiler import NormalizedCompiledNode, NormalizedDependencyEdge
from autoclaw.db.models import (
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    NodePlanRevisionModel,
)
from autoclaw.runtime.ids import assignment_id, flow_edge_id, flow_node_id, node_plan_revision_id
from autoclaw.runtime.launch.bootstrap.context import LaunchBootstrapPersistenceContext
from autoclaw.runtime.launch.bootstrap.criteria import build_node_criteria_json
from autoclaw.schemas.runtime.contracts import (
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
)


def build_flow_row(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    context: LaunchBootstrapPersistenceContext,
) -> FlowModel:
    return FlowModel(
        flow_id=context.flow_id,
        task_id=bootstrap_input.task_id,
        compiled_plan_id=context.compiled_plan_id,
        status="running",
        active_flow_revision_id=bootstrap_input.active_flow_revision_id,
        current_open_dispatch_id=None,
        current_node_key=bootstrap_input.current_node_key,
    )


def build_flow_revision_row(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    context: LaunchBootstrapPersistenceContext,
) -> FlowRevisionModel:
    return FlowRevisionModel(
        flow_revision_id=bootstrap_input.active_flow_revision_id,
        flow_id=context.flow_id,
        revision_index=1,
        source_compiled_plan_id=context.compiled_plan_id,
        cause="launch",
        snapshot_json=bootstrap_input.compiled_plan.model_dump(mode="json"),
    )


def build_flow_node_row(
    *,
    result: RuntimeBootstrapResult,
    flow_revision: FlowRevisionModel,
    context: LaunchBootstrapPersistenceContext,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    node: NormalizedCompiledNode,
    role_description: str,
    role_instruction: str | None,
    policy_description: str | None,
    policy_instruction: str | None,
) -> FlowNodeModel:
    return FlowNodeModel(
        flow_node_id=flow_node_id(
            bootstrap_input.active_flow_revision_id,
            node.node_key,
        ),
        flow_id=context.flow_id,
        flow_revision=flow_revision,
        node_key=node.node_key,
        parent_flow_node_id=(
            flow_node_id(bootstrap_input.active_flow_revision_id, node.parent_node_key)
            if node.parent_node_key is not None
            else None
        ),
        parent_node_key=node.parent_node_key,
        structural_kind=node.structural_kind.value,
        role_key=node.role,
        role_revision_no=node.role_revision_no,
        role_description=role_description,
        role_instruction=role_instruction,
        policy_key=node.policy,
        policy_revision_no=node.policy_revision_no,
        policy_description=policy_description,
        policy_instruction=policy_instruction,
        description=node.description,
        child_node_keys_json=list(node.child_node_keys),
        consumes_json=(node.consumes.model_dump(mode="json") if node.consumes else None),
        produces_json=(node.produces.model_dump(mode="json") if node.produces else None),
        criteria_json=build_node_criteria_json(paths=result.paths, node=node),
        child_defaults_json=node.child_defaults.model_dump(mode="json")
        if node.child_defaults
        else None,
        current_assignment_id=assignment_id(result.assignment.assignment_key)
        if node.node_key == result.assignment.node_key
        else None,
        order_index=node.order_index,
    )


def build_node_plan_revision_row(
    *,
    flow_revision: FlowRevisionModel,
    flow_node: FlowNodeModel,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    node: NormalizedCompiledNode,
    role_description: str,
    role_instruction: str | None,
    policy_description: str | None,
    policy_instruction: str | None,
) -> NodePlanRevisionModel:
    return NodePlanRevisionModel(
        node_plan_revision_id=node_plan_revision_id(
            bootstrap_input.active_flow_revision_id,
            node.node_key,
        ),
        flow_revision=flow_revision,
        flow_node=flow_node,
        role_key=node.role,
        role_revision_no=node.role_revision_no,
        role_description=role_description,
        role_instruction=role_instruction,
        policy_key=node.policy,
        policy_revision_no=node.policy_revision_no,
        policy_description=policy_description,
        policy_instruction=policy_instruction,
    )


def build_flow_edge_row(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    edge: NormalizedDependencyEdge,
) -> FlowEdgeModel:
    return FlowEdgeModel(
        flow_edge_id=flow_edge_id(
            bootstrap_input.active_flow_revision_id,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        ),
        flow_revision_id=bootstrap_input.active_flow_revision_id,
        provider_flow_node_id=flow_node_id(
            bootstrap_input.active_flow_revision_id,
            edge.provider_node_key,
        ),
        consumer_flow_node_id=flow_node_id(
            bootstrap_input.active_flow_revision_id,
            edge.consumer_node_key,
        ),
        provider_node_key=edge.provider_node_key,
        consumer_node_key=edge.consumer_node_key,
        kind=edge.kind.value,
        slot=edge.slot,
        description=edge.description,
        order_index=edge.order_index,
    )
