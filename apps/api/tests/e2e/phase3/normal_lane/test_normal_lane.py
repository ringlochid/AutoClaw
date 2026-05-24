from __future__ import annotations

from pathlib import Path

from tests.e2e.phase3.normal_lane.flow import run_phase3_normal_lane
from tests.integration.phase4a.support import LocalGatewayTestServer


async def test_phase3_normal_e2e_lane_runs_parent_subtree_release_and_final_readback(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    await run_phase3_normal_lane(tmp_path, openclaw_gateway_test_server)
