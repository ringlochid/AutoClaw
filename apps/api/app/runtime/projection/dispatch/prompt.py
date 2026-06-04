from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AttemptCheckpointModel,
    DispatchTurnModel,
    NodeSessionModel,
)
from app.runtime.contracts import (
    CheckpointProjection,
    ManifestProjection,
    PersistedPromptRecord,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    PromptTransportRequest,
    RenderedPromptBundle,
)
from app.runtime.projection.manifest.context import (
    checkpoint_attempt_id_from_path,
    latest_checkpoint_for_attempt_before_cutoff,
)
from app.runtime.projection.manifest.projection import build_dispatch_manifest_projection
from app.runtime.projection.projection_mappers import (
    assignment_projection_from_model,
    checkpoint_projection_from_model,
    resolved_node_context,
)
from app.runtime.projection.runtime_state import dispatch_runtime_state
from app.runtime.prompt.bundle import render_prompt_bundle
from app.runtime.task_root import (
    load_task_root_paths,
    localize_assignment_projection,
    localize_checkpoint_projection,
    prompt_markdown_path,
    prompt_request_json_path,
    stable_json_hash,
    write_prompt_artifact,
)


async def render_dispatch_prompt(
    session: AsyncSession,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> tuple[RenderedPromptBundle, PersistedPromptRecord]:
    bundle, record = await build_dispatch_prompt(session, task_id, dispatch)
    paths = await load_task_root_paths(session, task_id)
    write_prompt_artifact(paths=paths, prompt_record=record, full_markdown=bundle.full_markdown)
    return bundle, record


async def build_dispatch_prompt(
    session: AsyncSession,
    task_id: str,
    dispatch: DispatchTurnModel,
    *,
    session_key_override: str | None = None,
) -> tuple[RenderedPromptBundle, PersistedPromptRecord]:
    paths = await load_task_root_paths(session, task_id)
    state = await dispatch_runtime_state(session, task_id=task_id, dispatch=dispatch)
    manifest = await build_dispatch_manifest_projection(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    attempt = state.current_attempt
    assignment = state.current_assignment
    checkpoint = await _checkpoint_projection_for_dispatch(
        session,
        dispatch=dispatch,
        manifest=manifest,
    )
    assignment_projection = localize_assignment_projection(
        paths=paths,
        assignment=assignment_projection_from_model(assignment),
    )
    if checkpoint is not None:
        checkpoint = localize_checkpoint_projection(
            paths=paths,
            checkpoint=checkpoint,
        )
    send_mode = PromptSendMode.FULL_PROMPT
    session_key = await _dispatch_prompt_session_key(
        session,
        dispatch=dispatch,
        session_key_override=session_key_override,
    )
    bundle = render_prompt_bundle(
        PromptRenderRequest(
            prompt_family=PromptFamily(dispatch.prompt_name),
            send_mode=send_mode,
            task_id=task_id,
            session_key=session_key,
            current_node=resolved_node_context(state.current_node),
            manifest=manifest,
            assignment=assignment_projection,
            latest_checkpoint=checkpoint,
        )
    )
    transport_request = PromptTransportRequest(
        send_mode=send_mode,
        instructions_text=bundle.instructions_text,
        input_text=bundle.input_text,
    )
    record = PersistedPromptRecord(
        dispatch_id=dispatch.dispatch_id,
        node_key=dispatch.node_key,
        attempt_id=attempt.attempt_id,
        assignment_key=assignment_projection.assignment_key,
        prompt_name=PromptFamily(dispatch.prompt_name),
        send_mode=send_mode,
        rendered_markdown_path=prompt_markdown_path(paths=paths, dispatch_id=dispatch.dispatch_id),
        transport_request_path=prompt_request_json_path(
            paths=paths,
            dispatch_id=dispatch.dispatch_id,
        ),
        content_hash=bundle.content_hash,
        transport_request_hash=stable_json_hash(transport_request),
        rendered_at=dispatch.rendered_at,
        transport_request=transport_request,
    )
    return bundle, record


async def _checkpoint_row_for_path(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    checkpoint_path: Path,
) -> AttemptCheckpointModel | None:
    attempt_id = checkpoint_attempt_id_from_path(checkpoint_path)
    if attempt_id is None:
        return None
    return await latest_checkpoint_for_attempt_before_cutoff(
        session,
        attempt_id=attempt_id,
        recorded_at_cutoff=dispatch.rendered_at,
    )


async def _checkpoint_projection_for_dispatch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    manifest: ManifestProjection,
) -> CheckpointProjection | None:
    relevant_checkpoint_path = manifest.current_context.latest_relevant_checkpoint_path
    if relevant_checkpoint_path is not None:
        relevant_checkpoint_row = await _checkpoint_row_for_path(
            session,
            dispatch=dispatch,
            checkpoint_path=relevant_checkpoint_path,
        )
        if relevant_checkpoint_row is not None:
            return checkpoint_projection_from_model(relevant_checkpoint_row)
    latest_checkpoint_path = manifest.current_context.latest_checkpoint_path
    if latest_checkpoint_path is None:
        return None
    fallback_checkpoint_row = await _checkpoint_row_for_path(
        session,
        dispatch=dispatch,
        checkpoint_path=latest_checkpoint_path,
    )
    if fallback_checkpoint_row is None:
        return None
    return checkpoint_projection_from_model(fallback_checkpoint_row)


async def _dispatch_prompt_session_key(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    session_key_override: str | None,
) -> str | None:
    if session_key_override is not None:
        return session_key_override
    live_session_key = await session.scalar(
        select(NodeSessionModel.session_key)
        .where(
            NodeSessionModel.dispatch_id == dispatch.dispatch_id,
            NodeSessionModel.closed_at.is_(None),
        )
        .order_by(NodeSessionModel.opened_at.desc())
        .limit(1)
    )
    if live_session_key is not None:
        return live_session_key
    dispatch_session_key = await session.scalar(
        select(NodeSessionModel.session_key)
        .where(NodeSessionModel.dispatch_id == dispatch.dispatch_id)
        .order_by(NodeSessionModel.opened_at.desc())
        .limit(1)
    )
    if dispatch_session_key is not None:
        return dispatch_session_key
    return dispatch.gateway_session_key
