from __future__ import annotations

from pathlib import Path

import pytest
from tests.e2e.workflows.maximal.flow import run_phase4_maximal_lane
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer

pytestmark = [
    pytest.mark.requires_openclaw_gateway,
    pytest.mark.gateway_wait_timeout_default,
    pytest.mark.quiet_sqlalchemy_logs,
]


async def test_phase4_maximal_e2e_lane_runs_multiple_subtrees_and_final_release(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    await run_phase4_maximal_lane(tmp_path, openclaw_gateway_test_server)
