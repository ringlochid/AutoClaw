from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Literal, TypedDict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContextManifestStatus, NodeAttemptStatus, NodeSessionStatus
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import ContextManifest, Flow, FlowNode, NodeAttempt, NodeSession
from app.integrations.openclaw import (
    OpenClawClient,
    OpenClawRequest,
    OpenClawResponse,
    create_openclaw_client,
)
from app.runtime.control import latest_attempt, latest_checkpoint
from app.runtime.dispatcher import ensure_node_session
from app.runtime.runner import get_flow_with_relations
from app.runtime.scheduler import ordered_nodes
from app.runtime.state import utcnow_naive

logger = logging.getLogger(__name__)
_BACKGROUND_DISPATCH_TASKS: set[asyncio.Task[None]] = set()


def _manifest_payload_text(payload: object) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(payload)


@dataclass(slots=True)
class OpenClawDispatchCandidate:
    flow_node: FlowNode
    node_attempt: NodeAttempt
    phase: Literal["bootstrap", "execution"]
    node_session: NodeSession | None
    manifest: ContextManifest | None = None


@dataclass(slots=True)
class PreparedOpenClawDispatch:
    flow: Flow
    candidate: OpenClawDispatchCandidate
    request: OpenClawRequest


@dataclass(slots=True)
class OpenClawDispatchResult:
    flow: Flow
    candidate: OpenClawDispatchCandidate
    response: OpenClawResponse


class OpenClawDispatchPayload(TypedDict):
    delivery_status: Literal["accepted", "completed"]
    phase: Literal["bootstrap", "execution"]
    flow_node_id: UUID
    node_attempt_id: UUID
    node_session_key: str
    openclaw_response_id: str | None
    openclaw_output: str | None
    manifest_id: UUID | None
    manifest_hash: str | None
    ack_checkpoint_id: UUID | None
    next_checkpoint_sequence: int


def _latest_projected_manifest(
    flow: Flow,
    node_attempt: NodeAttempt,
) -> ContextManifest | None:
    manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.node_attempt_id == node_attempt.id
        and manifest.status == ContextManifestStatus.PROJECTED
    ]
    if not manifests:
        return None
    return sorted(manifests, key=lambda manifest: manifest.manifest_no)[-1]


def _latest_acked_manifest(
    flow: Flow,
    node_attempt: NodeAttempt,
) -> ContextManifest | None:
    manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.node_attempt_id == node_attempt.id
        and manifest.status == ContextManifestStatus.ACKED
    ]
    if not manifests:
        return None
    return sorted(manifests, key=lambda manifest: manifest.manifest_no)[-1]


def _manifest_ref(manifest: ContextManifest | None) -> tuple[UUID | None, str | None]:
    if manifest is None:
        return None, None
    return manifest.id, manifest.manifest_hash


def _next_checkpoint_sequence(node_attempt: NodeAttempt) -> int:
    checkpoint = latest_checkpoint(node_attempt)
    if checkpoint is None:
        return 1
    return checkpoint.sequence_no + 1


