from __future__ import annotations

from pathlib import Path

import pytest
from tests.e2e.workflows.normal.flow import run_phase3_normal_lane
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer

pytestmark = [
    pytest.mark.requires_openclaw_gateway,
    pytest.mark.gateway_wait_timeout_default,
    pytest.mark.quiet_sqlalchemy_logs,
]


async def test_phase3_normal_e2e_lane_runs_parent_subtree_release_and_final_readback(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    await run_phase3_normal_lane(tmp_path, openclaw_gateway_test_server)
