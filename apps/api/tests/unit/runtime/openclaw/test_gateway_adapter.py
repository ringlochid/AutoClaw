from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest
from autoclaw.config import OpenClawSettings
from autoclaw.definitions.contracts.registry import NetworkAccess, ProviderNativeAccess
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.integrations.openclaw.gateway import OpenClawGatewayAdapter, cli_transport
from autoclaw.integrations.openclaw.gateway import adapter as adapter_module
from autoclaw.integrations.openclaw.gateway.cli_transport import (
    OpenClawGatewayCliError,
    OpenClawGatewayFailureCode,
    build_openclaw_gateway_command,
    call_openclaw_gateway,
)
from autoclaw.runtime.contracts.provider_resolution import OpenClawProviderRoute
from autoclaw.runtime.providers.contracts import (
    CompatibilityNodeMcpConnection,
    DispatchStartRequest,
    ProviderCheckAxisStatus,
    ProviderCheckStatus,
    ProviderStartError,
    ProviderStartErrorCode,
    ProviderStartFailureKind,
    ProviderStopOutcome,
)


def build_start_request(
    working_directory: Path,
    *,
    provider_start_revision: int = 4,
) -> DispatchStartRequest:
    return DispatchStartRequest(
        task_id="task-1",
        dispatch_id="dispatch-1",
        provider_start_revision=provider_start_revision,
        working_directory=working_directory,
        instructions=b"Exact system instructions",
        input=b"Exact dispatch input",
        provider_route=OpenClawProviderRoute(
            kind=ProviderKind.OPENCLAW,
            gateway_profile="experimental",
        ),
        provider_native_access=ProviderNativeAccess.FULL,
        network_access=NetworkAccess.ALLOW,
        compatibility_node_mcp=CompatibilityNodeMcpConnection(
            url="http://127.0.0.1:18125/node/mcp"
        ),
    )


def test_gateway_command_uses_profile_url_and_never_waits_for_final() -> None:
    command = build_openclaw_gateway_command(
        profile="experimental",
        gateway_url="ws://127.0.0.1:18789",
        method="agent",
        params={
            "message": "input",
            "extraSystemPrompt": "instructions",
        },
        timeout_ms=7_500,
    )

    assert command[:6] == (
        "openclaw",
        "--profile",
        "experimental",
        "gateway",
        "call",
        "agent",
    )
    assert command[6:] == (
        "--url",
        "ws://127.0.0.1:18789",
        "--params",
        '{"message":"input","extraSystemPrompt":"instructions"}',
        "--json",
        "--timeout",
        "7500",
    )
    assert "--expect-final" not in command


@pytest.mark.asyncio
async def test_gateway_transport_returns_one_bounded_json_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spawned: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b'{"status":"accepted","runId":"private-run"}\n', b""

    async def create_process(*args: str, **kwargs: object) -> FakeProcess:
        spawned["args"] = args
        spawned["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    response = await call_openclaw_gateway(
        profile="experimental",
        gateway_url="ws://127.0.0.1:18789",
        method="agent",
        params={"message": "input"},
        working_directory=tmp_path,
    )
    spawned_args = cast(tuple[str, ...], spawned["args"])
    spawned_kwargs = cast(dict[str, object], spawned["kwargs"])

    assert response == {"status": "accepted", "runId": "private-run"}
    assert spawned_args[-3:] == ("--json", "--timeout", "10000")
    assert "--expect-final" not in spawned_args
    assert spawned_kwargs == {
        "cwd": str(tmp_path),
        "stdin": asyncio.subprocess.DEVNULL,
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }


