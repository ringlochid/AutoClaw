from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchCallbackBindingModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    ProviderEventRecordModel,
    WorkspaceRootLeaseModel,
)
from app.runtime.contracts import (
    EvidenceKind,
    FlowStatus,
)
from app.runtime.ids import (
    dispatch_callback_binding_id,
    provider_event_record_id,
)
from app.runtime.post_commit import queue_post_commit_action
from app.runtime.projection import (
    load_task_root_paths,
    materialize_artifact_current_pointer,
    materialize_attempt_files,
    materialize_dispatch_files,
    materialize_manifest,
)
from app.runtime.resources import (
    checkpoint_json_path,
    checkpoint_markdown_path,
    copy_file_if_needed,
)

_DISPATCH_DRAIN_TIMEOUT_SECONDS = 30


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


def _json_list(payload: object) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], payload or [])


def _int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, int | str) else None


def _coerce_source_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _dispatch_control_deadline(*, base: datetime | None = None) -> datetime:
    return (base or _now()) + timedelta(seconds=_DISPATCH_DRAIN_TIMEOUT_SECONDS)


def _is_path_current(path: str | Path) -> bool:
    return Path(path).expanduser().resolve().exists()


def _queue_file_copy(
    session: AsyncSession,
    *,
    source_path: Path,
    destination: Path,
) -> None:
    resolved_source = _coerce_source_path(source_path)
    queue_post_commit_action(
        session,
        key=("copy-file", str(destination)),
        runner=lambda _session: asyncio.to_thread(
            copy_file_if_needed,
            source_path=resolved_source,
            destination=destination,
        ),
    )


def _queue_attempt_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> None:
    queue_post_commit_action(
        session,
        key=("materialize-attempt", task_id, attempt_id),
        runner=lambda post_commit_session: materialize_attempt_files(
            post_commit_session,
            task_id,
            attempt_id,
        ),
    )


def _queue_manifest_materialization(session: AsyncSession, *, task_id: str) -> None:
    async def _runner(post_commit_session: AsyncSession) -> None:
        await materialize_manifest(post_commit_session, task_id)
        return None

    queue_post_commit_action(
        session,
        key=("materialize-manifest", task_id),
        runner=_runner,
    )


def _queue_dispatch_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    queue_post_commit_action(
        session,
        key=("materialize-dispatch", task_id, dispatch_id),
        runner=lambda post_commit_session: materialize_dispatch_files(
            post_commit_session,
            task_id,
            dispatch_id,
        ),
    )


def _queue_artifact_current_pointer_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> None:
    queue_post_commit_action(
        session,
        key=("materialize-artifact-current", task_id, owner_node_key, slot),
        runner=lambda post_commit_session: materialize_artifact_current_pointer(
            post_commit_session,
            task_id,
            owner_node_key,
            slot,
        ),
    )


async def _count_for_node(
    session: AsyncSession,
    model: type[AttemptModel] | type[DispatchTurnModel],
    task_id: str,
    node_key: str,
) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(model)
        .where(
            model.task_id == task_id,
            model.node_key == node_key,
        )
    )
    return int(count or 0) + 1


async def _flow_by_task(session: AsyncSession, task_id: str) -> FlowModel:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    return flow


async def _live_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> DispatchCallbackBindingModel | None:
    result = await session.execute(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.dispatch_id == dispatch_id,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def validate_callback_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
) -> None:
    binding = await session.scalar(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.session_key == session_key,
        )
    )
    if binding is None:
        raise ValueError("invalid callback session key")
    if binding.binding_status != "live" or binding.revoked_at is not None:
        raise ValueError("stale callback session key")
    flow = await _flow_by_task(session, task_id)
    if flow.current_open_dispatch_id != binding.dispatch_id:
        raise ValueError("stale callback session key")
    if flow.status != FlowStatus.RUNNING.value:
        raise ValueError("inactive callback session key")


async def _revoke_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    binding = await _live_callback_binding(session, task_id=task_id, dispatch_id=dispatch_id)
    if binding is None:
        return
    binding.binding_status = "revoked"
    binding.revoked_at = _now()
    await session.flush()


async def _release_workspace_root_lease(
    session: AsyncSession,
    *,
    task_id: str,
) -> None:
    lease = await session.scalar(
        select(WorkspaceRootLeaseModel).where(
            WorkspaceRootLeaseModel.task_id == task_id,
            WorkspaceRootLeaseModel.lease_status == "live",
        )
    )
    if lease is None:
        return
    lease.lease_status = "released"
    lease.released_at = _now()
    await session.flush()


