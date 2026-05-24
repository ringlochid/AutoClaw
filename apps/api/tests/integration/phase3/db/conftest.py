from __future__ import annotations

from collections.abc import Generator

import pytest
from tests.integration.phase3.db.context import phase3_db_gateway_server_context
from tests.integration.phase4a.support import LocalGatewayTestServer


@pytest.fixture(autouse=True)
def _configure_phase3_db_gateway_wait_ok(
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> Generator[None, None, None]:
    with phase3_db_gateway_server_context(openclaw_gateway_test_server):
        yield