def _build_dispatch_input(
    flow: Flow,
    candidate: OpenClawDispatchCandidate,
    *,
    instruction_override: str | None,
) -> str:
    if candidate.phase == "bootstrap":
        manifest = candidate.manifest
        manifest_payload = manifest.manifest_payload if manifest is not None else {}
        lines = [
            "AutoClaw bootstrap execution started.",
            "You are an AutoClaw node worker. Your job is to execute the current workflow node.",
            f"Flow ID: {flow.id}",
            f"Flow node ID: {candidate.flow_node.id}",
            f"Node attempt ID: {candidate.node_attempt.id}",
            f"Node session key: {candidate.node_session.provider_session_key if candidate.node_session else 'n/a'}",
            f"Manifest ID: {manifest.id if manifest else 'n/a'}",
            f"Manifest hash: {manifest.manifest_hash if manifest else 'n/a'}",
            "Context manifest payload:",
            _manifest_payload_text(manifest_payload),
            "If any required item includes `inline_content`, use that content directly.",
            "Treat `storage_uri` as provenance/reference, not as the only access path.",
            "Use callback tools to ack the manifest, then continue with execution controls.",
            "First action for bootstrap should be `ack_context_manifest`.",
            (
                "When calling callbacks from this delegated run, include the exact "
                "node_session_key, manifest_id, and manifest_hash from this envelope."
            ),
        ]
        if instruction_override:
            lines.append(f"Operator guidance: {instruction_override}")
        return "\n".join(lines)

    lines = [
        "Continue AutoClaw node execution.",
        "If any control action is required, use callback tools",
        "(record_checkpoint, request_approval, request_replan).",
        f"Flow ID: {flow.id}",
        f"Flow node ID: {candidate.flow_node.id}",
        f"Node attempt ID: {candidate.node_attempt.id}",
        f"Node session key: {candidate.node_session.provider_session_key if candidate.node_session else 'n/a'}",
        f"Next suggested checkpoint sequence: {_next_checkpoint_sequence(candidate.node_attempt)}",
    ]
    acked_manifest = _latest_acked_manifest(flow, candidate.node_attempt)
    if acked_manifest is not None:
        lines.extend(
            [
                f"Acknowledged manifest ID: {acked_manifest.id}",
                f"Acknowledged manifest hash: {acked_manifest.manifest_hash}",
                f"Acknowledged checkpoint lineage ID: {acked_manifest.ack_checkpoint_id}",
                "Latest acknowledged context manifest payload:",
                _manifest_payload_text(acked_manifest.manifest_payload),
                "If any required item includes `inline_content`, use that content directly.",
                (
                    "Do not block only because a `storage_uri` is not dereferenceable "
                    "from this runtime."
                ),
                (
                    "When calling callbacks from this delegated run, keep using the exact "
                    "node_session_key, manifest_id, manifest_hash, and ack_checkpoint_id "
                    "from the latest acknowledged manifest."
                ),
            ]
        )
    if instruction_override:
        lines.append(f"Operator guidance: {instruction_override}")
    return "\n".join(lines)


def _candidate_for_attempt(
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> OpenClawDispatchCandidate:
    projected_manifest = _latest_projected_manifest(flow, node_attempt)
    if node_attempt.status == NodeAttemptStatus.BLOCKED and projected_manifest is not None:
        return OpenClawDispatchCandidate(
            flow_node=flow_node,
            node_attempt=node_attempt,
            phase="bootstrap",
            node_session=flow_node.node_session,
            manifest=projected_manifest,
        )

    if node_attempt.status == NodeAttemptStatus.RUNNING and projected_manifest is None:
        return OpenClawDispatchCandidate(
            flow_node=flow_node,
            node_attempt=node_attempt,
            phase="execution",
            node_session=flow_node.node_session,
        )

    raise ConflictError("Selected node attempt is not OpenClaw-ready")


def _select_dispatch_candidate(
    flow: Flow,
    *,
    target_flow_node_id: UUID | None = None,
    target_node_attempt_id: UUID | None = None,
) -> OpenClawDispatchCandidate:
    if target_flow_node_id is not None or target_node_attempt_id is not None:
        for flow_node in ordered_nodes(flow):
            if target_flow_node_id is not None and flow_node.id != target_flow_node_id:
                continue

            node_attempt = latest_attempt(flow_node)
            if node_attempt is None:
                continue
            if target_node_attempt_id is not None and node_attempt.id != target_node_attempt_id:
                continue
            return _candidate_for_attempt(flow, flow_node, node_attempt)

        raise ConflictError("Targeted node attempt is missing or no longer OpenClaw-ready")

    for flow_node in ordered_nodes(flow):
        node_attempt = latest_attempt(flow_node)
        if node_attempt is None:
            continue
        try:
            return _candidate_for_attempt(flow, flow_node, node_attempt)
        except ConflictError:
            continue

    raise ConflictError("Flow has no OpenClaw-ready attempt")


async def prepare_flow_dispatch_to_openclaw(
    session: AsyncSession,
    *,
    flow_id: UUID,
    instruction_override: str | None = None,
    target_flow_node_id: UUID | None = None,
    target_node_attempt_id: UUID | None = None,
) -> PreparedOpenClawDispatch:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")

    candidate = _select_dispatch_candidate(
        flow,
        target_flow_node_id=target_flow_node_id,
        target_node_attempt_id=target_node_attempt_id,
    )
    node_session = await ensure_node_session(
        session,
        flow=flow,
        flow_node=candidate.flow_node,
        node_attempt=candidate.node_attempt,
    )

    node_session.status = NodeSessionStatus.ACTIVE
    node_session.last_seen_at = utcnow_naive()
    candidate.node_session = node_session

    request = OpenClawRequest(
        session_key=node_session.provider_session_key,
        input=_build_dispatch_input(
            flow,
            candidate,
            instruction_override=instruction_override,
        ),
        user=str(flow.task_id),
        max_output_tokens=2048,
    )

    await session.flush()
    await session.commit()
    return PreparedOpenClawDispatch(flow=flow, candidate=candidate, request=request)


async def _run_detached_openclaw_dispatch(
    prepared: PreparedOpenClawDispatch,
    *,
    client: OpenClawClient,
) -> None:
    try:
        await client.create_response(prepared.request)
    except Exception:
        logger.exception(
            "Detached OpenClaw dispatch failed for flow %s node %s attempt %s phase %s",
            prepared.flow.id,
            prepared.candidate.flow_node.id,
            prepared.candidate.node_attempt.id,
            prepared.candidate.phase,
        )


def spawn_detached_openclaw_dispatch(
    prepared: PreparedOpenClawDispatch,
    *,
    client: OpenClawClient | None = None,
) -> None:
    transport_client = client if client is not None else create_openclaw_client()
    task = asyncio.create_task(
        _run_detached_openclaw_dispatch(prepared, client=transport_client)
    )
    _BACKGROUND_DISPATCH_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_DISPATCH_TASKS.discard)


