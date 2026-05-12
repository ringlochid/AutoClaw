# Phase 3 Closeout Runtime Lineage and Budget

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2, P3-WP3
summary-only: no
delegated slices: listed
slice id: phase3-runtime-db-and-replan-layout
slice type: edit
owned surfaces: apps/api/app/db/models/runtime/**, apps/api/app/runtime/replan/**, apps/api/app/runtime/contracts.py, apps/api/tests/integration/test_phase3_runtime_db.py, apps/api/tests/integration/test_runtime_schema_contract.py
touched surfaces: apps/api/app/db/models/runtime/**, apps/api/app/runtime/replan/**, apps/api/app/runtime/contracts.py, apps/api/tests/integration/test_phase3_runtime_db.py, apps/api/tests/integration/test_runtime_schema_contract.py
slice id: phase3-control-layout-and-release-cleanup
slice type: edit
owned surfaces: apps/api/app/runtime/control/**, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, apps/api/tests/integration/test_phase3_runtime_control_state.py
touched surfaces: apps/api/app/runtime/control/**, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, apps/api/tests/integration/test_phase3_runtime_control_state.py
slice id: phase3-durable-post-commit-effects
slice type: edit
owned surfaces: apps/api/app/db/session.py, apps/api/app/main.py, apps/api/app/runtime/post_commit.py, apps/api/app/db/models/runtime/effects.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/surfaces.py, apps/api/app/runtime/launch/service.py, apps/api/app/api/routes/runtime.py, apps/api/app/api/routes/callback.py, apps/api/tests/integration/test_phase3_runtime_routes.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py
touched surfaces: apps/api/app/db/session.py, apps/api/app/main.py, apps/api/app/runtime/post_commit.py, apps/api/app/db/models/runtime/effects.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/surfaces.py, apps/api/app/runtime/launch/service.py, apps/api/app/api/routes/runtime.py, apps/api/app/api/routes/callback.py, apps/api/tests/integration/test_phase3_runtime_routes.py, apps/api/tests/integration/test_phase3_runtime_contract_fixes.py
slice id: phase3-proof-suite-split
slice type: edit
owned surfaces: apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, apps/api/tests/integration/test_phase3_runtime_control_state.py, apps/api/tests/integration/test_phase3_runtime_db.py, apps/api/tests/integration/test_phase3_runtime_routes.py, apps/api/tests/integration/test_runtime_schema_contract.py, apps/api/tests/e2e/test_phase3_normal_lane.py
touched surfaces: apps/api/tests/integration/test_phase3_runtime_contract_fixes.py, apps/api/tests/integration/test_phase3_runtime_control_state.py, apps/api/tests/integration/test_phase3_runtime_db.py, apps/api/tests/integration/test_phase3_runtime_routes.py, apps/api/tests/integration/test_runtime_schema_contract.py, apps/api/tests/e2e/test_phase3_normal_lane.py
slice id: phase3-closeout-current-doc-refresh
slice type: edit
owned surfaces: docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md, docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/manifest-projection-and-acknowledgement.md
touched surfaces: docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md, docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/manifest-projection-and-acknowledgement.md
slice id: phase3-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 3
- work package or slice: authoritative Phase 3 closeout chain for the landed
  runtime layout cleanup, durable post-commit effect runner, and proof refresh
- slice type: edit
- owner: Codex
- date: 2026-05-12

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Closeout focus

- keep this triplet as the only `summary-only: no` Phase 3 closeout chain
- describe the current tree, not the pre-split runtime tree:
  - no `app.runtime.control.support`
  - no `runtime/replan/support.py`
  - no old `projection/state.py` monolith
  - no old file-size exception inventory for removed or split files
- record the landed durable `runtime_effects` queue, the app-lifespan runner,
  and the after-return write-route timing contract
- keep current docs truthful about eventual projection/materialization timing:
  controller rows plus durable effect rows commit before return; generated
  files follow asynchronously
- retain parent-side proof lanes only at their current known totals
- keep Phase 3-local blocker language exact and avoid claiming whole-program
  clean-worktree closure from this triplet

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/overview.md`
- `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`
- `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
- `docs/redesign/architecture/checkpoint-contract.md`
- `docs/redesign/architecture/runtime-database-and-object-contract.md`
- `docs/redesign/workflows/parent-root-release-and-closure.md`
- `docs/redesign/workflows/runtime-structural-replan.md`
- `docs/current/architecture/runtime-control-plane.md`
- `docs/current/interfaces/api-trust-lanes.md`
- `docs/current/architecture/manifest-projection-and-acknowledgement.md`
- the current Phase 3 plan/evidence/review chain
- the landed effect-runner code under `apps/api/app/runtime/post_commit.py`,
  `apps/api/app/db/session.py`, `apps/api/app/db/models/runtime/effects.py`,
  `apps/api/app/runtime/control/observability.py`, and
  `apps/api/app/runtime/launch/service.py`

## Live proof routing

- `P3-WP1`: runtime/control cleanup, release-precondition cleanup, grouped
  runtime model packaging, and removal of dead helpers and dead compatibility
  wrappers
- `P3-WP2`: durable post-commit effect queue, session commit staging,
  app-lifespan runner startup, and read-route no-inline-repair behavior
- `P3-WP3`: split Phase 3 proof suites and normal-e2e lane, then refresh the
  current-doc and authoritative closeout chain

## Validation checkpoints

- targeted static proof on Phase 3 runtime/control and effect-runner surfaces
- targeted Phase 3 route/control/contract proof after the effect-runner change
- retained parent-side full local suite, Docker/Postgres lane, and repo-wide
  structural audit totals
- current-doc readback after the timing contract and grouped-layout wording is
  refreshed
- final triplet readback to confirm old counts, removed files, and stale
  blocker claims are gone

## Required validation for this chain

- `./.venv/bin/ruff check apps/api/app/runtime/control apps/api/app/runtime/post_commit.py apps/api/app/db/session.py apps/api/app/db/models/runtime/effects.py`
- `./.venv/bin/mypy apps/api/app/runtime/control apps/api/app/runtime/post_commit.py apps/api/app/db/session.py apps/api/app/db/models/runtime/effects.py`
- `cd apps/api && npx --yes pyright app/runtime/control app/runtime/post_commit.py app/db/session.py app/db/models/runtime/effects.py`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/e2e/test_phase3_normal_lane.py`
- retained parent-side proof:
  - `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests`
  - `make test-api-db`
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`

## Exit evidence

- evidence artifact:
  `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Stop conditions

- stop if truthful wording requires reopening production code outside the
  Phase 3 owned and allowed collateral surfaces
- stop if the current-doc timing refresh would require inventing a contract not
  already supported by the landed effect-runner code or tests
- stop if global worktree reconciliation or non-Phase-3 artifact cleanup would
  need to be claimed from this phase-scoped chain
