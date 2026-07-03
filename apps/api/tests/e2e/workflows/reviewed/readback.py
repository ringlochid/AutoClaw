from __future__ import annotations

from tests.e2e.workflows.reviewed.support import EXPECTED_TRACE_NODE_KEYS
from tests.helpers.workflow_lane_driver import (
    JsonMap,
    ParentFirstLaneDriver,
    assert_parent_first_final_readback,
)


async def assert_final_readback(
    driver: ParentFirstLaneDriver,
    final_green: JsonMap,
) -> None:
    await assert_parent_first_final_readback(
        driver,
        final_green,
        expected_trace_node_keys=EXPECTED_TRACE_NODE_KEYS,
    )
