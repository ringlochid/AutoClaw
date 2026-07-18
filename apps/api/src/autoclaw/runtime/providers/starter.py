from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath

from pydantic import SecretStr, ValidationError
from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import RuntimeSettings
from autoclaw.definitions.contracts.registry import NetworkAccess, ProviderNativeAccess
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import TaskEventSource, TaskEventType
from autoclaw.runtime.contracts.provider_resolution import (
    ClaudeProviderRoute,
    CodexProviderRoute,
    OpenClawProviderRoute,
    ProviderRoute,
)
from autoclaw.runtime.dispatch.provider_start import (
    ProviderStartAcceptanceResult,
    ProviderStartCandidate,
    accept_provider_start_if_current,
    provider_start_is_current,
    read_provider_start_acceptance_after_commit,
    read_provider_start_candidate,
    rotate_provider_start_after_failure,
)
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.node_mcp import DispatchMcpBinding, DispatchMcpBindingRegistry
from autoclaw.runtime.node_operations import NodeOperationExecutor, NodeOperationScope
from autoclaw.runtime.post_commit import (
    AsyncSessionContextFactory,
    DeadlineScheduler,
    DispatchStartDue,
    RuntimeEffectPublisher,
    WatchdogDeadlineChanged,
)
from autoclaw.runtime.providers.contracts import (
    DEFAULT_PROVIDER_STOP_TIMEOUT_SECONDS,
    CompatibilityNodeMcpConnection,
    DispatchStartRequest,
    ManagedNodeMcpConnection,
    ProviderAdapter,
    ProviderStartError,
    ProviderStartErrorCode,
    ProviderStartFailureKind,
)
from autoclaw.runtime.providers.registry import ProviderAdapterRegistry
from autoclaw.runtime.providers.resolution import validate_provider_execution_policy
from autoclaw.runtime.task_events import append_task_event
from autoclaw.runtime.task_root import (
    read_logical_regular_file_bytes,
    read_task_root_paths,
)
from autoclaw.runtime.watchdog import calculate_watchdog_due_at

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _PreparedProviderStart:
    request: DispatchStartRequest
    binding: DispatchMcpBinding | None