async def dispatch_flow_to_openclaw(
    session: AsyncSession,
    *,
    flow_id: UUID,
    client: OpenClawClient | None = None,
    instruction_override: str | None = None,
    target_flow_node_id: UUID | None = None,
    target_node_attempt_id: UUID | None = None,
) -> OpenClawDispatchResult:
    prepared = await prepare_flow_dispatch_to_openclaw(
        session,
        flow_id=flow_id,
        instruction_override=instruction_override,
        target_flow_node_id=target_flow_node_id,
        target_node_attempt_id=target_node_attempt_id,
    )

    transport_client = client if client is not None else create_openclaw_client()
    response = await transport_client.create_response(prepared.request)

    refreshed_flow = await get_flow_with_relations(session, prepared.flow.id)
    return OpenClawDispatchResult(
        flow=refreshed_flow or prepared.flow,
        candidate=prepared.candidate,
        response=response,
    )


def dispatch_candidate_payload(
    candidate: OpenClawDispatchCandidate,
    *,
    response: OpenClawResponse | None = None,
) -> OpenClawDispatchPayload:
    manifest_id, manifest_hash = _manifest_ref(candidate.manifest)
    node_session = candidate.node_session
    if node_session is None:
        raise RuntimeError("Dispatch payload missing node session")

    return {
        "delivery_status": "completed" if response is not None else "accepted",
        "phase": candidate.phase,
        "flow_node_id": candidate.flow_node.id,
        "node_attempt_id": candidate.node_attempt.id,
        "node_session_key": node_session.provider_session_key,
        "openclaw_response_id": response.response_id if response is not None else None,
        "openclaw_output": response.output_text if response is not None else None,
        "manifest_id": manifest_id,
        "manifest_hash": manifest_hash,
        "ack_checkpoint_id": (
            candidate.manifest.ack_checkpoint_id if candidate.manifest is not None else None
        ),
        "next_checkpoint_sequence": _next_checkpoint_sequence(candidate.node_attempt),
    }


def dispatch_result_payload(result: OpenClawDispatchResult) -> OpenClawDispatchPayload:
    return dispatch_candidate_payload(result.candidate, response=result.response)
