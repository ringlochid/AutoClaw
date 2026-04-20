from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.enums import ContextManifestStatus, NodeAttemptStatus
from app.core.errors import ConflictError
from app.db.models.runtime import ContextManifest, Flow, FlowNode, NodeAttempt, NodeSession
from app.runtime.control import ensure_current_attempt, ensure_flow_not_terminal


@dataclass(frozen=True)
class ExecutionBinding:
    flow: Flow
    flow_node: FlowNode
    node_attempt: NodeAttempt
    node_session: NodeSession
    manifest: ContextManifest


@dataclass(frozen=True)
class CallbackBindingInput:
    manifest_id: UUID
    manifest_hash: str
    node_session_key: str
    ack_checkpoint_id: UUID


def ensure_node_session_key(
    node_session: NodeSession | None,
    *,
    node_session_key: str,
) -> NodeSession:
    if node_session is None:
        raise ConflictError("Node attempt has no bound OpenClaw session")
    if node_session.provider_session_key != node_session_key:
        raise ConflictError("Node session key does not match the current delegated session")
    return node_session


def resolve_attempt_manifest(
    flow: Flow,
    node_attempt: NodeAttempt,
    *,
    manifest_id: UUID,
) -> ContextManifest:
    manifest = next(
        (
            item
            for item in flow.context_manifests
            if item.id == manifest_id and item.node_attempt_id == node_attempt.id
        ),
        None,
    )
    if manifest is None:
        raise ConflictError("Context manifest does not belong to the current node attempt")
    return manifest


def ensure_manifest_binding(
    flow: Flow,
    node_attempt: NodeAttempt,
    node_session: NodeSession,
    *,
    manifest_id: UUID,
    manifest_hash: str,
    expected_status: ContextManifestStatus,
) -> ContextManifest:
    manifest = resolve_attempt_manifest(flow, node_attempt, manifest_id=manifest_id)
    if manifest.manifest_hash != manifest_hash:
        raise ConflictError("Context manifest hash does not match the current delegated manifest")
    if manifest.node_session_id != node_session.id:
        raise ConflictError("Context manifest is not bound to the current delegated session")
    if manifest.status != expected_status:
        raise ConflictError(
            "Context manifest is not in the expected callback state: "
            f"expected {expected_status.value}, got {manifest.status.value}"
        )
    return manifest


def latest_acked_manifest(flow: Flow, node_attempt: NodeAttempt) -> ContextManifest | None:
    manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.node_attempt_id == node_attempt.id
        and manifest.status == ContextManifestStatus.ACKED
    ]
    if not manifests:
        return None
    return sorted(manifests, key=lambda manifest: manifest.manifest_no)[-1]


def ensure_latest_acked_manifest(
    flow: Flow,
    node_attempt: NodeAttempt,
    node_session: NodeSession,
    *,
    manifest_id: UUID,
    manifest_hash: str,
    ack_checkpoint_id: UUID,
) -> ContextManifest:
    manifest = ensure_manifest_binding(
        flow,
        node_attempt,
        node_session,
        manifest_id=manifest_id,
        manifest_hash=manifest_hash,
        expected_status=ContextManifestStatus.ACKED,
    )
    latest_manifest = latest_acked_manifest(flow, node_attempt)
    if latest_manifest is None or latest_manifest.id != manifest.id:
        raise ConflictError(
            "Context manifest is not the latest acknowledged manifest for this node attempt"
        )
    if manifest.ack_checkpoint_id is None:
        raise ConflictError("Acknowledged manifest is missing durable ack checkpoint lineage")
    if manifest.ack_checkpoint_id != ack_checkpoint_id:
        raise ConflictError(
            "Ack checkpoint id does not match the latest acknowledged manifest lineage"
        )
    return manifest


