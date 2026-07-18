from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

DEFAULT_GATEWAY_CALL_TIMEOUT_MS = 10_000
GATEWAY_PROCESS_EXIT_GRACE_SECONDS = 2.0
MAX_GATEWAY_RESPONSE_BYTES = 1_048_576


class OpenClawGatewayFailureCode(StrEnum):
    NOT_INSTALLED = "openclaw_not_installed"
    PROCESS_LAUNCH_FAILED = "openclaw_process_launch_failed"
    AUTHENTICATION_FAILED = "openclaw_authentication_failed"
    UNREACHABLE = "openclaw_gateway_unreachable"
    REJECTED = "openclaw_gateway_rejected"
    TIMEOUT = "openclaw_gateway_timeout"
    INVALID_RESPONSE = "openclaw_gateway_invalid_response"
    CALL_FAILED = "openclaw_gateway_call_failed"


class OpenClawGatewayCliError(RuntimeError):
    """Expose only a stable code and acceptance certainty for one CLI call."""

    def __init__(
        self,
        *,
        code: OpenClawGatewayFailureCode,
        may_have_been_accepted: bool,
    ) -> None:
        super().__init__(code.value)
        self.code = code
        self.may_have_been_accepted = may_have_been_accepted


async def call_openclaw_gateway(
    *,
    profile: str,
    gateway_url: str,
    method: str,
    params: Mapping[str, object],
    working_directory: Path | None = None,
    timeout_ms: int = DEFAULT_GATEWAY_CALL_TIMEOUT_MS,
) -> dict[str, object]:
    """Call one Gateway method through the user-installed OpenClaw CLI."""

    command = build_openclaw_gateway_command(
        profile=profile,
        gateway_url=gateway_url,
        method=method,
        params=params,
        timeout_ms=timeout_ms,
    )
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=None if working_directory is None else str(working_directory),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise OpenClawGatewayCliError(
            code=OpenClawGatewayFailureCode.NOT_INSTALLED,
            may_have_been_accepted=False,
        ) from None
    except OSError:
        raise OpenClawGatewayCliError(
            code=OpenClawGatewayFailureCode.PROCESS_LAUNCH_FAILED,
            may_have_been_accepted=False,
        ) from None

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=(timeout_ms / 1000) + GATEWAY_PROCESS_EXIT_GRACE_SECONDS,
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        raise OpenClawGatewayCliError(
            code=OpenClawGatewayFailureCode.TIMEOUT,
            may_have_been_accepted=method in {"agent", "sessions.abort"},
        ) from None

    if process.returncode != 0:
        code, is_definite = classify_gateway_cli_failure(stderr)
        raise OpenClawGatewayCliError(
            code=code,
            may_have_been_accepted=method == "agent" and not is_definite,
        )
    return parse_gateway_response(stdout, may_accept_work=method == "agent")


def build_openclaw_gateway_command(
    *,
    profile: str,
    gateway_url: str,
    method: str,
    params: Mapping[str, object],
    timeout_ms: int,
) -> tuple[str, ...]:
    """Build the non-final-waiting Gateway CLI request."""

    serialized_params = json.dumps(
        params,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        "openclaw",
        "--profile",
        profile,
        "gateway",
        "call",
        method,
        "--url",
        gateway_url,
        "--params",
        serialized_params,
        "--json",
        "--timeout",
        str(timeout_ms),
    )


def classify_gateway_cli_failure(
    stderr: bytes,
) -> tuple[OpenClawGatewayFailureCode, bool]:
    """Classify a bounded diagnostic without returning provider text."""

    diagnostic = stderr[:16_384].decode("utf-8", errors="replace").casefold()
    if any(
        marker in diagnostic
        for marker in (
            "explicit credentials",
            "authentication",
            "not authenticated",
            "unauthorized",
            "forbidden",
        )
    ):
        return OpenClawGatewayFailureCode.AUTHENTICATION_FAILED, True
    if any(
        marker in diagnostic
        for marker in (
            "econnrefused",
            "connection refused",
            "enotfound",
            "could not connect",
            "failed to connect",
        )
    ):
        return OpenClawGatewayFailureCode.UNREACHABLE, True
    if any(
        marker in diagnostic
        for marker in (
            "invalid agent params",
            "invalid request",
            "not supported",
            "unsupported",
            "rejected",
        )
    ):
        return OpenClawGatewayFailureCode.REJECTED, True
    if "timeout" in diagnostic or "timed out" in diagnostic:
        return OpenClawGatewayFailureCode.TIMEOUT, False
    return OpenClawGatewayFailureCode.CALL_FAILED, False


def parse_gateway_response(
    stdout: bytes,
    *,
    may_accept_work: bool,
) -> dict[str, object]:
    """Parse one bounded JSON object without retaining raw CLI output."""

    if len(stdout) > MAX_GATEWAY_RESPONSE_BYTES:
        raise OpenClawGatewayCliError(
            code=OpenClawGatewayFailureCode.INVALID_RESPONSE,
            may_have_been_accepted=may_accept_work,
        )
    try:
        payload = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise OpenClawGatewayCliError(
            code=OpenClawGatewayFailureCode.INVALID_RESPONSE,
            may_have_been_accepted=may_accept_work,
        ) from None
    if not isinstance(payload, dict):
        raise OpenClawGatewayCliError(
            code=OpenClawGatewayFailureCode.INVALID_RESPONSE,
            may_have_been_accepted=may_accept_work,
        )
    return payload


__all__ = [
    "DEFAULT_GATEWAY_CALL_TIMEOUT_MS",
    "OpenClawGatewayCliError",
    "OpenClawGatewayFailureCode",
    "build_openclaw_gateway_command",
    "call_openclaw_gateway",
    "classify_gateway_cli_failure",
    "parse_gateway_response",
]
