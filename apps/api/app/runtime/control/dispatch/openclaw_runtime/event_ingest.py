from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime

from app.db.models import DispatchDeliveryStateModel, DispatchTurnModel
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch.gateway_observability import (
    OPENCLAW_GATEWAY_TRANSPORT_FAMILY,
    record_gateway_transport_failure,
)
from app.runtime.control.dispatch.openclaw_runtime.lease import (
    close_dispatch_launch_lease,
)
from app.runtime.control.dispatch.openclaw_runtime.models import (
    COMPLETED_RAW_EVENT_LABELS,
    EVENT_POLL_TIMEOUT_SECONDS,
    FAILED_RAW_EVENT_LABELS,
    PROGRESS_RAW_EVENT_LABELS,
    SUPPORTED_RAW_EVENT_LABELS,
    TERMINAL_DELIVERY_STATUS,
    TOOL_RAW_EVENT_LABELS,
    ActiveOpenClawDispatchRuntime,
    NormalizedOpenClawEvent,
)
from app.runtime.control.dispatch.provider_events import append_provider_event
from app.runtime.openclaw import OpenClawObservedEvent
from app.runtime.openclaw.gateway_event_normalization import (
    normalize_gateway_event_name,
)

LOGGER = logging.getLogger(__name__)


async def run_dispatch_ingest(runtime: ActiveOpenClawDispatchRuntime) -> None:
    try:
        while True:
            event = await runtime.lease.handle.next_event(
                timeout_seconds=EVENT_POLL_TIMEOUT_SECONDS
            )
            if event is None:
                continue
            normalized = normalize_observed_event(runtime, event)
            if normalized is None or event_is_duplicate(runtime, event):
                continue
            await commit_normalized_event(runtime, normalized)
            if normalized.advances_liveness:
                runtime.saw_provider_progress = True
            if normalized.event_kind in TERMINAL_DELIVERY_STATUS:
                await finalize_runtime_after_terminal_event(runtime)
                return
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if runtime.closing:
            return
        LOGGER.warning(
            "openclaw dispatch ingest failed for %s: %s",
            runtime.dispatch_id,
            exc,
        )
        await record_ingest_transport_failure(runtime, exc)
        await finalize_runtime_after_terminal_event(runtime)


async def commit_normalized_event(
    runtime: ActiveOpenClawDispatchRuntime,
    normalized: NormalizedOpenClawEvent,
) -> None:
    async with runtime.session_factory() as session:
        session.info["openclaw_dispatch_runtime"] = runtime.dispatch_id
        dispatch = await session.get(DispatchTurnModel, runtime.dispatch_id)
        delivery_state = await session.get(DispatchDeliveryStateModel, runtime.dispatch_id)
        if not event_matches_runtime(dispatch, delivery_state, runtime):
            return
        committed_at = utc_now()
        await append_provider_event(
            session,
            dispatch=dispatch,
            attempt_id=runtime.attempt_id,
            event_source="provider",
            event_kind=normalized.event_kind,
            summary=normalized.summary,
            detail=normalized.detail,
            provider_event_name=normalized.provider_event_name,
            provider_occurred_at=normalized.provider_occurred_at,
            event_payload_json=normalized.event_payload_json,
        )
        update_delivery_state(
            dispatch=dispatch,
            delivery_state=delivery_state,
            normalized=normalized,
            committed_at=committed_at,
        )
        from app.runtime.effects import (
            commit_runtime_session,
            notify_runtime_effect_runner,
            stage_dispatch_open_outputs,
        )

        stage_dispatch_open_outputs(
            session,
            task_id=runtime.task_id,
            dispatch_id=runtime.dispatch_id,
        )
        await commit_runtime_session(session)
        notify_runtime_effect_runner()


def event_matches_runtime(
    dispatch: DispatchTurnModel | None,
    delivery_state: DispatchDeliveryStateModel | None,
    runtime: ActiveOpenClawDispatchRuntime,
) -> bool:
    if dispatch is None or delivery_state is None:
        return False
    if dispatch.gateway_run_id != runtime.run_id:
        return False
    return dispatch.gateway_session_key is None or session_keys_equal(
        dispatch.gateway_session_key,
        runtime.session_key,
    )


