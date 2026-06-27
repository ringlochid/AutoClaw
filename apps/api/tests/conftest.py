from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture

from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support.dispatch import (
    gateway_test_server_context,
)

os.environ["AUTOCLAW_ENV"] = "test"
os.environ["AUTOCLAW_DEBUG"] = "false"
os.environ["AUTOCLAW_API_KEY"] = "autoclaw-operator-test-key"
os.environ["AUTOCLAW_INTERNAL_API_KEY"] = "autoclaw-internal-test-key"

get_settings.cache_clear()


_REQUIRES_OPENCLAW_GATEWAY = "requires_openclaw_gateway"
_GATEWAY_WAIT_TIMEOUT_DEFAULT = "gateway_wait_timeout_default"
_QUIET_SQLALCHEMY_LOGS = "quiet_sqlalchemy_logs"
_SQLALCHEMY_LOGGER_NAMES = (
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.engine.Engine",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        f"{_REQUIRES_OPENCLAW_GATEWAY}: configure the local OpenClaw gateway test server.",
    )
    config.addinivalue_line(
        "markers",
        (f"{_GATEWAY_WAIT_TIMEOUT_DEFAULT}: use timeout responses for default gateway wait calls."),
    )
    config.addinivalue_line(
        "markers",
        f"{_QUIET_SQLALCHEMY_LOGS}: silence noisy SQLAlchemy loggers for the marked tests.",
    )


def _has_marker(request: pytest.FixtureRequest, marker_name: str) -> bool:
    return request.node.get_closest_marker(marker_name) is not None


def _needs_openclaw_gateway(request: pytest.FixtureRequest) -> bool:
    return _has_marker(request, _REQUIRES_OPENCLAW_GATEWAY) or (
        "openclaw_gateway_test_server" in request.fixturenames
    )


@pytest.fixture(scope="session")
def openclaw_gateway_test_server() -> Generator[LocalGatewayTestServer, None, None]:
    server = LocalGatewayTestServer()
    server.start()
    yield server
    server.close()


@pytest.fixture(autouse=True)
def quiet_sqlalchemy_logs_for_selected_e2e_tests(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    if not _has_marker(request, _QUIET_SQLALCHEMY_LOGS):
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
def configure_openclaw_gateway_for_selected_tests(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    if not _needs_openclaw_gateway(request):
        yield
        return

    openclaw_gateway_test_server = request.getfixturevalue("openclaw_gateway_test_server")
    openclaw_gateway_test_server.clear_requests()
    if _has_marker(request, _GATEWAY_WAIT_TIMEOUT_DEFAULT):
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
    with (
        openclaw_gateway_test_server.configured_env(),
        gateway_test_server_context(openclaw_gateway_test_server),
    ):
        yield


@pytest_asyncio.fixture(autouse=True)
async def cleanup_runtime_async_state() -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        from autoclaw.persistence.session import dispose_test_db_engine
        from autoclaw.runtime.lifecycle import shutdown_runtime_lifecycle

        await shutdown_runtime_lifecycle()
        await dispose_test_db_engine()
