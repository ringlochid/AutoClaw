from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.helpers.workflow_lane_driver import write_lane_artifact

EXPECTED_TRACE_NODE_KEYS = (
    "root",
    "implementation_subtree",
    "investigate_issue",
    "implementation_subtree",
    "implement_change",
    "implementation_subtree",
    "review_change",
    "implementation_subtree",
    "root",
    "release_closure",
    "root",
)


@dataclass(frozen=True)
class NormalLaneArtifacts:
    findings_report: Path
    change_patch: Path
    verification_report: Path
    review_report: Path
    closure_report: Path


def materialize_artifacts(task_root: Path) -> NormalLaneArtifacts:
    return NormalLaneArtifacts(
        findings_report=write_lane_artifact(
            task_root,
            "investigate/findings_report.md",
            "Findings: refresh token path regressed after scope narrowing.\n",
        ),
        change_patch=write_lane_artifact(
            task_root,
            "implement/change_patch.diff",
            "diff --git a/auth.py b/auth.py\n",
        ),
        verification_report=write_lane_artifact(
            task_root,
            "implement/verification_report.md",
            "Verification: targeted regression checks passed.\n",
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