def update_delivery_state(
    *,
    dispatch: DispatchTurnModel,
    delivery_state: DispatchDeliveryStateModel,
    normalized: NormalizedOpenClawEvent,
    committed_at: datetime,
) -> None:
    delivery_state.last_provider_event_kind = normalized.event_kind
    delivery_state.updated_at = committed_at
    if normalized.advances_liveness:
        delivery_state.last_provider_signal_at = committed_at
    terminal_status = TERMINAL_DELIVERY_STATUS.get(normalized.event_kind)
    if terminal_status is None:
        return
    dispatch.delivery_status = terminal_status
    delivery_state.transport_state = terminal_status
    delivery_state.provider_final_status = (
        "ok" if terminal_status == "provider_completed" else "error"
    )
    delivery_state.provider_error = (
        None
        if terminal_status == "provider_completed"
        else extract_provider_error(normalized.event_payload_json)
    )


async def record_ingest_transport_failure(
    runtime: ActiveOpenClawDispatchRuntime,
    error: Exception,
) -> None:
    async with runtime.session_factory() as session:
        session.info["openclaw_dispatch_runtime"] = runtime.dispatch_id
        dispatch = await session.get(DispatchTurnModel, runtime.dispatch_id)
        if dispatch is None:
            return
        changed = await record_gateway_transport_failure(
            session,
            dispatch=dispatch,
            operation="gateway.ingest",
            error=error,
        )
        if not changed:
            return
        from app.runtime.effects import (
            commit_runtime_session,
            notify_runtime_effect_runner,
            stage_dispatch_open_outputs,
        )

        stage_dispatch_open_outputs(
            session,
            task_id=runtime.task_id,
            dispatch_id=runtime.dispatch_id,
        )
        await commit_runtime_session(session)
        notify_runtime_effect_runner()


async def finalize_runtime_after_terminal_event(runtime: ActiveOpenClawDispatchRuntime) -> None:
    runtime.closing = True
    await close_dispatch_launch_lease(runtime.lease)


def normalize_observed_event(
    runtime: ActiveOpenClawDispatchRuntime,
    event: OpenClawObservedEvent,
) -> NormalizedOpenClawEvent | None:
    gateway_event_name = str(event.event).strip()
    provider_event_name = normalize_gateway_event_name(event)
    if provider_event_name is None:
        return None
    if provider_event_name in {"presence", "tick", "health", "shutdown"}:
        return None
    run_id = payload_string(event.payload, "runId", "run_id")
    session_key = payload_string(event.payload, "sessionKey", "session_key", "key")
    if not matches_active_run(runtime, provider_event_name, run_id, session_key):
        return None
    event_payload_json = build_event_payload(
        gateway_event_name=gateway_event_name,
        provider_event_name=provider_event_name,
        run_id=run_id,
        session_key=session_key,
        event=event,
    )
    provider_occurred_at = payload_datetime(event.payload)
    if provider_event_name in PROGRESS_RAW_EVENT_LABELS:
        return normalize_delta_event(
            runtime, provider_event_name, provider_occurred_at, event_payload_json
        )
    if provider_event_name in TOOL_RAW_EVENT_LABELS:
        return build_normalized_event(
            event_kind="tool_event",
            summary="Gateway ingest committed correlated provider tool activity.",
            detail="Correlated provider tool activity was observed for the active run.",
            provider_event_name=provider_event_name,
            provider_occurred_at=provider_occurred_at,
            event_payload_json=event_payload_json,
            advances_liveness=True,
        )
    if provider_event_name in COMPLETED_RAW_EVENT_LABELS:
        return build_normalized_event(
            event_kind="response_completed",
            summary="Gateway ingest committed correlated terminal completion for the active run.",
            detail="The active run reported terminal completion through the raw event stream.",
            provider_event_name=provider_event_name,
            provider_occurred_at=provider_occurred_at,
            event_payload_json=event_payload_json,
            advances_liveness=True,
        )
    assert provider_event_name in FAILED_RAW_EVENT_LABELS
    return build_normalized_event(
        event_kind="response_failed",
        summary="Gateway ingest committed correlated terminal failure for the active run.",
        detail="The active run reported terminal failure through the raw event stream.",
        provider_event_name=provider_event_name,
        provider_occurred_at=provider_occurred_at,
        event_payload_json=event_payload_json,
        advances_liveness=True,
    )


