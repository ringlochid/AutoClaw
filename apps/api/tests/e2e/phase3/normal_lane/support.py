from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

JsonMap = dict[str, Any]
ArtifactClaims = list[dict[str, str]]

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}
EXPECTED_OPERATOR_CURRENT_PATHS = (
    (
        "manifest",
        "workflow-manifest.md",
        "Whole-workflow visible contract for the current task.",
    ),
    (
        "delivery_state",
        "delivery-state.json",
        "Latest task-scoped delivery-state projection.",
    ),
    (
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    (
        "watchdog_state",
        "watchdog-state.json",
        "Latest task-scoped watchdog-state projection.",
    ),
    (
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)
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
OBSERVABILITY_ROUTES = (
    (
        "delivery-state",
        "delivery_state",
        "delivery-state.json",
        "Latest task-scoped delivery-state projection.",
    ),
    (
        "continuity-state",
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    (
        "watchdog-state",
        "watchdog_state",
        "watchdog-state.json",
        "Latest task-scoped watchdog-state projection.",
    ),
    (
        "provider-events",
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)


@dataclass(frozen=True)
class NormalLaneArtifacts:
    findings_report: Path
    change_patch: Path
    verification_report: Path
    review_report: Path
    closure_report: Path


@dataclass(frozen=True)
class NormalLaneDriver:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]
    task_id: str


def materialize_artifacts(task_root: Path) -> NormalLaneArtifacts:
    return NormalLaneArtifacts(
        findings_report=write_artifact(
            task_root,
            "investigate/findings_report.md",
            "Findings: refresh token path regressed after scope narrowing.\n",
        ),
        change_patch=write_artifact(
            task_root,
            "implement/change_patch.diff",
            "diff --git a/auth.py b/auth.py\n",
        ),
        verification_report=write_artifact(
            task_root,
            "implement/verification_report.md",
            "Verification: targeted regression checks passed.\n",
        ),
        review_report=write_artifact(
            task_root,
            "review/review_report.md",
            "Review: patch is scoped and evidence is sufficient.\n",
        ),
        closure_report=write_artifact(
            task_root,
            "release/closure_report.md",
            "Release: bounded closure completed from current surfaced evidence.\n",
        ),
    )


def write_artifact(task_root: Path, relative_path: str, content: str) -> Path:
    path = task_root / "workspace" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def assert_operator_current_paths(entries: list[JsonMap]) -> None:
    assert [
        (
            entry["kind"],
            Path(str(entry["path"])).name,
            entry["description"],
            entry["slot"],
            entry["version"],
        )
        for entry in entries
    ] == [
        (kind, name, description, None, None)
        for kind, name, description in EXPECTED_OPERATOR_CURRENT_PATHS
    ]


def json_map(response: Response) -> JsonMap:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict)
    return payload
