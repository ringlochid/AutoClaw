# Phase 3 Closeout Runtime Lineage and Budget Evidence

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
- work package or slice: authoritative evidence refresh for the landed runtime
  layout cleanup and durable post-commit effect runner
- slice type: edit
- date: 2026-05-12

## Plan and review links

- approved plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- mandatory review:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact: `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Cleanup refresh executed

- removed stale closeout references to deleted or replaced surfaces:
  - `apps/api/app/runtime/control/support.py`
  - `apps/api/app/runtime/replan/support.py`
  - `apps/api/app/runtime/projection/state.py`
  - old monolithic Phase 3 proof-suite and e2e size exceptions
- recorded the landed grouped Phase 3 runtime tree:
  - runtime DB model families now live under `apps/api/app/db/models/runtime/**`
  - runtime replan helpers now live under `apps/api/app/runtime/replan/**`
  - runtime control helpers are split across `callbacks.py`, `budgets.py`,
    `clock.py`, `flow_queries.py`, `flow_listing.py`, `flow_resume.py`,
    `release_preconditions.py`, `checkpoint_recording.py`,
    `assignment_persistence.py`, `assignment_staging.py`, and related grouped
    modules
- recorded the landed durable `runtime_effects` queue and the after-return
  timing contract:
  - controller rows plus `runtime_effects` rows commit in one transaction
  - `RuntimeAsyncSession.commit()` wakes the in-process runner after commit
  - runtime and callback write routes return after commit instead of awaiting
    file or projection regeneration
  - the app lifespan starts the effect runner
  - operator and observability GET routes no longer recreate or repair missing
    projections inline
- refreshed the owned current-doc pages so they now describe the durable queue,
  the eventual projection/materialization timing, and the no-inline-repair read
  contract
- replaced the old retained proof totals with the current parent-side totals
  from the shared tree and kept only live Phase 3 proof references

## Slice-local proof lanes

- `./.venv/bin/ruff check apps/api/app/db/session.py apps/api/app/main.py apps/api/app/runtime/post_commit.py apps/api/app/runtime/control/surfaces.py apps/api/app/runtime/control/observability.py apps/api/app/runtime/launch/service.py apps/api/app/api/routes/runtime.py apps/api/app/api/routes/callback.py apps/api/app/db/models/runtime/effects.py apps/api/app/db/models/runtime/shared.py apps/api/app/db/models/runtime/__init__.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/phase3_runtime_routes_support.py apps/api/tests/integration/phase3_runtime_routes_observability_support.py apps/api/tests/integration/phase3_runtime_routes_surface_contract.py apps/api/tests/integration/phase3_runtime_support.py apps/api/tests/integration/phase3_runtime_contract_callback_cases.py`
  - outcome: `All checks passed!`
- `./.venv/bin/mypy apps/api/app/db/session.py apps/api/app/main.py apps/api/app/runtime/post_commit.py apps/api/app/runtime/control/surfaces.py apps/api/app/runtime/control/observability.py apps/api/app/runtime/launch/service.py apps/api/app/api/routes/runtime.py apps/api/app/api/routes/callback.py apps/api/app/db/models/runtime/effects.py apps/api/app/db/models/runtime/shared.py apps/api/app/db/models/runtime/__init__.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/phase3_runtime_routes_support.py apps/api/tests/integration/phase3_runtime_routes_observability_support.py apps/api/tests/integration/phase3_runtime_routes_surface_contract.py apps/api/tests/integration/phase3_runtime_support.py apps/api/tests/integration/phase3_runtime_contract_callback_cases.py`
  - outcome: `Success: no issues found in 18 source files`
- `cd apps/api && npx --yes pyright app/db/session.py app/main.py app/runtime/post_commit.py app/runtime/control/surfaces.py app/runtime/control/observability.py app/runtime/launch/service.py app/api/routes/runtime.py app/api/routes/callback.py app/db/models/runtime/effects.py app/db/models/runtime/shared.py tests/integration/test_phase3_runtime_routes.py tests/integration/test_phase3_runtime_contract_fixes.py tests/integration/phase3_runtime_routes_support.py tests/integration/phase3_runtime_routes_observability_support.py tests/integration/phase3_runtime_routes_surface_contract.py tests/integration/phase3_runtime_support.py tests/integration/phase3_runtime_contract_callback_cases.py`
  - outcome: `0 errors, 0 warnings, 0 informations`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py`
  - outcome: `45 passed in 318.64s`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_db.py apps/api/tests/integration/test_runtime_schema_contract.py apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_contract_fixes.py apps/api/tests/integration/test_phase3_runtime_routes.py apps/api/tests/e2e/test_phase3_normal_lane.py`
  - outcome: `86 passed in 896.72s (0:14:56)`
- `cd apps/api && npx --yes pyright tests/integration/phase3_runtime_control_boundary_cases.py tests/integration/phase3_runtime_routes_guidance_contract.py tests/integration/phase3_runtime_routes_observability_support.py`
  - outcome: `0 errors, 0 warnings, 0 informations`
- `./.venv/bin/pytest -q apps/api/tests/integration/test_phase3_runtime_control_state.py apps/api/tests/integration/test_phase3_runtime_routes.py`
  - outcome: `20 passed in 176.77s`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - outcome: `No findings.`

## Retained parent-side proof lanes

- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests`
  - outcome: `238 passed in 947.69s (0:15:47)`
- `make test-api-db`
  - outcome: `236 passed in 751.09s (0:12:31)`
- `./.venv/bin/pytest -q apps/api/tests/e2e/test_phase3_normal_lane.py`
  - outcome: `1 passed in 91.42s`
- `./.venv/bin/pytest -q apps/api/tests/e2e/test_phase2_minimal_runtime_lane.py apps/api/tests/e2e/test_phase3_normal_lane.py`
  - outcome: `2 passed`

## Current timing and readback truth

- write-route responses are derived from committed controller truth
- projection/materialization work is durable and asynchronous:
  `runtime_effects` rows queue `file_copy`,
  `manifest_materialization`,
  `dispatch_materialization`,
  `artifact_current_pointer_materialization`, and
  `attempt_materialization`
- the effect runner drains ready rows in priority order after return
- runtime and callback write routes no longer wait for manifest, dispatch,
  attempt, or pointer files to exist before returning `200`
- operator snapshot, trace, and observability reads surface the current file
  refs but do not repair or recreate missing files inline

## Artifacts changed

- `docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/current/architecture/runtime-control-plane.md`
- `docs/current/interfaces/api-trust-lanes.md`
- `docs/current/architecture/manifest-projection-and-acknowledgement.md`

## Residual blockers

- none inside the owned Phase 3 closeout chain
- parent-owned final worktree reconciliation and non-Phase-3 artifact closure
  remain outside this phase-scoped evidence
