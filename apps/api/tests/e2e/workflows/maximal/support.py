from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.helpers.workflow_lane_driver import write_lane_artifact

EXPECTED_TRACE_NODE_KEYS = (
    "root",
    "discovery",
    "gather_evidence",
    "discovery",
    "root",
    "implementation_loop",
    "plan_iteration",
    "implementation_loop",
    "implement_change",
    "implementation_loop",
    "review_change",
    "implementation_loop",
    "qa_sweep",
    "implementation_loop",
    "root",
    "release_closure",
    "root",
)


@dataclass(frozen=True)
class MaximalLaneArtifacts:
    findings_report: Path
    discovery_notes: Path
    delivery_plan: Path
    change_patch: Path
    verification_report: Path
    review_report: Path
    qa_report: Path
    closure_report: Path


def materialize_artifacts(task_root: Path) -> MaximalLaneArtifacts:
    return MaximalLaneArtifacts(
        findings_report=write_lane_artifact(
            task_root,
            "gather_evidence/findings_report.md",
            "Findings: auth refresh failures cluster around stale token rotation.\n",
        ),
        discovery_notes=write_lane_artifact(
            task_root,
            "gather_evidence/discovery_notes.md",
            "Notes: narrowed the failure to the refresh + session continuity path.\n",
        ),
        delivery_plan=write_lane_artifact(
            task_root,
            "plan_iteration/delivery_plan.md",
            "Plan: patch token rotation, add regression checks, then verify release evidence.\n",
        ),
        change_patch=write_lane_artifact(
            task_root,
            "implement_change/change_patch.diff",
            "diff --git a/auth_refresh.py b/auth_refresh.py\n",
        ),
        verification_report=write_lane_artifact(
            task_root,
            "implement_change/verification_report.md",
            "Verification: refresh regression and continuity checks passed.\n",
        ),
        review_report=write_lane_artifact(
            task_root,
            "review_change/review_report.md",
            "Review: scoped change matches the surfaced plan and findings.\n",
        ),
        qa_report=write_lane_artifact(
            task_root,
            "qa_sweep/qa_report.md",
            "QA: surfaced evidence is coherent and replan-safe for release.\n",
        ),
        closure_report=write_lane_artifact(
            task_root,
            "release_closure/closure_report.md",
            (
                "Release: bounded closure completed from surfaced discovery and "
                "implementation evidence.\n"
            ),
        ),
    )
