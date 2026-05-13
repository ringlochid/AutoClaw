# Phase 3 Controller-Truth and Failure Contract Repair Evidence

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2, P3-WP3
summary-only: no
delegated slices: listed
slice id: phase3-controller-truth-validation
slice type: edit
owned surfaces: apps/api/app/runtime/control/__init__.py, apps/api/app/runtime/control/assignment/staging.py, apps/api/app/runtime/control/release/preconditions.py, apps/api/app/runtime/control/boundary/relations.py, apps/api/app/runtime/control/boundary/release_descendant_refs.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/effects/validation.py, apps/api/tests/integration/phase3/contracts/**, apps/api/tests/integration/runtime_schema_contract/**, and apps/api/tests/e2e/phase3/normal_lane/**
touched surfaces: apps/api/app/runtime/control/__init__.py, apps/api/app/runtime/control/assignment/staging.py, apps/api/app/runtime/control/boundary/relations.py, apps/api/app/runtime/control/boundary/release_descendant_refs.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/release/preconditions.py, apps/api/app/runtime/effects/validation.py, apps/api/tests/integration/phase3/contracts/test_assignment_cases.py, apps/api/tests/integration/phase3/contracts/test_error_cases.py, apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py, apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py, apps/api/tests/integration/phase3/contracts/pending_materialization_support.py
slice id: phase3-failure-contract-and-boundary
slice type: edit
owned surfaces: apps/api/app/api/errors.py, apps/api/app/api/runtime_exception_mapping.py, apps/api/app/api/routes/*.py, apps/api/app/db/session.py, apps/api/app/runtime/control/failures.py, apps/api/app/runtime/control/boundary/service.py, apps/api/app/runtime/control/boundary/transitions.py, apps/api/app/runtime/control/checkpoint/recording.py, apps/api/app/runtime/control/dispatch/callbacks.py, apps/api/app/runtime/control/dispatch/control.py, apps/api/app/runtime/control/flow/listing.py, apps/api/app/runtime/control/flow/queries.py, apps/api/app/runtime/control/flow/resume.py, apps/api/app/runtime/control/flow/service.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/control/release/basis.py, apps/api/app/runtime/control/release/guards.py, apps/api/app/runtime/replan/**, apps/api/tests/integration/phase3/contracts/**, apps/api/tests/integration/phase3/routes/**, apps/api/tests/integration/phase3/db/**, apps/api/tests/integration/runtime_schema_contract/**, and apps/api/tests/e2e/phase3/normal_lane/**
touched surfaces: apps/api/app/api/errors.py, apps/api/app/api/runtime_exception_mapping.py, apps/api/app/api/routes/callback.py, apps/api/app/api/routes/observability.py, apps/api/app/api/routes/operator.py, apps/api/app/api/routes/runtime.py, apps/api/app/db/session.py, apps/api/app/runtime/control/assignment/service.py, apps/api/app/runtime/control/assignment/supersession.py, apps/api/app/runtime/control/boundary/service.py, apps/api/app/runtime/control/boundary/transitions.py, apps/api/app/runtime/control/budgets.py, apps/api/app/runtime/control/checkpoint/artifacts.py, apps/api/app/runtime/control/checkpoint/recording.py, apps/api/app/runtime/control/dispatch/callbacks.py, apps/api/app/runtime/control/dispatch/control.py, apps/api/app/runtime/control/failures.py, apps/api/app/runtime/control/flow/listing.py, apps/api/app/runtime/control/flow/queries.py, apps/api/app/runtime/control/flow/resume.py, apps/api/app/runtime/control/flow/service.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/control/release/basis.py, apps/api/app/runtime/control/release/guards.py, apps/api/app/runtime/replan/adopt.py, apps/api/app/runtime/replan/defaults.py, apps/api/app/runtime/replan/edges.py, apps/api/app/runtime/replan/lineage.py, apps/api/app/runtime/replan/lookup.py, apps/api/app/runtime/replan/revision_state.py, apps/api/app/runtime/replan/service.py, apps/api/tests/e2e/phase3/normal_lane/flow.py, apps/api/tests/integration/phase3/contracts/test_callback_cases.py, apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py, apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py, apps/api/tests/integration/phase3/contracts/test_replan_cases.py, apps/api/tests/integration/phase3/contracts/test_replan_descendant_cases.py, apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py, apps/api/tests/integration/phase3/db/actions.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py
slice id: phase3-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/interfaces/api-surface-and-route-map.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
touched surfaces: docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/interfaces/api-surface-and-route-map.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md

## Slice identity

- selected phase: Phase 3
- work package or slice: merged Phase 3 controller-truth validation,
  failure-contract repair, boundary-legality cleanup, split test-support
  cleanup, and authoritative proof refresh
- slice type: edit
- date: 2026-05-12

## Plan and review links

- approved plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- mandatory review:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact: `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Current doc and record refresh executed

- rewrote the owned Phase 3 current docs to point at the live split runtime
  surfaces:
  - `apps/api/app/runtime/control/flow/**`
  - `apps/api/app/runtime/control/dispatch/callbacks.py`
  - `apps/api/app/runtime/control/observability.py`
  - `apps/api/app/runtime/effects/worker.py`
  - `apps/api/app/api/routes/callback.py`
  - `apps/api/tests/integration/phase3/routes/**`
  - `apps/api/tests/integration/phase3/contracts/test_callback_cases.py`
  - `apps/api/tests/integration/runtime_schema_contract/**`
- completed the typed runtime-failure migration inside the Phase 3-owned
  runtime-read and callback compatibility shell by replacing the remaining
  summary-driven `ValueError` producers on the callback, runtime-read, and
  structural-replan paths with typed runtime failures
- moved structural callback manifest success to a rollback-safe pre-commit
  rewrite path so structural tool failure can no longer follow a committed
  graph revision
- removed the eager runtime `control` barrel cycle and cut the remaining
  `load_task_root_paths` projection-barrel imports on live Phase 3 paths so the
  scoped Phase 2 and Phase 3 proof lanes collect cleanly again
- replaced stale closeout references to deleted flat files and retired monolith
  test paths:
  - removed `runtime/post_commit.py`
  - removed `runtime/control/surfaces.py`
  - removed flat `test_phase3_runtime_*.py` references from the authoritative
    triplet
- rewrote the authoritative Phase 3 triplet to the live split proof layout:
  - `apps/api/tests/integration/phase3/contracts/**`
  - `apps/api/tests/integration/phase3/control/**`
  - `apps/api/tests/integration/phase3/db/**`
  - `apps/api/tests/integration/phase3/routes/**`
  - `apps/api/tests/integration/runtime_schema_contract/**`
  - `apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`
- deleted the obsolete summary-only
  `phase-3-runtime-contract-and-control-repair*` family because it no longer
  added routing value beyond the current closeout triplet
- reviewed `docs/current/operations/run-docker-postgres-verification.md` and
  left it unchanged because its current-lane wording still matched the live
  stronger DB proof path

## Executed validation

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
  - outcome: passed
- `./.venv/bin/ruff check apps/api/tests/integration/phase3/db/actions.py`
  - outcome: passed
- `./.venv/bin/ruff check apps/api/app/api/errors.py apps/api/app/runtime/control apps/api/app/runtime/effects/validation.py apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`
  - outcome: passed
- `./.venv/bin/mypy apps/api/app/api/errors.py apps/api/app/runtime/control apps/api/app/runtime/effects/validation.py apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract`
  - outcome: passed
- `make pyright-api`
  - outcome: passed
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py apps/api/tests/integration/phase3/contracts/test_assignment_cases.py apps/api/tests/integration/phase3/contracts/test_error_cases.py apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py`
  - outcome: `30 passed in 122.18s (0:02:02)`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/contracts/test_replan_cases.py apps/api/tests/integration/phase3/contracts/test_replan_descendant_cases.py apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py`
  - outcome: `9 passed in 77.17s (0:01:17)`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/routes apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`
  - outcome: `34 passed in 183.04s (0:03:03)`

## Artifacts changed

- `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
- `docs/current/interfaces/api-surface-and-route-map.md`
- `docs/current/interfaces/api-trust-lanes.md`
- `docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- `docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
- `apps/api/app/api/errors.py`
- `apps/api/app/api/runtime_exception_mapping.py`
- `apps/api/app/api/routes/observability.py`
- `apps/api/app/api/routes/operator.py`
- `apps/api/app/api/routes/runtime.py`
- `apps/api/app/db/session.py`
- `apps/api/app/runtime/control/assignment/staging.py`
- `apps/api/app/runtime/control/assignment/service.py`
- `apps/api/app/runtime/control/__init__.py`
- `apps/api/app/runtime/control/assignment/supersession.py`
- `apps/api/app/runtime/control/boundary/relations.py`
- `apps/api/app/runtime/control/boundary/release_descendant_refs.py`
- `apps/api/app/runtime/control/boundary/service.py`
- `apps/api/app/runtime/control/boundary/transitions.py`
- `apps/api/app/runtime/control/budgets.py`
- `apps/api/app/runtime/control/checkpoint/artifacts.py`
- `apps/api/app/runtime/control/checkpoint/recording.py`
- `apps/api/app/runtime/control/dispatch/callbacks.py`
- `apps/api/app/runtime/control/dispatch/control.py`
- `apps/api/app/runtime/control/failures.py`
- `apps/api/app/runtime/control/flow/listing.py`
- `apps/api/app/runtime/control/flow/queries.py`
- `apps/api/app/runtime/control/flow/resume.py`
- `apps/api/app/runtime/control/flow/service.py`
- `apps/api/app/runtime/control/observability.py`
- `apps/api/app/runtime/control/parent_tools.py`
- `apps/api/app/runtime/control/release/basis.py`
- `apps/api/app/runtime/control/release/guards.py`
- `apps/api/app/runtime/replan/adopt.py`
- `apps/api/app/runtime/replan/defaults.py`
- `apps/api/app/runtime/replan/edges.py`
- `apps/api/app/runtime/replan/lineage.py`
- `apps/api/app/runtime/replan/lookup.py`
- `apps/api/app/runtime/replan/revision_state.py`
- `apps/api/app/runtime/replan/service.py`
- `apps/api/app/runtime/control/release/preconditions.py`
- `apps/api/app/runtime/effects/validation.py`
- `apps/api/app/api/routes/callback.py`
- `apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_callback_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_error_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_replan_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_replan_descendant_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py`
- `apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py`
- `apps/api/tests/integration/phase3/contracts/pending_materialization_support.py`
- `apps/api/tests/integration/phase3/db/actions.py`
- `apps/api/tests/e2e/phase3/normal_lane/flow.py`
- deleted the obsolete Phase 3 runtime-contract-and-control repair triplet

## Residual blockers

- none
