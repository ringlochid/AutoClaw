from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.helpers.workflow_lane_driver import write_lane_artifact

EXPECTED_TRACE_NODE_KEYS = (
    "root",
    "change_subtree",
    "scope_change",
    "change_subtree",
    "implement_change",
    "change_subtree",
    "review_change",
    "change_subtree",
    "root",
    "release_closure",
    "root",
)


@dataclass(frozen=True)
class ReviewedLaneArtifacts:
    change_scope_report: Path
    change_patch: Path
    verification_report: Path
    review_report: Path
    closure_report: Path


def materialize_artifacts(task_root: Path) -> ReviewedLaneArtifacts:
    return ReviewedLaneArtifacts(
        change_scope_report=write_lane_artifact(
            task_root,
            "scope_change/change_scope_report.md",
            "Scope: target one small settings-loader cleanup and its regression check.\n",
        ),
        change_patch=write_lane_artifact(
            task_root,
            "implement/change_patch.diff",
            "diff --git a/settings.py b/settings.py\n",
        ),
        verification_report=write_lane_artifact(
            task_root,
            "implement/verification_report.md",
            "Verification: targeted regression check passed.\n",
        ),
        review_report=write_lane_artifact(
            task_root,
            "review/review_report.md",
            "Review: patch is scoped and evidence is sufficient.\n",
        ),
        closure_report=write_lane_artifact(
            task_root,
            "release/closure_report.md",
            "Release: bounded closure completed from current surfaced evidence.\n",
        ),
    )
