from __future__ import annotations

from uuid import UUID

from app.core.enums import ContextManifestStatus
from app.core.errors import ConflictError
from app.db.models.runtime import ContextManifest, Flow, NodeAttempt, NodeSession


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
