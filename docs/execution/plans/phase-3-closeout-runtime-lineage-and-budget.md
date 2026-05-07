# Phase 3 Closeout Runtime Lineage and Budget

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2, P3-WP3
summary-only: no
delegated slices: listed
slice id: phase3-lineage-hardening
slice type: edit
owned surfaces: apps/api/app/db/models/runtime/dispatch.py, apps/api/app/runtime/projection/state.py, apps/api/tests/integration/test_runtime_schema_contract.py, apps/api/tests/integration/test_phase3_runtime_db.py, docs/redesign/architecture/runtime-database-and-object-contract.md, docs/redesign/workflows/runtime-structural-replan.md
touched surfaces: apps/api/app/db/models/runtime/dispatch.py, apps/api/app/runtime/projection/state.py, apps/api/tests/integration/test_runtime_schema_contract.py, apps/api/tests/integration/test_phase3_runtime_db.py, docs/redesign/architecture/runtime-database-and-object-contract.md, docs/redesign/workflows/runtime-structural-replan.md
slice id: phase3-control-and-budget
slice type: edit
owned surfaces: apps/api/app/runtime/control/flows.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md
touched surfaces: apps/api/app/runtime/control/flows.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md
slice id: phase3-assign-child-taxonomy
slice type: edit
owned surfaces: apps/api/app/runtime/control/assign_child.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/control/release.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py
touched surfaces: apps/api/app/runtime/control/assign_child.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/control/release.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py
slice id: phase3-pause-dispatch-gating
slice type: edit
owned surfaces: apps/api/app/runtime/control/flows.py, apps/api/app/runtime/control/support.py, apps/api/tests/integration/test_phase3_runtime_control_state.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
touched surfaces: apps/api/app/runtime/control/flows.py, apps/api/app/runtime/control/support.py, apps/api/tests/integration/test_phase3_runtime_control_state.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
slice id: phase3-closeout-artifacts
slice type: edit
owned surfaces: docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/plans/phase-3-runtime-contract-and-control-repair.md, docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md, docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md
touched surfaces: docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/plans/phase-3-runtime-contract-and-control-repair.md, docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md, docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md
slice id: phase3-normal-e2e
slice type: edit
owned surfaces: apps/api/tests/e2e/*
touched surfaces: apps/api/tests/e2e/test_phase3_normal_lane.py
slice id: phase3-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 3
- work package or slice: authoritative Phase 3 closeout cleanup for
  `P3-WP1` through `P3-WP3`
- slice type: edit
- owner: Codex
- date: 2026-05-07

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Closeout focus

- keep this triplet as the only `summary-only: no` Phase 3 closeout chain in
  the owned execution-record surfaces
- phase-scoped artifact set:
  - `docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
  - `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
  - `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
- list the real delegated Phase 3 slices instead of leaving the header as
  `delegated slices: none`
- keep the historical `phase-3-runtime-contract-and-control-repair*` chain
  clearly summary-only and non-authoritative
- make reset-lane proof explicit without pretending this cleanup refresh reran
  shipped-path SQLite or Postgres or Docker verification
- record the current normal-e2e proof from the shared worktree exactly and
  attach it on the authoritative chain once it lands
- keep the pause/continue gating cleanup scoped to
  `apps/api/app/runtime/control/flows.py`,
  `apps/api/app/runtime/control/support.py`,
  `apps/api/tests/integration/test_phase3_runtime_control_state.py`,
  `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`,
  `docs/current/architecture/runtime-control-plane.md`, and
  `docs/current/interfaces/api-trust-lanes.md`

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/overview.md`
- `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/gates/reset-gate.md`
- the current authoritative Phase 3 plan, evidence, and review triplet
- the current historical `phase-3-runtime-contract-and-control-repair*`
  triplet
- current cleanup findings in
  `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/current/architecture/runtime-control-plane.md`
- `apps/api/app/runtime/control/flows.py`

## Live proof routing

- `P3-WP1`: runtime DB lineage hardening, callback tuple integrity, and
  structural replan lineage preservation
- `P3-WP2`: checkpoint ordering, parent or review release semantics, and retry
  budget or failure taxonomy repair, including the final split between missing
  required publication and missing backing-file cases on parent-child durable
  dependency reads
- that final taxonomy cleanup may reopen only
  `apps/api/app/runtime/control/assign_child.py`,
  `apps/api/app/runtime/control/parent_tools.py`,
  `apps/api/app/runtime/control/release.py`, and
  `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `P3-WP3`: parent-owned structural replan or adopt wording and current-doc
  lineage contrast needed to explain the landed runtime truth
- reset proof: retain the previously attached authoritative SQLite and
  Postgres or Docker proof lanes on the evidence chain, but mark them as
  retained proof rather than commands rerun by this cleanup slice
- normal e2e proof: inspect the shared worktree at final readback time and
  either record the new Phase 3 normal lane or record the blocker exactly;
  as of 2026-05-07 the tree contains `apps/api/tests/e2e/.gitkeep` and
  `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`, so no Phase 3
  normal lane is yet available to record

## Validation checkpoints

- exact execution-record grammar and delegated-slice blocks on the
  authoritative triplet
- `summary-only: yes` plus truthful `## Authoritative replacements` links on
  the historical triplet
- targeted validation for `apps/api/app/runtime/control/flows.py`
- final shared-worktree inspection for the Phase 3 normal-e2e lane state
- readback sanity on the final Phase 3 plan, evidence, and review triplet

## Required validation for this slice

- `./.venv/bin/ruff check apps/api/app/runtime/control/flows.py`
- `./.venv/bin/mypy apps/api/app/runtime/control/flows.py`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_control_state.py`
- `find apps/api/tests/e2e -maxdepth 2 -type f | sort`
- readback on the updated Phase 3 authoritative and historical execution
  artifacts

## Exit evidence

- evidence artifact:
  `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Stop conditions

- stop if truthful routing requires edits to execution validator or gate docs
- stop if a truthful closeout update would need hotspot runtime code beyond
  `apps/api/app/runtime/control/flows.py`
- stop if the normal-e2e blocker can only be resolved by editing
  `apps/api/tests/e2e/*` or any other surface outside the owned slice
