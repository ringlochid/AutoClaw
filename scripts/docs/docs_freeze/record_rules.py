from __future__ import annotations

import re

from .paths import EXECUTION_ROOT, ROOT

PHASE_PAGE_BY_NAME = {
    "Phase 0": EXECUTION_ROOT / "phases" / "phase-0-docs-contract-freeze-and-setup.md",
    "Phase 0.5": EXECUTION_ROOT / "phases" / "phase-0.5-cleanup-and-salvage-baseline.md",
    "Phase 1": EXECUTION_ROOT / "phases" / "phase-1-authoring-and-compiler-rewrite.md",
    "Phase 2": EXECUTION_ROOT / "phases" / "phase-2-prompt-manifest-artifact-bootstrap.md",
    "Phase 3": EXECUTION_ROOT / "phases" / "phase-3-runtime-parent-review-and-replan.md",
    "Phase 4A": EXECUTION_ROOT
    / "phases"
    / "phase-4a-openclaw-gateway-session-and-continuity.md",
    "Phase 4B": EXECUTION_ROOT
    / "phases"
    / "phase-4b-watchdog-operator-plugin-and-support-state.md",
    "Phase 4.5": EXECUTION_ROOT
    / "phases"
    / "phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md",
    "Phase 5A": EXECUTION_ROOT / "phases" / "phase-5a-definition-ingest-api-and-cli.md",
    "Phase 5B": EXECUTION_ROOT / "phases" / "phase-5b-packaging-release-and-docs-cutover.md",
}

WORK_PACKAGE_ID_TOKEN = r"P[0-9]+(?:\.[0-9]+|[A-Z])?-WP[0-9]+"

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)#]+)")
REVIEWED_PLAN_PATTERN = re.compile(r"^- reviewed plan: `(?P<value>[^`]+)`$", re.MULTILINE)
REVIEWED_EVIDENCE_PATTERN = re.compile(r"^- reviewed evidence: `(?P<value>[^`]+)`$", re.MULTILINE)
REVIEW_ARTIFACT_PATTERN = re.compile(r"^- review artifact: `(?P<value>[^`]+)`$", re.MULTILINE)
SELECTED_PHASE_PATTERN = re.compile(r"^selected phase: (?P<value>.+)$", re.MULTILINE)
CURRENT_PHASE_PAGE_PATTERN = re.compile(r"^current phase page: (?P<value>\S+)$", re.MULTILINE)
SELECTED_WORK_PACKAGES_PATTERN = re.compile(
    r"^selected work packages: (?P<value>.+)$",
    re.MULTILINE,
)
SELECTED_WORK_PACKAGES_VALUE_PATTERN = re.compile(
    rf"^{WORK_PACKAGE_ID_TOKEN}(?:, {WORK_PACKAGE_ID_TOKEN})*$"
)
SUMMARY_ONLY_PATTERN = re.compile(r"^summary-only: (?P<value>yes|no)$", re.MULTILINE)
DELEGATED_SLICES_PATTERN = re.compile(r"^delegated slices: (?P<value>none|listed)$", re.MULTILINE)
SLICE_ID_PATTERN = re.compile(r"^slice id: (?P<value>.+)$", re.MULTILINE)
SLICE_TYPE_PATTERN = re.compile(r"^slice type: (?P<value>edit|review-only)$", re.MULTILINE)
OWNED_SURFACES_PATTERN = re.compile(r"^owned surfaces: (?P<value>.+)$", re.MULTILINE)
TOUCHED_SURFACES_PATTERN = re.compile(r"^touched surfaces: (?P<value>.+)$", re.MULTILINE)
APPROVED_PLAN_PATTERN = re.compile(r"^- approved plan: `(?P<value>[^`]+)`$", re.MULTILINE)
SUMMARY_EXCEPTION_ENTRY_PATTERN = re.compile(
    r"^### (?P<title>[^\n]+)$\n(?P<body>.*?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)
SUMMARY_EXCEPTION_SURFACE_PATTERN = re.compile(r"^- surface: `(?P<value>[^`]+)`$", re.MULTILINE)
LATEST_OWNING_PHASE_REVIEW_PATTERN = re.compile(
    r"^- latest owning phase review: `(?P<value>[^`]+)`$",
    re.MULTILINE,
)
AUTHORITATIVE_EXCEPTION_HOME_PATTERN = re.compile(
    r"^- authoritative exception home: `(?P<value>[^`]+)`$",
    re.MULTILINE,
)
WORK_PACKAGE_ID_PATTERN = re.compile(rf"\b{WORK_PACKAGE_ID_TOKEN}\b")
CURRENT_DOC_PATH_PATTERN = re.compile(r"\bdocs-internal/current/v1/[A-Za-z0-9._/-]+\.md\b")
BACKTICKED_VALUE_PATTERN = re.compile(r"`(?P<value>[^`]+)`")
REPO_PATH_PATTERN = re.compile(
    r"\b(?:AGENTS\.md|STYLE\.md|README\.md|pyproject\.toml|Makefile|"
    r"docs/[A-Za-z0-9_./*-]+|apps/[A-Za-z0-9_./*-]+|"
    r"scripts/[A-Za-z0-9_./*-]+|definitions/[A-Za-z0-9_./*-]+|"
    r"docs-internal/[A-Za-z0-9_./*-]+)\b"
)

PHASE_SCOPED_REVIEW_EXCLUDED_PATHS = {
    EXECUTION_ROOT / "reviews" / "README.md",
    EXECUTION_ROOT / "reviews" / "phase-0-3-closeout.md",
    EXECUTION_ROOT / "reviews" / "phase-0-3-closeout-review-exceptions.md",
    EXECUTION_ROOT / "reviews" / "phase-review-template.md",
}

PHASE_SCOPED_REVIEW_REQUIRED_HEADINGS = [
    "## Slice identity",
    "## Phase-local contract",
    "## Scope",
    "## Verdict",
    "## Findings",
    "## Delegated-slice compliance",
    "## Proof lanes relied on",
    "## Stale-logic search proof",
    "## Kill-list proof",
    "## Docs answer-sourcing proof",
    "## Phase-bounded STYLE exceptions",
]

PHASE_SCOPED_PLAN_EXCLUDED_PATHS = {
    EXECUTION_ROOT / "plans" / "README.md",
    EXECUTION_ROOT / "plans" / "phase-plan-template.md",
    EXECUTION_ROOT / "plans" / "phase-0-3-closeout.md",
}

PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS = {
    EXECUTION_ROOT / "evidence" / "README.md",
    EXECUTION_ROOT / "evidence" / "phase-evidence-template.md",
    EXECUTION_ROOT / "evidence" / "phase-0-3-closeout.md",
}


def phase0_allowed_current_doc_paths(
    phase0_current_doc_required_markers: dict,
) -> set[str]:
    allowed_paths = {
        path.relative_to(ROOT).as_posix() for path in phase0_current_doc_required_markers
    }
    allowed_paths |= {
        "docs-internal/current/v1/architecture/current-architecture.md",
        "docs-internal/current/v1/architecture/openclaw-dispatch-and-session-contract.md",
        "docs-internal/current/v1/architecture/watchdog-and-runtime-monitoring.md",
    }
    return allowed_paths
