from typing import Any

from app.core.enums import SkillBindingState
from app.core.errors import InvalidDefinitionError
from app.schemas.compiler import ResolvedWorkflowDefinition

_ALLOWED_TASK_DEFAULT_MODES = {
    "workspace": {"use_existing", "ensure_task_primary", "clone_from"},
    "context": {"use_existing", "ensure_task_primary", "clone_from", "seed_from"},
    "manifests": {"ensure_task_root"},
}


def _validate_task_default(slot: str, binding: dict[str, Any]) -> None:
    mode = binding["mode"]
    if mode not in _ALLOWED_TASK_DEFAULT_MODES[slot]:
        raise InvalidDefinitionError(f"Task default '{slot}' does not support mode '{mode}'")

    ref = binding.get("ref")
    seed_from = binding.get("seed_from") or []
    auto_create = binding.get("auto_create")

    if mode in {"use_existing", "clone_from"} and not ref:
        raise InvalidDefinitionError(f"Task default '{slot}' with mode '{mode}' requires a ref")
    if mode in {"ensure_task_primary", "ensure_task_root", "seed_from"} and ref is not None:
        raise InvalidDefinitionError(
            f"Task default '{slot}' with mode '{mode}' cannot also declare a ref"
        )
    if slot != "context" and seed_from:
        raise InvalidDefinitionError(f"Task default '{slot}' cannot declare seed_from")
    if mode == "seed_from" and slot != "context":
        raise InvalidDefinitionError("Only context task defaults may use mode 'seed_from'")
    if mode == "seed_from" and not seed_from:
        raise InvalidDefinitionError(
            "Task default 'context' with mode 'seed_from' requires seed_from"
        )
    if seed_from and mode not in {"ensure_task_primary", "seed_from"}:
        raise InvalidDefinitionError(
            f"Task default '{slot}' cannot combine seed_from with mode '{mode}'"
        )
    if mode in {"ensure_task_primary", "ensure_task_root"} and auto_create is False:
        raise InvalidDefinitionError(
            f"Task default '{slot}' with mode '{mode}' cannot disable auto_create"
        )


def _validate_workspace_mount_ref(node_key: str, ref: str) -> None:
    if ref.startswith("task.") and not (
        ref == "task.primary_workspace" or ref.startswith("task.reference_workspace.")
    ):
        raise InvalidDefinitionError(f"Node '{node_key}' has invalid workspace mount ref '{ref}'")


def _validate_context_ref(node_key: str, ref: str) -> None:
    if ref.startswith("task.") and not (
        ref == "task.primary_context" or ref.startswith("task.reference_context.")
    ):
        raise InvalidDefinitionError(f"Node '{node_key}' has invalid context ref '{ref}'")


def _validate_passthrough_resource(
    node_key: str, resource_key: str, resource: dict[str, Any]
) -> None:
    required = bool(resource.get("required", True))
    if resource_key == "image":
        if required and not resource.get("ref") and not resource.get("kind"):
            raise InvalidDefinitionError(
                f"Node '{node_key}' has required image resource without ref or kind"
            )
    elif resource_key == "compose":
        if required and not resource.get("ref") and not resource.get("services"):
            raise InvalidDefinitionError(
                f"Node '{node_key}' has required compose resource without ref or services"
            )
    elif resource_key == "container":
        if required and not resource.get("ref") and not resource.get("backend_kind"):
            raise InvalidDefinitionError(
                f"Node '{node_key}' has required container resource without ref or backend_kind"
            )


def validate_resolved_workflow(resolved_workflow: ResolvedWorkflowDefinition) -> None:
    if not resolved_workflow.nodes:
        raise InvalidDefinitionError("Workflow must resolve to at least one node")

    node_keys = [node.node_key for node in resolved_workflow.nodes]
    node_key_set = set(node_keys)
    if len(node_keys) != len(node_key_set):
        raise InvalidDefinitionError("Workflow contains duplicate node keys")

    for slot, binding in resolved_workflow.task_defaults.items():
        _validate_task_default(slot, binding)

    for node in resolved_workflow.nodes:
        if node.mode not in node.allowed_modes:
            raise InvalidDefinitionError(
                f"Node '{node.node_key}' uses mode '{node.mode}' "
                f"which is not allowed by role '{node.role_key}'"
            )

        skill_state_by_key: dict[str, set[SkillBindingState]] = {}
        for binding in node.skill_bindings:
            skill_key = f"{binding.provider}:{binding.key}"
            skill_state_by_key.setdefault(skill_key, set()).add(binding.state)
        for skill_key, states in skill_state_by_key.items():
            if SkillBindingState.REQUIRED in states and SkillBindingState.BLOCKED in states:
                raise InvalidDefinitionError(
                    "Node "
                    f"'{node.node_key}' has conflicting required/blocked skill refs for "
                    f"'{skill_key}'"
                )

        for mount in node.resources.get("workspace", {}).get("mounts", []):
            _validate_workspace_mount_ref(node.node_key, mount["ref"])
        for context_ref in node.resources.get("context", {}).get("refs", []):
            _validate_context_ref(node.node_key, context_ref["ref"])
        for resource_key in ("image", "compose", "container"):
            resource = node.resources.get(resource_key)
            if isinstance(resource, dict):
                _validate_passthrough_resource(node.node_key, resource_key, resource)

    seen_edges: set[tuple[str, str, str, str | None]] = set()
    for edge in resolved_workflow.edges:
        if edge.from_node not in node_key_set:
            raise InvalidDefinitionError(f"Edge source '{edge.from_node}' does not exist")
        if edge.to_node not in node_key_set:
            raise InvalidDefinitionError(f"Edge target '{edge.to_node}' does not exist")

        edge_key = (
            edge.from_node,
            edge.to_node,
            edge.edge_kind.value,
            edge.condition_expr,
        )
        if edge_key in seen_edges:
            raise InvalidDefinitionError("Workflow contains duplicate edges")
        seen_edges.add(edge_key)
