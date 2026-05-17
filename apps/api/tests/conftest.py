from __future__ import annotations

import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from app.config import get_settings
from app.runtime.openclaw.fixtures import agent_wait_fixture

from tests.integration.phase4a.support import LocalGatewayTestServer

os.environ.setdefault("AUTOCLAW_ENV", "test")
os.environ.setdefault("AUTOCLAW_DEBUG", "false")
os.environ.setdefault("AUTOCLAW_API_KEY", "autoclaw-operator-test-key")
os.environ.setdefault("AUTOCLAW_INTERNAL_API_KEY", "autoclaw-internal-test-key")

get_settings.cache_clear()


_OPENCLAW_GATEWAY_TEST_SEGMENTS = (
    ("integration", "phase3"),
    ("integration", "phase4a"),
    ("e2e", "phase2"),
    ("e2e", "phase3"),
    ("e2e", "phase4"),
)
_PHASE3_ROUTE_GATEWAY_TIMEOUT_SEGMENT = ("integration", "phase3", "routes")
_PHASE3_CONTRACT_GATEWAY_TIMEOUT_SEGMENT = ("integration", "phase3", "contracts")
_GATEWAY_TIMEOUT_BY_DEFAULT_SEGMENTS = (
    _PHASE3_ROUTE_GATEWAY_TIMEOUT_SEGMENT,
    _PHASE3_CONTRACT_GATEWAY_TIMEOUT_SEGMENT,
    ("integration", "phase3", "db"),
    ("e2e", "phase2"),
    ("e2e", "phase3"),
    ("e2e", "phase4"),
)
_QUIET_SQLALCHEMY_E2E_SEGMENTS = (
    ("e2e", "phase2"),
    ("e2e", "phase3"),
    ("e2e", "phase4"),
)
_SQLALCHEMY_LOGGER_NAMES = (
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.engine.Engine",
)


def _test_needs_openclaw_gateway(path: Path) -> bool:
    parts = path.parts
    try:
        tests_index = parts.index("tests")
    except ValueError:
        return False
    relative_parts = parts[tests_index + 1 :]
    return any(
        relative_parts[: len(segment)] == segment for segment in _OPENCLAW_GATEWAY_TEST_SEGMENTS
    )


def _test_is_phase3_route_lane(path: Path) -> bool:
    parts = path.parts
    try:
        tests_index = parts.index("tests")
    except ValueError:
        return False
    relative_parts = parts[tests_index + 1 :]
    return relative_parts[: len(_PHASE3_ROUTE_GATEWAY_TIMEOUT_SEGMENT)] == (
        _PHASE3_ROUTE_GATEWAY_TIMEOUT_SEGMENT
    )


def _test_prefers_gateway_wait_timeout(path: Path) -> bool:
    parts = path.parts
    try:
        tests_index = parts.index("tests")
    except ValueError:
        return False
    relative_parts = parts[tests_index + 1 :]
    return any(
        relative_parts[: len(segment)] == segment
        for segment in _GATEWAY_TIMEOUT_BY_DEFAULT_SEGMENTS
    )


def _test_prefers_quiet_sqlalchemy_logs(path: Path) -> bool:
    parts = path.parts
    try:
        tests_index = parts.index("tests")
    except ValueError:
        return False
    relative_parts = parts[tests_index + 1 :]
    return any(
        relative_parts[: len(segment)] == segment for segment in _QUIET_SQLALCHEMY_E2E_SEGMENTS
    )


@pytest.fixture(scope="session")
def openclaw_gateway_test_server() -> Generator[LocalGatewayTestServer, None, None]:
    server = LocalGatewayTestServer()
    server.start()
    yield server
    server.close()


@pytest.fixture(autouse=True)
def _quiet_sqlalchemy_logs_for_selected_e2e_tests(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    path = getattr(request.node, "path", None)
    if path is None or not _test_prefers_quiet_sqlalchemy_logs(Path(path)):
        yield
        return

    logger_state: list[tuple[logging.Logger, int, bool]] = []
    for logger_name in _SQLALCHEMY_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger_state.append((logger, logger.level, logger.propagate))
        logger.setLevel(logging.WARNING)
        logger.propagate = False
    try:
        yield
    finally:
        for logger, level, propagate in logger_state:
            logger.setLevel(level)
            logger.propagate = propagate


@pytest.fixture(autouse=True)
def _configure_openclaw_gateway_for_selected_tests(
    request: pytest.FixtureRequest,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> Generator[None, None, None]:
    openclaw_gateway_test_server.clear_requests()
    path = getattr(request.node, "path", None)
    if path is None or not _test_needs_openclaw_gateway(Path(path)):
        yield
        return
    if _test_prefers_gateway_wait_timeout(Path(path)):
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
    with openclaw_gateway_test_server.configured_env():
        yield
