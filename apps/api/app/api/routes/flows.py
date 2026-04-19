import hashlib
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.api.presenters.runtime import (
    to_checkpoint_read,
    to_context_item_audit_read,
    to_context_manifest_read,
    to_flow_audit_read,
    to_flow_inspect_response,
    to_flow_operator_read,
    to_flow_runtime_slice_read,
    to_flow_start_response,
    to_flow_summary_read,
    to_flow_timeline_slice_read,
    to_flow_worker_bundle_read,
    to_node_plan_revision_read,
    to_task_compose_read,
)
from app.core.enums import (
    CheckpointStatus,
    ContextItemStatus,
    ContextManifestStatus,
    NodeAttemptStatus,
)
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.core.ids import parse_uuid_like
from app.db.models.runtime import (
    CompiledPlan,
    ContextItem,
    FlowRevision,
    TaskCompose,
)
from app.integrations.openclaw import (
    OpenClawConfigurationError,
    OpenClawIntegrationError,
    OpenClawRequestError,
    OpenClawTimeoutError,
)
from app.runtime.callback_bindings import (
    ensure_latest_acked_manifest,
    ensure_manifest_binding,
    ensure_node_session_key,
)
from app.runtime.checkpoints import list_flow_checkpoints, record_checkpoint
from app.runtime.control import ensure_current_attempt, ensure_flow_not_terminal, lock_flow
from app.runtime.dispatcher import acknowledge_context_manifest, get_context_manifest
from app.runtime.read_models import get_flow_audit_snapshot, list_flows
from app.runtime.replan import list_flow_replans, request_replan
from app.runtime.runner import (
    advance_flow_until_boundary,
    cancel_flow,
    continue_flow,
    get_flow_with_relations,
    pause_flow,
    retry_flow_node,
    start_flow_from_workflow,
)
from app.runtime.state import utcnow_naive
from app.runtime.watchdog import recover_flow_watchdog, run_flow_watchdog
from app.schemas.runtime import (
    CheckpointRead,
    ContextItemAuditRead,
    ContextManifestAckWrite,
    ContextManifestRead,
    FlowAuditRead,
    FlowInspectResponse,
    FlowNodeRetryResponse,
    FlowOperatorRead,
    FlowPauseResponse,
    FlowRuntimeSliceRead,
    FlowStartResponse,
    FlowSummaryRead,
    FlowTimelineSliceRead,
    FlowWatchdogRecoveryResponse,
    FlowWatchdogResponse,
    FlowWorkerBundleRead,
    InternalCheckpointWrite,
    InternalContextItemPublish,
    InternalNodePlanRevisionCreate,
    NodePlanRevisionCreate,
    NodePlanRevisionRead,
    OpenClawDispatchResponse,
)
from app.services.openclaw_bridge import (
    dispatch_candidate_payload,
    dispatch_flow_to_openclaw,
    dispatch_result_payload,
    prepare_flow_dispatch_to_openclaw,
    spawn_detached_openclaw_dispatch,
)

router = APIRouter(prefix="/flows", tags=["flows"])
internal_router = APIRouter(prefix="/flows", tags=["internal"])

WORKER_BUNDLE_MANIFEST_ID_QUERY = Query(...)
WORKER_BUNDLE_MANIFEST_HASH_QUERY = Query(...)
WORKER_BUNDLE_NODE_SESSION_KEY_QUERY = Query(...)
WORKER_BUNDLE_ACK_CHECKPOINT_ID_QUERY = Query(None)


@router.get("", response_model=list[FlowSummaryRead])
async def list_flows_route(session: DbSession) -> list[FlowSummaryRead]:
    flows = await list_flows(session)
    return [to_flow_summary_read(flow) for flow in flows]


