from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    AttemptProducedRefModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowNodeModel,
    ProviderEventRecordModel,
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
from app.runtime.projection.state import (
    _assignment_projection_from_model,
    _checkpoint_attempt_id_from_path,
    _checkpoint_projection_from_model,
    _int_or_none,
    _latest_checkpoint_for_attempt_before_cutoff,
    _resolved_node_context,
    build_dispatch_manifest_projection,
    build_manifest_projection,
    current_runtime_state,
    dispatch_runtime_state,
    load_task_root_paths,
)
from app.runtime.prompt.bundle import render_prompt_bundle
from app.runtime.resources import (
    artifact_current_json_path,
    artifact_index_json_path,
    continuity_state_json_path,
    criteria_file_path,
    delivery_state_json_path,
    localize_assignment_projection,
    localize_checkpoint_projection,
    prompt_markdown_path,
    prompt_request_json_path,
    provider_events_ndjson_path,
    stable_json_hash,
    transient_index_json_path,
    watchdog_state_json_path,
    write_assignment_projection,
    write_checkpoint_projection,
    write_json_file,
    write_manifest_projection,
    write_ndjson_file,
    write_prompt_artifact,
)


def _project_provider_event(row: ProviderEventRecordModel) -> dict[str, object | None]:
    return {
        "event_no": row.event_no,
        "dispatch_id": row.dispatch_id,
        "attempt_id": row.attempt_id,
        "event_source": row.event_source,
        "event_kind": row.event_kind,
        "provider_event_name": row.provider_event_name,
        "summary": row.summary,
        "observed_at": row.occurred_at.isoformat(),
        "provider_occurred_at": (
            row.provider_occurred_at.isoformat() if row.provider_occurred_at is not None else None
        ),
        "detail": row.detail,
    }


async def _checkpoint_row_for_path(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    checkpoint_path: Path,
) -> AttemptCheckpointModel | None:
    attempt_id = _checkpoint_attempt_id_from_path(checkpoint_path)
    if attempt_id is None:
        return None
    return await _latest_checkpoint_for_attempt_before_cutoff(
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
            return _checkpoint_projection_from_model(relevant_checkpoint_row)
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
    return _checkpoint_projection_from_model(fallback_checkpoint_row)


async def materialize_attempt_files(session: AsyncSession, task_id: str, attempt_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    attempt = await session.get(AttemptModel, attempt_id)
    if attempt is None:
        raise ValueError(f"unknown attempt_id '{attempt_id}'")
    assignment = await session.scalar(
        select(AssignmentModel).where(AssignmentModel.current_attempt_id == attempt_id)
    )
    if assignment is None:
        assignment = await session.get(AssignmentModel, attempt.assignment_id)
    if assignment is None:
        raise ValueError(f"missing assignment for attempt '{attempt_id}'")
    assignment_projection = localize_assignment_projection(
        paths=paths,
        assignment=_assignment_projection_from_model(assignment),
    )
    write_assignment_projection(
        paths=paths,
        attempt_id=attempt_id,
        assignment=assignment_projection,
    )
    checkpoint_projection = None
    if attempt.latest_checkpoint_id is not None:
        checkpoint = await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)
        if checkpoint is not None:
            checkpoint_projection = localize_checkpoint_projection(
                paths=paths,
                checkpoint=_checkpoint_projection_from_model(checkpoint),
            )
            write_checkpoint_projection(
                paths=paths,
                attempt_id=attempt_id,
                checkpoint=checkpoint_projection,
            )
    produced_refs = list(
        await session.scalars(
            select(AttemptProducedRefModel)
            .where(AttemptProducedRefModel.attempt_id == attempt_id)
            .order_by(AttemptProducedRefModel.order_index.asc())
        )
    )
    write_json_file(
        artifact_index_json_path(paths=paths, attempt_id=attempt_id),
        {
            "attempt_id": attempt_id,
            "node_key": attempt.node_key,
            "assignment_key": assignment.assignment_key,
            "publications": [
                {
                    "owner_node_key": produced.owner_node_key,
                    "slot": produced.slot,
                    "version": produced.version,
                    "path": produced.path,
                    "description": produced.description,
                    "published_at": produced.published_at.isoformat(),
                    "became_current": produced.became_current,
                }
                for produced in produced_refs
            ],
        },
    )
    transient_entries: list[dict[str, str]] = []
    seen_transient_keys: set[tuple[str, str]] = set()
    for transient_ref in (
        *assignment_projection.transient_refs,
        *(checkpoint_projection.transient_refs if checkpoint_projection is not None else ()),
    ):
        entry = {
            "path": str(transient_ref.path),
            "description": transient_ref.description,
        }
        key = (entry["path"], entry["description"])
        if key in seen_transient_keys:
            continue
        seen_transient_keys.add(key)
        transient_entries.append(entry)
    write_json_file(
        transient_index_json_path(paths=paths, attempt_id=attempt_id),
        transient_entries,
    )


def _criteria_markdown(criteria: dict[str, Any]) -> str:
    lines = [f"# {criteria['slot']}", "", str(criteria["description"]), ""]
    lines.extend(f"- {item}" for item in cast(list[str], criteria.get("criteria", [])))
    return "\n".join(lines).rstrip() + "\n"


async def materialize_manifest(session: AsyncSession, task_id: str) -> ManifestProjection:
    paths = await load_task_root_paths(session, task_id)
    state = await current_runtime_state(session, task_id)
    nodes = await session.scalars(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == state.flow_revision.flow_revision_id
        )
    )
    for node in nodes:
        for criteria in node.criteria_json:
            version = _int_or_none(criteria.get("version"))
            criteria_path = (
                Path(str(criteria["path"]))
                if criteria.get("path") is not None
                else criteria_file_path(paths=paths, slot=str(criteria["slot"]), version=version)
            )
            criteria_path.parent.mkdir(parents=True, exist_ok=True)
            criteria_markdown = _criteria_markdown(criteria)
            criteria_path.write_text(criteria_markdown, encoding="utf-8")
            compatibility_path = criteria_file_path(paths=paths, slot=str(criteria["slot"]))
            compatibility_path.write_text(criteria_markdown, encoding="utf-8")
    manifest = await build_manifest_projection(session, task_id)
    write_manifest_projection(paths=paths, manifest=manifest)
    return manifest