def validate_manifest_execution_binding(
    manifest: ContextManifest,
    *,
    node_session_key: str,
    manifest_hash: str,
    flow_id: UUID | None = None,
    flow_node_id: UUID | None = None,
    node_attempt_id: UUID | None = None,
    ack_checkpoint_id: UUID | None = None,
    allowed_manifest_statuses: set[ContextManifestStatus],
    allowed_attempt_statuses: set[NodeAttemptStatus] | None = None,
    require_current_attempt_binding: bool = False,
    require_non_terminal_flow: bool = False,
) -> ExecutionBinding:
    if flow_id is not None and manifest.flow_id != flow_id:
        raise ConflictError("Manifest does not belong to flow")
    if flow_node_id is not None and manifest.flow_node_id != flow_node_id:
        raise ConflictError("Manifest does not belong to flow node")
    if node_attempt_id is not None and manifest.node_attempt_id != node_attempt_id:
        raise ConflictError("Manifest does not belong to node attempt")
    if manifest.status not in allowed_manifest_statuses:
        raise ConflictError("Manifest is no longer active for this operation")

    node_session = ensure_node_session_key(
        manifest.node_session,
        node_session_key=node_session_key,
    )

    if require_non_terminal_flow:
        ensure_flow_not_terminal(manifest.flow)

    if require_current_attempt_binding:
        ensure_current_attempt(
            manifest.flow,
            manifest.flow_node,
            manifest.node_attempt,
            allowed_statuses=allowed_attempt_statuses,
            require_current_session=True,
            node_session=node_session,
        )

    if manifest.status == ContextManifestStatus.ACKED:
        if ack_checkpoint_id is None:
            raise ConflictError("Acknowledged manifest access requires ack checkpoint lineage")
        ensure_latest_acked_manifest(
            manifest.flow,
            manifest.node_attempt,
            node_session,
            manifest_id=manifest.id,
            manifest_hash=manifest_hash,
            ack_checkpoint_id=ack_checkpoint_id,
        )
    else:
        ensure_manifest_binding(
            manifest.flow,
            manifest.node_attempt,
            node_session,
            manifest_id=manifest.id,
            manifest_hash=manifest_hash,
            expected_status=manifest.status,
        )

    return ExecutionBinding(
        flow=manifest.flow,
        flow_node=manifest.flow_node,
        node_attempt=manifest.node_attempt,
        node_session=node_session,
        manifest=manifest,
    )


def extract_callback_binding(
    payload: Any,
    *,
    required: bool,
    operation: str,
) -> CallbackBindingInput | None:
    manifest_id = getattr(payload, "manifest_id", None)
    manifest_hash = getattr(payload, "manifest_hash", None)
    node_session_key = getattr(payload, "node_session_key", None)
    ack_checkpoint_id = getattr(payload, "ack_checkpoint_id", None)

    has_any = any(
        value is not None
        for value in [manifest_id, manifest_hash, node_session_key, ack_checkpoint_id]
    )
    if not has_any:
        if required:
            raise ConflictError(
                f"{operation} requires manifest, session, and ack lineage binding"
            )
        return None

    if (
        manifest_id is None
        or manifest_hash is None
        or node_session_key is None
        or ack_checkpoint_id is None
    ):
        raise ConflictError(f"{operation} requires manifest, session, and ack lineage binding")

    return CallbackBindingInput(
        manifest_id=manifest_id,
        manifest_hash=manifest_hash,
        node_session_key=node_session_key,
        ack_checkpoint_id=ack_checkpoint_id,
    )


def validate_attempt_execution_binding(
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
    *,
    callback_binding: CallbackBindingInput | None,
    allowed_attempt_statuses: set[NodeAttemptStatus],
    require_non_terminal_flow: bool = False,
) -> ExecutionBinding | None:
    if require_non_terminal_flow:
        ensure_flow_not_terminal(flow)

    node_session = None
    if callback_binding is not None:
        node_session = ensure_node_session_key(
            flow_node.node_session,
            node_session_key=callback_binding.node_session_key,
        )

    ensure_current_attempt(
        flow,
        flow_node,
        node_attempt,
        allowed_statuses=allowed_attempt_statuses,
        require_current_session=node_session is not None,
        node_session=node_session,
    )

    if callback_binding is None or node_session is None:
        return None

    manifest = ensure_latest_acked_manifest(
        flow,
        node_attempt,
        node_session,
        manifest_id=callback_binding.manifest_id,
        manifest_hash=callback_binding.manifest_hash,
        ack_checkpoint_id=callback_binding.ack_checkpoint_id,
    )
    return ExecutionBinding(
        flow=flow,
        flow_node=flow_node,
        node_attempt=node_attempt,
        node_session=node_session,
        manifest=manifest,
    )