@router.post("/{flow_id}/continue", response_model=FlowInspectResponse)
async def continue_flow_route(flow_id: UUID, session: DbSession) -> FlowInspectResponse:
    try:
        flow = await continue_flow(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return to_flow_inspect_response(flow)


@router.post("/{flow_id}/pause", response_model=FlowPauseResponse)
async def pause_flow_route(flow_id: UUID, session: DbSession) -> FlowPauseResponse:
    try:
        flow, paused_nodes = await pause_flow(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return FlowPauseResponse(
        flow=to_flow_inspect_response(flow),
        paused_node_ids=[node.id for node in paused_nodes],
    )


@router.post("/{flow_id}/cancel", response_model=FlowInspectResponse)
async def cancel_flow_route(flow_id: UUID, session: DbSession) -> FlowInspectResponse:
    try:
        flow = await cancel_flow(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return to_flow_inspect_response(flow)


@router.post("/{flow_id}/nodes/{flow_node_id}/retry", response_model=FlowNodeRetryResponse)
async def retry_flow_node_route(
    flow_id: UUID,
    flow_node_id: UUID,
    session: DbSession,
) -> FlowNodeRetryResponse:
    try:
        _flow, node_attempt = await retry_flow_node(
            session,
            flow_id=flow_id,
            flow_node_id=flow_node_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    refreshed_flow = await get_flow_with_relations(session, flow_id)
    if refreshed_flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found: {flow_id}",
        )
    return FlowNodeRetryResponse(
        flow=to_flow_inspect_response(refreshed_flow),
        retried_node_attempt_id=node_attempt.id,
    )


@router.get("/{flow_id}", response_model=FlowInspectResponse)
async def get_flow(flow_id: UUID, session: DbSession) -> FlowInspectResponse:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No flow found: {flow_id}"
        )
    return to_flow_inspect_response(flow)


@router.get("/{flow_id}/operator", response_model=FlowOperatorRead)
async def get_flow_operator_route(flow_id: UUID, session: DbSession) -> FlowOperatorRead:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found: {flow_id}",
        )
    return to_flow_operator_read(flow)


@internal_router.get(
    "/{flow_id}/audit",
    response_model=FlowAuditRead,
    include_in_schema=False,
)
async def get_flow_audit_route(flow_id: UUID, session: DbSession) -> FlowAuditRead:
    snapshot = await get_flow_audit_snapshot(session, flow_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found: {flow_id}",
        )
    return to_flow_audit_read(snapshot)


@internal_router.get(
    "/{flow_id}/runtime-slice",
    response_model=FlowRuntimeSliceRead,
    include_in_schema=False,
)
async def get_flow_runtime_slice_route(
    flow_id: UUID,
    session: DbSession,
    checkpoint_limit: int = Query(10, ge=1, le=25),
    approval_limit: int = Query(10, ge=1, le=25),
    manifest_limit: int = Query(5, ge=1, le=10),
    context_limit: int = Query(10, ge=1, le=25),
    event_limit: int = Query(20, ge=1, le=50),
) -> FlowRuntimeSliceRead:
    snapshot = await get_flow_audit_snapshot(session, flow_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found: {flow_id}",
        )
    return to_flow_runtime_slice_read(
        snapshot,
        checkpoint_limit=checkpoint_limit,
        approval_limit=approval_limit,
        manifest_limit=manifest_limit,
        context_limit=context_limit,
        event_limit=event_limit,
    )


@internal_router.get(
    "/{flow_id}/timeline-slice",
    response_model=FlowTimelineSliceRead,
    include_in_schema=False,
)
async def get_flow_timeline_slice_route(
    flow_id: UUID,
    session: DbSession,
    context_limit: int = Query(10, ge=1, le=25),
    event_limit: int = Query(20, ge=1, le=50),
) -> FlowTimelineSliceRead:
    snapshot = await get_flow_audit_snapshot(session, flow_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found: {flow_id}",
        )
    return to_flow_timeline_slice_read(
        snapshot,
        context_limit=context_limit,
        event_limit=event_limit,
    )


@internal_router.get(
    "/{flow_id}/worker-bundle",
    response_model=FlowWorkerBundleRead,
    include_in_schema=False,
)
async def get_flow_worker_bundle_route(
    flow_id: UUID,
    session: DbSession,
    manifest_id: UUID = WORKER_BUNDLE_MANIFEST_ID_QUERY,
    manifest_hash: str = WORKER_BUNDLE_MANIFEST_HASH_QUERY,
    node_session_key: str = WORKER_BUNDLE_NODE_SESSION_KEY_QUERY,
    ack_checkpoint_id: UUID | None = WORKER_BUNDLE_ACK_CHECKPOINT_ID_QUERY,
) -> FlowWorkerBundleRead:
    manifest = await get_context_manifest(session, manifest_id)
    if manifest is None or manifest.flow_id != flow_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No context manifest found: {manifest_id}",
        )

    if manifest.status not in {ContextManifestStatus.PROJECTED, ContextManifestStatus.ACKED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Manifest is no longer active for worker bundle access",
        )

    node_session = ensure_node_session_key(
        manifest.node_session,
        node_session_key=node_session_key,
    )
    if manifest.status == ContextManifestStatus.ACKED:
        if ack_checkpoint_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Acknowledged worker bundle access requires ack checkpoint lineage",
            )
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

    snapshot = await get_flow_audit_snapshot(session, flow_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found: {flow_id}",
        )
    task_compose = await session.scalar(
        select(TaskCompose).where(TaskCompose.task_id == snapshot.flow.task_id)
    )
    compiled_plan = None
    if manifest.node_attempt.flow_revision_id is not None:
        compiled_plan = await session.scalar(
            select(CompiledPlan)
            .join(FlowRevision, FlowRevision.compiled_plan_id == CompiledPlan.id)
            .options(
                selectinload(CompiledPlan.nodes),
                selectinload(CompiledPlan.edges),
            )
            .where(FlowRevision.id == manifest.node_attempt.flow_revision_id)
        )
    return to_flow_worker_bundle_read(
        snapshot,
        current_manifest=manifest,
        task_compose=task_compose,
        compiled_plan=compiled_plan,
    )