async def _create_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    attempt_id: str,
    assignment_id: str,
) -> DispatchCallbackBindingModel:
    binding = DispatchCallbackBindingModel(
        dispatch_callback_binding_id=dispatch_callback_binding_id(dispatch_id),
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        assignment_id=assignment_id,
        task_id=task_id,
        session_key=token_urlsafe(24),
        binding_status="live",
    )
    session.add(binding)
    await session.flush()
    return binding


async def _append_provider_event(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    attempt_id: str,
    event_source: str,
    event_kind: str,
    summary: str,
    detail: str | None = None,
    provider_event_name: str | None = None,
    provider_occurred_at: datetime | None = None,
    event_payload_json: dict[str, object] | None = None,
) -> ProviderEventRecordModel:
    next_event_no = (
        int(
            await session.scalar(
                select(func.max(ProviderEventRecordModel.event_no)).where(
                    ProviderEventRecordModel.dispatch_id == dispatch.dispatch_id
                )
            )
            or 0
        )
        + 1
    )
    row = ProviderEventRecordModel(
        provider_event_record_id=provider_event_record_id(dispatch.dispatch_id, next_event_no),
        dispatch_id=dispatch.dispatch_id,
        task_id=dispatch.task_id,
        attempt_id=attempt_id,
        event_no=next_event_no,
        event_source=event_source,
        event_kind=event_kind,
        provider_event_name=provider_event_name,
        summary=summary,
        detail=detail,
        event_payload_json=event_payload_json,
        occurred_at=_now(),
        provider_occurred_at=provider_occurred_at,
    )
    session.add(row)
    await session.flush()
    return row


def _ensure_no_staged_child_assignment(
    dispatch: DispatchTurnModel,
    *,
    action_name: str,
) -> None:
    if dispatch.staged_child_assignment_id is not None:
        raise ValueError(f"{action_name} is illegal after staging a child assignment")


def _terminal_release_basis_committed(dispatch: DispatchTurnModel) -> bool:
    return dispatch.release_precondition_kind is not None


def _ensure_no_terminal_release_basis(
    dispatch: DispatchTurnModel,
    *,
    action_name: str,
) -> None:
    if _terminal_release_basis_committed(dispatch):
        raise ValueError(f"{action_name} is illegal after terminal release basis was committed")


async def _latest_checkpoint_for_attempt(
    session: AsyncSession,
    attempt: AttemptModel,
) -> AttemptCheckpointModel | None:
    if attempt.latest_checkpoint_id is None:
        return None
    return await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)


async def _latest_resumable_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> DispatchTurnModel | None:
    dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.attempt_id == attempt_id,
            DispatchTurnModel.accepted_boundary.is_(None),
            DispatchTurnModel.closed_at.is_not(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    return dispatch


async def _latest_closed_dispatch_for_task(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchTurnModel | None:
    dispatch: DispatchTurnModel | None = await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.closed_at.is_not(None),
        )
        .order_by(DispatchTurnModel.closed_at.desc(), DispatchTurnModel.rendered_at.desc())
    )
    return dispatch


async def _current_surfaced_ref_failure(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> str | None:
    if ref.get("kind") == EvidenceKind.CRITERIA.value:
        flow = await _flow_by_task(session, task_id)
        if flow.active_flow_revision_id is None:
            return "current criteria ref is stale"
        nodes = await session.scalars(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id
            )
        )
        for node in nodes:
            for criteria in node.criteria_json:
                if str(criteria.get("slot")) == str(ref.get("slot")) and str(
                    criteria.get("path")
                ) == str(ref["path"]):
                    if not _is_path_current(str(ref["path"])):
                        return "current criteria file is missing"
                    return None
        return "current criteria ref is stale"
    if ref.get("kind") != EvidenceKind.ARTIFACT.value:
        if not _is_path_current(str(ref["path"])):
            if ref.get("kind") == "checkpoint":
                return "current checkpoint file is missing"
            return "current surfaced file is missing"
        return None
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.slot == ref.get("slot"),
            ArtifactCurrentPointerModel.current_path == str(ref["path"]),
            ArtifactCurrentPointerModel.current_version == ref.get("version"),
        )
    )
    if pointer is None:
        return "current artifact ref is stale"
    if not _is_path_current(pointer.current_path):
        return "current artifact file is missing"
    return None


async def _attempt_checkpoint_projection_failure(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> str | None:
    paths = await load_task_root_paths(session, task_id)
    checkpoint_json = checkpoint_json_path(paths=paths, attempt_id=attempt_id)
    checkpoint_markdown = checkpoint_markdown_path(paths=paths, attempt_id=attempt_id)
    if not _is_path_current(checkpoint_json) or not _is_path_current(checkpoint_markdown):
        return "current checkpoint projection files are missing"
    return None