@pytest.mark.asyncio
async def test_start_preserves_two_request_lanes_and_stop_aborts_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    async def call_gateway(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        if kwargs["method"] == "agent":
            return {"status": "accepted", "runId": "private-run"}
        return {"ok": True, "status": "aborted", "abortedRunId": "private-run"}

    monkeypatch.setattr(adapter_module, "call_openclaw_gateway", call_gateway)
    adapter = OpenClawGatewayAdapter(
        config=OpenClawSettings(
            enabled=True,
            gateway_url="ws://127.0.0.1:18789",
            gateway_profile="configured-default",
        )
    )

    await adapter.start(build_start_request(tmp_path))
    first_call = calls[0]
    params = first_call["params"]

    assert first_call["profile"] == "experimental"
    assert first_call["gateway_url"] == "ws://127.0.0.1:18789"
    assert first_call["working_directory"] == tmp_path
    assert isinstance(params, Mapping)
    assert params["message"] == "Exact dispatch input"
    assert params["extraSystemPrompt"] == "Exact system instructions"
    assert params["idempotencyKey"] == "autoclaw:dispatch-1:provider-start:4"
    assert isinstance(params["sessionKey"], str)

    assert await adapter.stop("dispatch-1") is ProviderStopOutcome.STOPPED
    assert calls[1]["method"] == "sessions.abort"
    assert calls[1]["profile"] == "experimental"
    assert calls[1]["params"] == {
        "key": params["sessionKey"],
        "runId": "private-run",
    }
    assert await adapter.stop("dispatch-1") is ProviderStopOutcome.NOT_RUNNING
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("transport_code", "is_acceptance_uncertain", "expected_kind", "expected_code"),
    [
        (
            OpenClawGatewayFailureCode.AUTHENTICATION_FAILED,
            False,
            ProviderStartFailureKind.DEFINITE_FAILURE,
            ProviderStartErrorCode.AUTHENTICATION,
        ),
        (
            OpenClawGatewayFailureCode.TIMEOUT,
            True,
            ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE,
            ProviderStartErrorCode.TIMEOUT,
        ),
    ],
)
async def test_start_classifies_definite_and_uncertain_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    transport_code: OpenClawGatewayFailureCode,
    is_acceptance_uncertain: bool,
    expected_kind: ProviderStartFailureKind,
    expected_code: ProviderStartErrorCode,
) -> None:
    async def fail_gateway(**_kwargs: object) -> dict[str, object]:
        raise OpenClawGatewayCliError(
            code=transport_code,
            is_acceptance_uncertain=is_acceptance_uncertain,
        )

    monkeypatch.setattr(adapter_module, "call_openclaw_gateway", fail_gateway)
    adapter = OpenClawGatewayAdapter(config=OpenClawSettings(enabled=True))

    with pytest.raises(ProviderStartError) as caught:
        await adapter.start(build_start_request(tmp_path))

    assert caught.value.kind is expected_kind
    assert caught.value.code is expected_code


@pytest.mark.asyncio
async def test_start_rejects_nonacceptance_without_storing_a_handle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def call_gateway(**_kwargs: object) -> dict[str, object]:
        return {"status": "complete"}

    monkeypatch.setattr(adapter_module, "call_openclaw_gateway", call_gateway)
    adapter = OpenClawGatewayAdapter(config=OpenClawSettings(enabled=True))

    with pytest.raises(ProviderStartError) as caught:
        await adapter.start(build_start_request(tmp_path))

    assert caught.value.kind is ProviderStartFailureKind.UNCERTAIN_ACCEPTANCE
    assert await adapter.stop("dispatch-1") is ProviderStopOutcome.NOT_RUNNING


@pytest.mark.asyncio
async def test_check_is_non_agent_and_reports_experimental_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    async def call_gateway(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"ok": True}

    monkeypatch.setattr(adapter_module, "call_openclaw_gateway", call_gateway)
    adapter = OpenClawGatewayAdapter(config=OpenClawSettings(enabled=True))

    result = await adapter.read_availability()

    assert result.status is ProviderCheckStatus.LIMITED
    assert result.code == "openclaw_experimental"
    assert result.authentication is ProviderCheckAxisStatus.NOT_CHECKED
    assert result.reachability is ProviderCheckAxisStatus.PASSED
    assert calls == [
        {
            "profile": "default",
            "gateway_url": "ws://127.0.0.1:18789",
            "method": "health",
            "params": {},
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure_code", "expected_authentication", "expected_reachability"),
    (
        (
            OpenClawGatewayFailureCode.AUTHENTICATION_FAILED,
            ProviderCheckAxisStatus.FAILED,
            ProviderCheckAxisStatus.NOT_CHECKED,
        ),
        (
            OpenClawGatewayFailureCode.UNREACHABLE,
            ProviderCheckAxisStatus.NOT_CHECKED,
            ProviderCheckAxisStatus.FAILED,
        ),
        (
            OpenClawGatewayFailureCode.TIMEOUT,
            ProviderCheckAxisStatus.NOT_CHECKED,
            ProviderCheckAxisStatus.FAILED,
        ),
    ),
)
async def test_check_reports_only_the_failed_gateway_axis(
    monkeypatch: pytest.MonkeyPatch,
    failure_code: OpenClawGatewayFailureCode,
    expected_authentication: ProviderCheckAxisStatus,
    expected_reachability: ProviderCheckAxisStatus,
) -> None:
    async def fail_gateway(**_kwargs: object) -> dict[str, object]:
        raise OpenClawGatewayCliError(
            code=failure_code,
            is_acceptance_uncertain=False,
        )

    monkeypatch.setattr(adapter_module, "call_openclaw_gateway", fail_gateway)
    adapter = OpenClawGatewayAdapter(config=OpenClawSettings(enabled=True))

    result = await adapter.read_availability()

    assert result.status is ProviderCheckStatus.UNAVAILABLE
    assert result.authentication is expected_authentication
    assert result.reachability is expected_reachability


def test_failure_classification_does_not_retain_gateway_diagnostics() -> None:
    raw_diagnostic = b"Gateway call failed: unauthorized token=private-secret"

    code, is_definite = cli_transport.classify_gateway_cli_failure(raw_diagnostic)

    assert code is OpenClawGatewayFailureCode.AUTHENTICATION_FAILED
    assert is_definite is True
    assert "private-secret" not in code.value