@internal_router.get(
    "/{flow_id}/replans",
    response_model=list[NodePlanRevisionRead],
    include_in_schema=False,
)
async def list_flow_replans_route(
    flow_id: UUID,
    session: DbSession,
) -> list[NodePlanRevisionRead]:
    try:
        replans = await list_flow_replans(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [to_node_plan_revision_read(replan) for replan in replans]


@internal_router.post(
    "/{flow_id}/replans/internal",
    response_model=NodePlanRevisionRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def request_replan_internal_route(
    flow_id: UUID,
    payload: InternalNodePlanRevisionCreate,
    session: DbSession,
) -> NodePlanRevisionRead:
    try:
        replan = await request_replan(session, flow_id=flow_id, payload=payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ConflictError, InvalidDefinitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT
            if isinstance(exc, ConflictError)
            else status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    await advance_flow_until_boundary(
        session,
        flow_id,
        cause="replan-adopted",
    )
    await session.commit()
    return to_node_plan_revision_read(replan)


@internal_router.post(
    "/{flow_id}/dispatch-openclaw",
    response_model=OpenClawDispatchResponse,
    include_in_schema=False,
)
async def dispatch_openclaw_route(
    flow_id: UUID,
    session: DbSession,
    response: Response,
    wait_for_response: bool = Query(
        default=False,
        description=(
            "When true, wait for the delegated OpenClaw response before returning. "
            "Default false returns 202 Accepted after local handoff so callers do not hit "
            "their own read timeouts while the worker runs."
        ),
    ),
) -> OpenClawDispatchResponse:
    if wait_for_response:
        try:
            dispatch_result = await dispatch_flow_to_openclaw(session, flow_id=flow_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except OpenClawConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc
        except (OpenClawTimeoutError, OpenClawRequestError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        except OpenClawIntegrationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        await session.commit()
        payload = dispatch_result_payload(dispatch_result)
        return OpenClawDispatchResponse(
            flow=to_flow_inspect_response(dispatch_result.flow),
            **payload,
        )

    try:
        prepared_dispatch = await prepare_flow_dispatch_to_openclaw(session, flow_id=flow_id)
        spawn_detached_openclaw_dispatch(prepared_dispatch)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OpenClawConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    response.status_code = status.HTTP_202_ACCEPTED
    payload = dispatch_candidate_payload(prepared_dispatch.candidate)
    return OpenClawDispatchResponse(
        flow=to_flow_inspect_response(prepared_dispatch.flow),
        **payload,
    )


@router.post(
    "/{flow_id}/replans",
    response_model=NodePlanRevisionRead,
    status_code=status.HTTP_201_CREATED,
)
async def request_replan_route(
    flow_id: UUID,
    payload: NodePlanRevisionCreate,
    session: DbSession,
) -> NodePlanRevisionRead:
    try:
        replan = await request_replan(session, flow_id=flow_id, payload=payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ConflictError, InvalidDefinitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT
            if isinstance(exc, ConflictError)
            else status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    await advance_flow_until_boundary(
        session,
        flow_id,
        cause="replan-adopted",
    )
    await session.commit()
    return to_node_plan_revision_read(replan)


@internal_router.post(
    "/{flow_id}/watchdog",
    response_model=FlowWatchdogResponse,
    include_in_schema=False,
)
async def run_watchdog_route(flow_id: UUID, session: DbSession) -> FlowWatchdogResponse:
    try:
        flow, stalled_attempt_ids, checkpoints = await run_flow_watchdog(
            session,
            flow_id=flow_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return FlowWatchdogResponse(
        flow=to_flow_inspect_response(flow),
        stalled_node_attempt_ids=stalled_attempt_ids,
        checkpoint_ids=[checkpoint.id for checkpoint in checkpoints],
    )


@internal_router.post(
    "/{flow_id}/watchdog/recover",
    response_model=FlowWatchdogRecoveryResponse,
    include_in_schema=False,
)
async def recover_watchdog_route(
    flow_id: UUID,
    session: DbSession,
) -> FlowWatchdogRecoveryResponse:
    try:
        recovery_result = await recover_flow_watchdog(session, flow_id=flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OpenClawConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (OpenClawTimeoutError, OpenClawRequestError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except OpenClawIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    await session.commit()
    dispatch_result = recovery_result.dispatch_result
    node_session = recovery_result.flow_node.node_session if recovery_result.flow_node else None
    return FlowWatchdogRecoveryResponse(
        flow=to_flow_inspect_response(recovery_result.flow),
        recovery_action=recovery_result.recovery_action,
        recovery_reason=recovery_result.recovery_reason,
        flow_node_id=recovery_result.flow_node.id if recovery_result.flow_node else None,
        node_attempt_id=recovery_result.node_attempt.id if recovery_result.node_attempt else None,
        node_session_key=node_session.provider_session_key if node_session is not None else None,
        openclaw_response_id=(dispatch_result.response.response_id if dispatch_result else None),
        openclaw_output=(dispatch_result.response.output_text if dispatch_result else None),
        detail=recovery_result.detail,
        operator_next_step=recovery_result.operator_next_step,
    )


@internal_router.get(
    "/{flow_id}/checkpoints",
    response_model=list[CheckpointRead],
    include_in_schema=False,
)
async def get_flow_checkpoints(flow_id: UUID, session: DbSession) -> list[CheckpointRead]:
    try:
        checkpoints_ = await list_flow_checkpoints(session, flow_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [to_checkpoint_read(cp) for cp in checkpoints_]


def _content_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


@internal_router.post(
    "/context-items",
    response_model=ContextItemAuditRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def publish_context_item_route(
    payload: InternalContextItemPublish,
    session: DbSession,
) -> ContextItemAuditRead:
    await lock_flow(session, payload.flow_id)
    manifest = await get_context_manifest(session, payload.manifest_id)
    if manifest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No context manifest found: {payload.manifest_id}",
        )
    if manifest.flow_id != payload.flow_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Manifest does not belong to flow"
        )
    if manifest.flow_node_id != payload.flow_node_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Manifest does not belong to flow node"
        )
    if manifest.node_attempt_id != payload.node_attempt_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Manifest does not belong to node attempt"
        )
    if manifest.status != ContextManifestStatus.ACKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Context publication requires the latest acknowledged manifest",
        )

    ensure_flow_not_terminal(manifest.flow)
    node_session = ensure_node_session_key(
        manifest.node_session,
        node_session_key=payload.node_session_key,
    )
    ensure_current_attempt(
        manifest.flow,
        manifest.flow_node,
        manifest.node_attempt,
        allowed_statuses={NodeAttemptStatus.RUNNING, NodeAttemptStatus.BLOCKED},
        require_current_session=True,
        node_session=node_session,
    )
    ensure_latest_acked_manifest(
        manifest.flow,
        manifest.node_attempt,
        node_session,
        manifest_id=manifest.id,
        manifest_hash=payload.manifest_hash,
        ack_checkpoint_id=payload.ack_checkpoint_id,
    )

    item = ContextItem(
        task_id=manifest.flow.task_id,
        flow_id=manifest.flow_id,
        flow_revision_id=manifest.node_attempt.flow_revision_id,
        flow_node_id=manifest.flow_node_id,
        node_attempt_id=manifest.node_attempt_id,
        scope=payload.scope,
        kind=payload.kind,
        visibility_policy=payload.visibility_policy,
        status=ContextItemStatus.PUBLISHED,
        title=payload.title,
        storage_uri=(payload.storage_uri or f"context-item://{manifest.flow_id}/{uuid4().hex}"),
        content_hash=_content_hash(payload.content),
        metadata_={**payload.metadata, "inline_content": payload.content},
        published_by="tool:publish_context_item",
        published_at=utcnow_naive(),
    )
    session.add(item)
    await session.flush()
    await session.commit()
    return to_context_item_audit_read(item)


@internal_router.post(
    "/checkpoints",
    response_model=CheckpointRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_checkpoint(payload: InternalCheckpointWrite, session: DbSession) -> CheckpointRead:
    try:
        checkpoint = await record_checkpoint(session, payload)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if isinstance(exc, NotFoundError)
            else status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if payload.status in {CheckpointStatus.GREEN, CheckpointStatus.RETRY}:
        await advance_flow_until_boundary(
            session,
            payload.flow_id,
            cause=f"checkpoint:{payload.status.value}",
        )
    await session.commit()
    return to_checkpoint_read(checkpoint)


@internal_router.post(
    "/context-manifests/{manifest_id}/ack",
    response_model=FlowInspectResponse,
    include_in_schema=False,
)
@internal_router.post(
    "/{flow_id}/context-manifests/{manifest_id}/ack",
    response_model=FlowInspectResponse,
    include_in_schema=False,
)
async def acknowledge_context_manifest_route(
    manifest_id: str,
    payload: ContextManifestAckWrite,
    session: DbSession,
    flow_id: UUID | None = None,
) -> FlowInspectResponse:
    try:
        normalized_manifest_id = parse_uuid_like(manifest_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        manifest = await acknowledge_context_manifest(
            session,
            normalized_manifest_id,
            manifest_hash=payload.manifest_hash,
            node_session_key=payload.node_session_key,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if flow_id is not None and parse_uuid_like(manifest.flow_id) != flow_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Context manifest {manifest.id} does not belong to flow {flow_id}",
        )

    await advance_flow_until_boundary(
        session,
        manifest.flow_id,
        cause="context-acknowledged",
    )
    await session.commit()

    flow = await get_flow_with_relations(session, manifest.flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No flow found after ack: {manifest.flow_id}",
        )
    return to_flow_inspect_response(flow)


@internal_router.get(
    "/{flow_id}/context-manifests",
    response_model=list[ContextManifestRead],
    include_in_schema=False,
)
async def get_flow_manifests(flow_id: UUID, session: DbSession) -> list[ContextManifestRead]:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No flow found: {flow_id}"
        )
    return [to_context_manifest_read(manifest) for manifest in flow.context_manifests]
