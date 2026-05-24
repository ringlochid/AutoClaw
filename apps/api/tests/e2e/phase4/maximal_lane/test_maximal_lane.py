from __future__ import annotations

from pathlib import Path

from tests.e2e.phase4.maximal_lane.flow import run_phase4_maximal_lane
from tests.integration.phase4a.support import LocalGatewayTestServer


async def test_phase4_maximal_e2e_lane_runs_multiple_subtrees_and_final_release(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    await run_phase4_maximal_lane(tmp_path, openclaw_gateway_test_server)