async def materialize_artifact_current_pointer(
    session: AsyncSession,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> None:
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.owner_node_key == owner_node_key,
            ArtifactCurrentPointerModel.slot == slot,
        )
    )
    if pointer is None:
        return
    paths = await load_task_root_paths(session, task_id)
    write_json_file(
        artifact_current_json_path(paths=paths, owner_node_key=owner_node_key, slot=slot),
        {
            "owner_node_key": pointer.owner_node_key,
            "slot": pointer.slot,
            "current_version": pointer.current_version,
            "current_path": pointer.current_path,
            "description": pointer.description,
            "assignment_key": pointer.assignment_key,
            "attempt_id": pointer.attempt_id,
            "published_at": pointer.published_at.isoformat(),
            "supersedes_path": pointer.supersedes_path,
        },
    )


async def materialize_dispatch_files(session: AsyncSession, task_id: str, dispatch_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    if dispatch is None:
        raise ValueError(f"missing dispatch '{dispatch_id}'")
    prompt_path = prompt_markdown_path(paths=paths, dispatch_id=dispatch_id)
    prompt_request_path = prompt_request_json_path(paths=paths, dispatch_id=dispatch_id)
    if not prompt_path.exists() or not prompt_request_path.exists():
        bundle, prompt_record = await build_dispatch_prompt(session, task_id, dispatch)
        write_prompt_artifact(
            paths=paths,
            prompt_record=prompt_record,
            full_markdown=bundle.full_markdown,
        )
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
    watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
    provider_events = list(
        await session.scalars(
            select(ProviderEventRecordModel)
            .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
            .order_by(
                ProviderEventRecordModel.event_no.asc(),
                ProviderEventRecordModel.occurred_at.asc(),
            )
        )
    )
    if delivery_state is not None:
        write_json_file(
            delivery_state_json_path(paths=paths, dispatch_id=dispatch_id),
            {
                "dispatch_id": delivery_state.dispatch_id,
                "attempt_id": delivery_state.attempt_id,
                "assignment_key": delivery_state.assignment_key,
                "node_key": delivery_state.node_key,
                "transport_family": delivery_state.transport_family,
                "transport_state": delivery_state.transport_state,
                "controller_observation_state": delivery_state.controller_observation_state,
                "last_provider_event_kind": delivery_state.last_provider_event_kind,
                "provider_final_status": delivery_state.provider_final_status,
                "provider_error": delivery_state.provider_error,
                "send_mode": delivery_state.send_mode,
                "previous_dispatch_id": delivery_state.previous_dispatch_id,
                "superseded_by_dispatch_id": delivery_state.superseded_by_dispatch_id,
                "prepared_at": delivery_state.prepared_at.isoformat(),
                "accepted_at": (
                    delivery_state.accepted_at.isoformat()
                    if delivery_state.accepted_at is not None
                    else None
                ),
                "last_provider_signal_at": (
                    delivery_state.last_provider_signal_at.isoformat()
                    if delivery_state.last_provider_signal_at is not None
                    else None
                ),
                "last_controller_progress_at": (
                    delivery_state.last_controller_progress_at.isoformat()
                    if delivery_state.last_controller_progress_at is not None
                    else None
                ),
                "last_controller_terminal_at": (
                    delivery_state.last_controller_terminal_at.isoformat()
                    if delivery_state.last_controller_terminal_at is not None
                    else None
                ),
                "updated_at": delivery_state.updated_at.isoformat(),
            },
        )
    if continuity_state is not None:
        write_json_file(
            continuity_state_json_path(paths=paths, dispatch_id=dispatch_id),
            {
                "dispatch_id": continuity_state.dispatch_id,
                "attempt_id": continuity_state.attempt_id,
                "assignment_key": continuity_state.assignment_key,
                "node_key": continuity_state.node_key,
                "continuity_state": continuity_state.continuity_state,
                "previous_response_id": continuity_state.previous_response_id,
                "session_key_present": continuity_state.session_key_present,
                "invalidation_reason": continuity_state.invalidation_reason,
                "updated_at": continuity_state.updated_at.isoformat(),
            },
        )
    if watchdog_state is not None:
        write_json_file(
            watchdog_state_json_path(paths=paths, dispatch_id=dispatch_id),
            {
                "dispatch_id": watchdog_state.dispatch_id,
                "attempt_id": watchdog_state.attempt_id,
                "assignment_key": watchdog_state.assignment_key,
                "node_key": watchdog_state.node_key,
                "watchdog_state": watchdog_state.watchdog_state,
                "current_watchdog_kind": watchdog_state.current_watchdog_kind,
                "current_watchdog_reason": watchdog_state.current_watchdog_reason,
                "recovery_action": watchdog_state.recovery_action,
                "recovery_reason": watchdog_state.recovery_reason,
                "recovery_dispatch_id": watchdog_state.recovery_dispatch_id,
                "previous_dispatch_id": watchdog_state.previous_dispatch_id,
                "superseded_by_dispatch_id": watchdog_state.superseded_by_dispatch_id,
                "classified_at": watchdog_state.classified_at.isoformat(),
                "updated_at": watchdog_state.updated_at.isoformat(),
            },
        )
    write_ndjson_file(
        provider_events_ndjson_path(paths=paths, dispatch_id=dispatch_id),
        [_project_provider_event(row) for row in provider_events],
    )


async def build_dispatch_prompt(
    session: AsyncSession,
    task_id: str,
    dispatch: DispatchTurnModel,
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
        assignment=_assignment_projection_from_model(assignment),
    )
    if checkpoint is not None:
        checkpoint = localize_checkpoint_projection(
            paths=paths,
            checkpoint=checkpoint,
        )
    send_mode = PromptSendMode(dispatch.send_mode)
    bundle = render_prompt_bundle(
        PromptRenderRequest(
            prompt_family=PromptFamily(dispatch.prompt_name),
            send_mode=send_mode,
            task_id=task_id,
            current_node=_resolved_node_context(state.current_node),
            manifest=manifest,
            assignment=assignment_projection,
            latest_checkpoint=checkpoint,
        )
    )
    if send_mode == PromptSendMode.SAME_SESSION_CONTINUE:
        bundle = bundle.model_copy(update={"instructions_text": None})
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch.dispatch_id)
    transport_request = PromptTransportRequest(
        send_mode=send_mode,
        previous_response_id=(
            continuity_state.previous_response_id if continuity_state is not None else None
        ),
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


async def render_dispatch_prompt(
    session: AsyncSession,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> tuple[RenderedPromptBundle, PersistedPromptRecord]:
    bundle, record = await build_dispatch_prompt(session, task_id, dispatch)
    paths = await load_task_root_paths(session, task_id)
    write_prompt_artifact(paths=paths, prompt_record=record, full_markdown=bundle.full_markdown)
    return bundle, record
