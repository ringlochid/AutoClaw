from __future__ import annotations

from pathlib import Path

import pytest
from tests.e2e.workflows.reviewed.flow import run_reviewed_change_release_lane
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer

pytestmark = [
    pytest.mark.requires_openclaw_gateway,
    pytest.mark.gateway_wait_timeout_default,
    pytest.mark.quiet_sqlalchemy_logs,
]


async def test_reviewed_change_release_lane_runs_parent_subtree_and_final_readback(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    await run_reviewed_change_release_lane(tmp_path, openclaw_gateway_test_server)
