# Phase 3 Closeout Runtime Lineage and Budget Evidence

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
- work package or slice: authoritative Phase 3 closeout cleanup evidence
  refresh for `P3-WP1` through `P3-WP3`
- slice type: edit
- date: 2026-05-07

## Plan and review links

- approved plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- mandatory review:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact: `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- historical support evidence:
  `../evidence/phase-3-runtime-contract-and-control-repair.md`

## Cleanup refresh executed

- removed the dead duplicate current-node resume branch from
  `apps/api/app/runtime/control/flows.py`
- rewrote the authoritative Phase 3 triplet so the delegated-slice header,
  current-doc usage, reset-proof status, and normal-e2e status are all
  truthful on the shared worktree
- extracted the `assign_child` staging path into a dedicated control module and
  repaired the remaining child durable-basis taxonomy gap so release-time and
  assign-time missing-publication failures no longer collapse into the same
  generic missing-resource path
- rewrote the historical `phase-3-runtime-contract-and-control-repair*` chain
  as summary-only support with explicit authoritative replacement links
- rechecked the shared worktree to see whether a Phase 3 normal e2e lane
  landed before this cleanup slice closed
- attached the landed Phase 3 normal e2e proof from the shared worktree

## Commands run in this cleanup refresh

- `./.venv/bin/ruff check apps/api/app/runtime/control/flows.py`
  - result: `All checks passed!`
- `./.venv/bin/mypy apps/api/app/runtime/control/flows.py`
  - result: `Success: no issues found in 1 source file`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_control_state.py`
  - result: `5 passed in 45.42s`
- `find apps/api/tests/e2e -maxdepth 2 -type f | sort`
  - result:
    - `apps/api/tests/e2e/.gitkeep`
    - `apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py`
    - `apps/api/tests/e2e/test_phase3_normal_lane.py`
- `sed -n '1,40p' apps/api/tests/e2e/test_phase3_normal_lane.py`
  - result: readback shows the landed e2e file is the Phase 3 normal lane
- `./.venv/bin/ruff format apps/api/tests/e2e/test_phase3_normal_lane.py`
  - result: `1 file reformatted`
- `./.venv/bin/ruff check apps/api/tests/e2e/test_phase3_normal_lane.py`
  - result: `All checks passed!`
- `./.venv/bin/pytest -q apps/api/tests/e2e/test_phase3_normal_lane.py`
  - result: `1 passed in 91.42s`
- `./.venv/bin/ruff format --check apps/api/app/runtime/control/assign_child.py apps/api/app/runtime/control/parent_tools.py apps/api/app/runtime/control/release.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - result: `4 files already formatted`
- `./.venv/bin/ruff check apps/api/app/runtime/control/assign_child.py apps/api/app/runtime/control/parent_tools.py apps/api/app/runtime/control/release.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - result: `All checks passed!`
- `./.venv/bin/mypy apps/api/app/runtime/control/assign_child.py apps/api/app/runtime/control/parent_tools.py apps/api/app/runtime/control/release.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - result: `Success: no issues found in 4 source files`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_contract_fixes.py -k "missing_required_publication or missing_child_current_publication or assign_child"`
  - result: `5 passed, 24 deselected in 38.62s`
- `rg -n "^(selected phase|current phase page|selected work packages|summary-only|delegated slices|slice id|slice type|owned surfaces|touched surfaces):" docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - result: readback confirmed exact execution-record grammar on the
    authoritative triplet and the historical summary triplet
- `rg -n "^summary-only: (yes|no)$|^## Authoritative replacements$" docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md docs/execution/plans/phase-3-runtime-contract-and-control-repair.md docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`
  - result: readback confirmed `summary-only: no` on the authoritative chain,
    `summary-only: yes` on the historical chain, and `## Authoritative replacements`
    sections on the historical files
- `sed -n '1,220p' docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
  - result: readback passed
- `sed -n '1,260p' docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
  - result: readback passed
- `sed -n '1,320p' docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
  - result: readback passed

## Retained integrated proof lanes

- shipped-path SQLite reset proof remains explicitly attached on this
  authoritative chain from the previously recorded command:
  `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_routes.py`
  -> `58 passed`
- Postgres or Docker strong verification remains explicitly attached on this
  authoritative chain from the previously recorded command:
  `make test-api-db` -> `161 passed`

## Explicit blocker status

- the shared worktree now contains a Phase 3 normal e2e lane at
  `apps/api/tests/e2e/test_phase3_normal_lane.py`
- that lane passed on 2026-05-07 and satisfies the Phase 3 normal-e2e proof
  requirement for this closeout chain
- this cleanup refresh introduced no new reset-gate blocker

## Artifacts changed

- `apps/api/app/runtime/control/assign_child.py`
- `apps/api/app/runtime/control/parent_tools.py`
- `apps/api/app/runtime/control/release.py`
- `apps/api/app/runtime/control/flows.py`
- `apps/api/tests/e2e/test_phase3_normal_lane.py`
- `apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/plans/phase-3-runtime-contract-and-control-repair.md`
- `docs/execution/evidence/phase-3-runtime-contract-and-control-repair.md`
- `docs/execution/reviews/phase-3-runtime-contract-and-control-repair.md`

## Residual blockers

- none