class DispatchStarter:
    """Handle one exact provider-start generation without provider observation."""

    def __init__(
        self,
        *,
        adapters: ProviderAdapterRegistry,
        binding_registry: DispatchMcpBindingRegistry,
        operation_executor: NodeOperationExecutor,
        scheduler: DeadlineScheduler,
        runtime_effect_publisher: RuntimeEffectPublisher,
        runtime_settings: RuntimeSettings,
        session_factory: AsyncSessionContextFactory,
        managed_node_mcp_url: str,
        compatibility_node_mcp_url: str,
        clock: Callable[[], datetime] = utc_now,
        stop_timeout_seconds: float = DEFAULT_PROVIDER_STOP_TIMEOUT_SECONDS,
    ) -> None:
        if stop_timeout_seconds <= 0:
            raise ValueError("provider stop timeout must be positive")
        self._adapters = adapters
        self._binding_registry = binding_registry
        self._operation_executor = operation_executor
        self._scheduler = scheduler
        self._runtime_effect_publisher = runtime_effect_publisher
        self._runtime_settings = runtime_settings.model_copy(deep=True)
        self._session_factory = session_factory
        self._managed_node_mcp_url = managed_node_mcp_url
        self._compatibility_node_mcp_url = compatibility_node_mcp_url
        self._clock = clock
        self._stop_timeout_seconds = stop_timeout_seconds
        self._in_flight_dispatches: set[str] = set()
        self._recovered_start_signals: set[DispatchStartDue] = set()

    def mark_recovered(self, signal: DispatchStartDue) -> None:
        """Mark one startup-audit signal for conservative stop-and-retry."""
        self._recovered_start_signals.add(signal)

    async def handle(self, session: AsyncSession, signal: DispatchStartDue) -> None:
        """Schedule a future hint or process one due exact generation once."""
        if _as_utc(signal.due_at) > _as_utc(self._clock()):
            self._scheduler.register(signal)
            return
        if signal.dispatch_id in self._in_flight_dispatches:
            return

        self._in_flight_dispatches.add(signal.dispatch_id)
        try:
            if signal in self._recovered_start_signals:
                await self._handle_recovered_due(session, signal)
            else:
                await self._handle_due(session, signal)
        finally:
            self._in_flight_dispatches.discard(signal.dispatch_id)
            self._recovered_start_signals.discard(signal)

    async def _handle_recovered_due(
        self,
        session: AsyncSession,
        signal: DispatchStartDue,
    ) -> None:
        candidate = await read_provider_start_candidate(session, signal)
        await session.rollback()
        if candidate is None:
            return
        if candidate.provider_kind is None:
            await _fail_invalid_request(
                session,
                signal=signal,
                candidate=candidate,
                failed_at=self._clock(),
                failure_code="dispatch_provider_route_invalid",
            )
            return
        try:
            adapter = self._adapters.get(candidate.provider_kind)
        except LookupError:
            await _fail_invalid_request(
                session,
                signal=signal,
                candidate=candidate,
                failed_at=self._clock(),
                failure_code="dispatch_provider_adapter_missing",
            )
            return

        if _is_initial_watchdog_recovery(candidate, signal):
            await self._stop_watchdog_predecessor(session, candidate)
        self._binding_registry.revoke_dispatch(signal.dispatch_id)
        await self._record_provider_failure(
            session,
            signal=signal,
            candidate=candidate,
            adapter=adapter,
            binding=None,
            failure_kind=ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE,
            error_code=ProviderStartErrorCode.UNCERTAIN,
        )

    async def _handle_due(self, session: AsyncSession, signal: DispatchStartDue) -> None:
        candidate = await read_provider_start_candidate(session, signal)
        await session.rollback()
        if candidate is None:
            return

        if candidate.provider_kind is None:
            await _fail_invalid_request(
                session,
                signal=signal,
                candidate=candidate,
                failed_at=self._clock(),
                failure_code="dispatch_provider_route_invalid",
            )
            return
        try:
            adapter = self._adapters.get(candidate.provider_kind)
        except LookupError:
            await _fail_invalid_request(
                session,
                signal=signal,
                candidate=candidate,
                failed_at=self._clock(),
                failure_code="dispatch_provider_adapter_missing",
            )
            return

        try:
            prepared = await self._prepare_request(session, signal, candidate)
        except (
            RuntimeOperationError,
            ValidationError,
            UnicodeDecodeError,
            OSError,
            ValueError,
        ) as exc:
            await session.rollback()
            await _fail_invalid_request(
                session,
                signal=signal,
                candidate=candidate,
                failed_at=self._clock(),
                failure_code=_controller_failure_code(exc),
            )
            return

        if _is_initial_watchdog_recovery(candidate, signal):
            await self._stop_watchdog_predecessor(session, candidate)

        if not await provider_start_is_current(
            session,
            signal=signal,
            candidate=candidate,
        ):
            self._revoke(prepared.binding)
            return

        try:
            await adapter.start(prepared.request)
        except asyncio.CancelledError:
            self._revoke(prepared.binding)
            await self._bounded_stop(adapter, signal.dispatch_id)
            raise
        except ProviderStartError as exc:
            await self._record_provider_failure(
                session,
                signal=signal,
                candidate=candidate,
                adapter=adapter,
                binding=prepared.binding,
                failure_kind=exc.kind,
                error_code=exc.code,
            )
            return
        except Exception:
            await self._record_provider_failure(
                session,
                signal=signal,
                candidate=candidate,
                adapter=adapter,
                binding=prepared.binding,
                failure_kind=ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE,
                error_code=ProviderStartErrorCode.UNCERTAIN,
            )
            return

        await self._record_acceptance(
            session,
            signal=signal,
            candidate=candidate,
            adapter=adapter,
            binding=prepared.binding,
        )

    async def _prepare_request(
        self,
        session: AsyncSession,
        signal: DispatchStartDue,
        candidate: ProviderStartCandidate,
    ) -> _PreparedProviderStart:
        if (
            candidate.instructions_logical_path is None
            or candidate.input_logical_path is None
            or candidate.provider_native_access is None
            or candidate.network_access is None
        ):
            raise ValueError("current starting dispatch is missing request records")
        _require_exact_request_refs(
            signal.dispatch_id,
            instructions_logical_path=candidate.instructions_logical_path,
            input_logical_path=candidate.input_logical_path,
        )

        paths = await read_task_root_paths(session, candidate.task_id)
        await session.rollback()
        instructions = read_logical_regular_file_bytes(
            paths,
            candidate.instructions_logical_path,
        )
        input_bytes = read_logical_regular_file_bytes(paths, candidate.input_logical_path)
        instructions.decode("utf-8")
        input_bytes.decode("utf-8")

        binding: DispatchMcpBinding | None = None
        try:
            route = _provider_route(candidate)
            native_access = ProviderNativeAccess(candidate.provider_native_access)
            network_access = NetworkAccess(candidate.network_access)
            validate_provider_execution_policy(
                route=route,
                provider_native_access=native_access,
                network_access=network_access,
            )
            managed_connection: ManagedNodeMcpConnection | None = None
            compatibility_connection: CompatibilityNodeMcpConnection | None = None
            if candidate.provider_kind is None:
                raise ValueError("current starting dispatch has an invalid provider route")
            if candidate.provider_kind in {ProviderKind.CODEX, ProviderKind.CLAUDE}:
                descriptors = await self._operation_executor.list_operations(
                    NodeOperationScope(
                        task_id=candidate.task_id,
                        dispatch_id=signal.dispatch_id,
                        provider_start_revision=signal.provider_start_revision,
                    )
                )
                operation_names = tuple(str(descriptor.name) for descriptor in descriptors)
                issued = self._binding_registry.issue_binding(
                    task_id=candidate.task_id,
                    dispatch_id=signal.dispatch_id,
                    provider_start_revision=signal.provider_start_revision,
                    exposure_ceiling=operation_names,
                )
                binding = issued.binding
                managed_connection = ManagedNodeMcpConnection(
                    url=self._managed_node_mcp_url,
                    bearer_token=SecretStr(issued.credential),
                    enabled_tools=operation_names,
                )
            else:
                compatibility_connection = CompatibilityNodeMcpConnection(
                    url=self._compatibility_node_mcp_url
                )

            request = DispatchStartRequest(
                task_id=candidate.task_id,
                dispatch_id=signal.dispatch_id,
                provider_start_revision=signal.provider_start_revision,
                working_directory=paths.workspace_path,
                instructions=instructions,
                input=input_bytes,
                provider_route=route,
                provider_native_access=native_access,
                network_access=network_access,
                managed_node_mcp=managed_connection,
                compatibility_node_mcp=compatibility_connection,
            )
        except Exception:
            self._revoke(binding)
            raise

        return _PreparedProviderStart(
            request=request,
            binding=binding,
        )

    async def _stop_watchdog_predecessor(
        self,
        session: AsyncSession,
        candidate: ProviderStartCandidate,
    ) -> None:
        predecessor_dispatch_id = candidate.predecessor_dispatch_id
        assert predecessor_dispatch_id is not None
        self._binding_registry.revoke_dispatch(predecessor_dispatch_id)
        predecessor_kind = await session.scalar(
            select(DispatchTurnModel.provider_route_kind).where(
                DispatchTurnModel.dispatch_id == predecessor_dispatch_id,
                DispatchTurnModel.task_id == candidate.task_id,
                DispatchTurnModel.flow_id == candidate.flow_id,
            )
        )
        await session.rollback()
        if predecessor_kind is None:
            return
        try:
            adapter = self._adapters.get(ProviderKind(predecessor_kind))
        except (LookupError, ValueError):
            return
        await self._bounded_stop(adapter, predecessor_dispatch_id)

    async def _record_acceptance(
        self,
        session: AsyncSession,
        *,
        signal: DispatchStartDue,
        candidate: ProviderStartCandidate,
        adapter: ProviderAdapter,
        binding: DispatchMcpBinding | None,
    ) -> None:
        accepted_at = self._clock()
        try:
            result = await accept_provider_start_if_current(
                session,
                task_id=candidate.task_id,
                dispatch_id=signal.dispatch_id,
                expected_provider_start_revision=signal.provider_start_revision,
                expected_provider_start_attempt_count=(candidate.provider_start_attempt_count),
                expected_due_at=candidate.persisted_due_at,
                accepted_at=accepted_at,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            async with self._session_factory() as reconciliation_session:
                reconciled = await read_provider_start_acceptance_after_commit(
                    reconciliation_session,
                    candidate=candidate,
                    signal=signal,
                )
                await reconciliation_session.rollback()
                if reconciled.is_accepted:
                    self._publish_watchdog(signal, reconciled)
                    return
                await self._record_provider_failure(
                    reconciliation_session,
                    signal=signal,
                    candidate=candidate,
                    adapter=adapter,
                    binding=binding,
                    failure_kind=ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE,
                    error_code=ProviderStartErrorCode.UNCERTAIN,
                )
            return

        if not result.is_accepted:
            self._revoke(binding)
            await self._bounded_stop(adapter, signal.dispatch_id)
            return

        self._publish_watchdog(signal, result)

    def _publish_watchdog(
        self,
        signal: DispatchStartDue,
        result: ProviderStartAcceptanceResult,
    ) -> None:
        assert result.adapter_started_at is not None
        assert result.node_activity_revision is not None
        due_at = calculate_watchdog_due_at(
            adapter_started_at=result.adapter_started_at,
            last_node_activity_at=result.last_node_activity_at,
            inactivity_timeout_seconds=(self._runtime_settings.watchdog_inactivity_timeout_seconds),
        )
        self._runtime_effect_publisher.publish(
            WatchdogDeadlineChanged(
                dispatch_id=signal.dispatch_id,
                activity_revision=result.node_activity_revision,
                due_at=due_at,
            )
        )

    async def _record_provider_failure(
        self,
        session: AsyncSession,
        *,
        signal: DispatchStartDue,
        candidate: ProviderStartCandidate,
        adapter: ProviderAdapter,
        binding: DispatchMcpBinding | None,
        failure_kind: ProviderStartFailureKind,
        error_code: ProviderStartErrorCode,
    ) -> None:
        retry = _next_retry_signal(
            signal,
            attempt_count=candidate.provider_start_attempt_count,
            now=self._clock(),
            settings=self._runtime_settings,
        )
        try:
            rotated = await rotate_provider_start_after_failure(
                session,
                signal=signal,
                candidate=candidate,
                retry=retry,
                failure_kind=failure_kind.value,
                error_code=error_code.value,
            )
        except Exception:
            await session.rollback()
            self._revoke(binding)
            if failure_kind is ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE:
                await self._bounded_stop(adapter, signal.dispatch_id)
            raise

        self._revoke(binding)
        if failure_kind is ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE:
            await self._bounded_stop(adapter, signal.dispatch_id)
        if rotated:
            self._scheduler.register(retry)

    def _revoke(self, binding: DispatchMcpBinding | None) -> None:
        if binding is not None:
            self._binding_registry.revoke_binding(binding)

    async def _bounded_stop(self, adapter: ProviderAdapter, dispatch_id: str) -> None:
        try:
            async with asyncio.timeout(self._stop_timeout_seconds):
                await adapter.stop(dispatch_id)
        except Exception as exc:
            logger.warning(
                "provider stop did not complete cleanly",
                extra={
                    "provider_kind": adapter.kind.value,
                    "dispatch_id": dispatch_id,
                    "exception_type": type(exc).__name__,
                },
            )


def _provider_route(candidate: ProviderStartCandidate) -> ProviderRoute:
    if candidate.provider_kind is None:
        raise ValueError("current starting dispatch has an invalid provider route")
    match candidate.provider_kind:
        case ProviderKind.CODEX:
            return CodexProviderRoute(
                kind=ProviderKind.CODEX,
                model_override=candidate.model_override,
                effort_override=candidate.effort_override,
            )
        case ProviderKind.CLAUDE:
            return ClaudeProviderRoute(
                kind=ProviderKind.CLAUDE,
                model_override=candidate.model_override,
                effort_override=candidate.effort_override,
            )
        case ProviderKind.OPENCLAW:
            return OpenClawProviderRoute(
                kind=ProviderKind.OPENCLAW,
                gateway_profile=candidate.gateway_profile or "",
            )


def _require_exact_request_refs(
    dispatch_id: str,
    *,
    instructions_logical_path: str,
    input_logical_path: str,
) -> None:
    expected_root = PurePosixPath("_runtime", "dispatch", dispatch_id)
    if (
        PurePosixPath(instructions_logical_path) != expected_root / "instructions.md"
        or PurePosixPath(input_logical_path) != expected_root / "input.md"
    ):
        raise ValueError("dispatch request refs do not identify the exact dispatch pair")


def _is_initial_watchdog_recovery(
    candidate: ProviderStartCandidate,
    signal: DispatchStartDue,
) -> bool:
    return (
        candidate.opened_reason == "watchdog_recovery"
        and candidate.predecessor_dispatch_id is not None
        and signal.provider_start_revision == 0
        and candidate.provider_start_attempt_count == 0
    )


def _next_retry_signal(
    signal: DispatchStartDue,
    *,
    attempt_count: int,
    now: datetime,
    settings: RuntimeSettings,
) -> DispatchStartDue:
    delay = min(
        settings.dispatch_launch_retry_max_backoff_seconds,
        settings.dispatch_launch_retry_initial_backoff_seconds * (2 ** min(attempt_count, 63)),
    )
    return DispatchStartDue(
        dispatch_id=signal.dispatch_id,
        provider_start_revision=signal.provider_start_revision + 1,
        due_at=_as_utc(now) + timedelta(seconds=delay),
    )


def _controller_failure_code(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    value = getattr(code, "value", None)
    if isinstance(value, str):
        return value
    return "dispatch_start_request_invalid"


async def _fail_invalid_request(
    session: AsyncSession,
    *,
    signal: DispatchStartDue,
    candidate: ProviderStartCandidate,
    failed_at: datetime,
    failure_code: str,
) -> bool:
    """Pause only the exact still-current dispatch with invalid committed input."""
    dispatch_id = await session.scalar(
        update(DispatchTurnModel)
        .where(
            DispatchTurnModel.dispatch_id == signal.dispatch_id,
            DispatchTurnModel.task_id == candidate.task_id,
            DispatchTurnModel.flow_id == candidate.flow_id,
            DispatchTurnModel.status == "starting",
            DispatchTurnModel.provider_start_revision == signal.provider_start_revision,
            DispatchTurnModel.provider_start_attempt_count
            == candidate.provider_start_attempt_count,
            DispatchTurnModel.next_provider_start_at == candidate.persisted_due_at,
            exists().where(
                FlowModel.flow_id == candidate.flow_id,
                FlowModel.task_id == candidate.task_id,
                FlowModel.status == "running",
                FlowModel.current_dispatch_id == signal.dispatch_id,
                FlowModel.waiting_cause == "none",
                FlowModel.control_revision == candidate.flow_control_revision,
            ),
        )
        .values(
            status="closed",
            closed_at=failed_at,
            closed_reason="control_failed",
            next_provider_start_at=None,
            provider_start_retry_kind=None,
            provider_start_last_error_code=None,
        )
        .returning(DispatchTurnModel.dispatch_id)
    )
    if dispatch_id is None:
        await session.rollback()
        return False

    details = {
        "source": "provider_start",
        "source_dispatch_id": signal.dispatch_id,
        "failure_code": failure_code,
    }
    flow_id = await session.scalar(
        update(FlowModel)
        .where(
            FlowModel.flow_id == candidate.flow_id,
            FlowModel.task_id == candidate.task_id,
            FlowModel.status == "running",
            FlowModel.active_flow_revision_id == candidate.flow_revision_id,
            FlowModel.current_dispatch_id == signal.dispatch_id,
            FlowModel.waiting_cause == "none",
            FlowModel.control_revision == candidate.flow_control_revision,
        )
        .values(
            status="paused",
            current_dispatch_id=None,
            pause_reason="runtime_transition_failed",
            pause_details=details,
            paused_at=failed_at,
            paused_by_actor_ref="controller.runtime",
            control_revision=FlowModel.control_revision + 1,
            updated_at=failed_at,
        )
        .returning(FlowModel.flow_id)
    )
    if flow_id is None:
        await session.rollback()
        return False

    await append_task_event(
        session,
        task_id=candidate.task_id,
        event_type=TaskEventType.TASK_PAUSED,
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=failed_at,
        flow_revision_id=candidate.flow_revision_id,
        dispatch_id=signal.dispatch_id,
        attempt_id=candidate.attempt_id,
        node_key=candidate.node_key,
        actor_ref="controller.runtime",
        payload={"reason": "runtime_transition_failed", **details},
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return True


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "DEFAULT_PROVIDER_STOP_TIMEOUT_SECONDS",
    "DispatchStarter",
]