def matches_active_run(
    runtime: ActiveOpenClawDispatchRuntime,
    provider_event_name: str,
    run_id: str | None,
    session_key: str | None,
) -> bool:
    if provider_event_name not in SUPPORTED_RAW_EVENT_LABELS:
        return False
    if run_id != runtime.run_id:
        return False
    return session_key is None or session_keys_equal(session_key, runtime.session_key)


def session_keys_equal(left: str, right: str) -> bool:
    return left.strip().lower() == right.strip().lower()


def build_event_payload(
    *,
    gateway_event_name: str,
    provider_event_name: str,
    run_id: str | None,
    session_key: str | None,
    event: OpenClawObservedEvent,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "transport_family": OPENCLAW_GATEWAY_TRANSPORT_FAMILY,
        "gateway_event": gateway_event_name,
        "gateway_event_label": provider_event_name,
        "gateway_run_id": run_id,
    }
    if session_key is not None:
        payload["gateway_session_key"] = session_key
    stream = payload_string(event.payload, "stream")
    if stream is not None:
        payload["gateway_stream"] = stream
    data = payload_object(event.payload.get("data"))
    phase = payload_string(data, "phase")
    if phase is not None:
        payload["gateway_phase"] = phase
    status = payload_string(data, "status")
    if status is not None:
        payload["gateway_status"] = status
    if event.seq is not None:
        payload["gateway_event_seq"] = event.seq
    if event.state_version is not None:
        payload["gateway_state_version"] = event.state_version
    if "error" in event.payload:
        payload["error"] = event.payload["error"]
    return payload


def normalize_delta_event(
    runtime: ActiveOpenClawDispatchRuntime,
    raw_event_name: str,
    provider_occurred_at: datetime | None,
    event_payload_json: dict[str, object],
) -> NormalizedOpenClawEvent:
    if runtime.saw_provider_progress:
        return build_normalized_event(
            event_kind="output_delta",
            summary="Gateway ingest committed correlated provider output progress.",
            detail="A later correlated provider output event was ingested for the active run.",
            provider_event_name=raw_event_name,
            provider_occurred_at=provider_occurred_at,
            event_payload_json=event_payload_json,
            advances_liveness=True,
        )
    return build_normalized_event(
        event_kind="first_data",
        summary="Gateway ingest committed the first correlated provider output event.",
        detail="The active run produced its first correlated provider output event.",
        provider_event_name=raw_event_name,
        provider_occurred_at=provider_occurred_at,
        event_payload_json=event_payload_json,
        advances_liveness=True,
    )


def build_normalized_event(
    *,
    event_kind: str,
    summary: str,
    detail: str,
    provider_event_name: str,
    provider_occurred_at: datetime | None,
    event_payload_json: dict[str, object],
    advances_liveness: bool,
) -> NormalizedOpenClawEvent:
    return NormalizedOpenClawEvent(
        event_kind=event_kind,
        summary=summary,
        detail=detail,
        provider_event_name=provider_event_name,
        provider_occurred_at=provider_occurred_at,
        event_payload_json=event_payload_json,
        advances_liveness=advances_liveness,
    )


def event_is_duplicate(
    runtime: ActiveOpenClawDispatchRuntime,
    event: OpenClawObservedEvent,
) -> bool:
    if event.seq is not None:
        if event.seq in runtime.seen_gateway_seqs:
            return True
        runtime.seen_gateway_seqs.add(event.seq)
        return False
    fingerprint = repr((str(event.event), event.payload, event.state_version))
    if fingerprint in runtime.seen_event_fingerprints:
        return True
    runtime.seen_event_fingerprints.add(fingerprint)
    return False


def payload_string(payload: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def payload_object(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def payload_datetime(payload: dict[str, object]) -> datetime | None:
    raw_value = payload.get("ts") or payload.get("timestamp") or payload.get("occurredAt")
    if isinstance(raw_value, int | float):
        return datetime.fromtimestamp(raw_value / 1000, tz=UTC)
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return None
        with suppress(ValueError):
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
    return None


def extract_provider_error(event_payload_json: dict[str, object]) -> str | None:
    raw_value = event_payload_json.get("error")
    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()
    if isinstance(raw_value, dict):
        message = raw_value.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return None
