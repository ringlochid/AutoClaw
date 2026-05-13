# Phase 3 Controller-Truth and Failure Contract Repair

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
owned surfaces: `apps/api/app/api/errors.py`, `apps/api/app/api/runtime_exception_mapping.py`, `apps/api/app/api/routes/*.py`, `apps/api/app/db/session.py`, `apps/api/app/runtime/control/failures.py`, `apps/api/app/runtime/control/boundary/service.py`, `apps/api/app/runtime/control/boundary/transitions.py`, `apps/api/app/runtime/control/checkpoint/recording.py`, `apps/api/app/runtime/control/dispatch/callbacks.py`, `apps/api/app/runtime/control/dispatch/control.py`, `apps/api/app/runtime/control/flow/listing.py`, `apps/api/app/runtime/control/flow/queries.py`, `apps/api/app/runtime/control/flow/resume.py`, `apps/api/app/runtime/control/flow/service.py`, `apps/api/app/runtime/control/parent_tools.py`, `apps/api/app/runtime/control/release/basis.py`, `apps/api/app/runtime/control/release/guards.py`, `apps/api/app/runtime/replan/**`, `apps/api/tests/integration/phase3/contracts/**`, `apps/api/tests/integration/phase3/routes/**`, `apps/api/tests/integration/phase3/db/**`, `apps/api/tests/integration/runtime_schema_contract/**`, and `apps/api/tests/e2e/phase3/normal_lane/**`
touched surfaces: apps/api/app/api/errors.py, apps/api/app/api/runtime_exception_mapping.py, apps/api/app/api/routes/callback.py, apps/api/app/api/routes/observability.py, apps/api/app/api/routes/operator.py, apps/api/app/api/routes/runtime.py, apps/api/app/db/session.py, apps/api/app/runtime/control/assignment/service.py, apps/api/app/runtime/control/assignment/supersession.py, apps/api/app/runtime/control/boundary/service.py, apps/api/app/runtime/control/boundary/transitions.py, apps/api/app/runtime/control/budgets.py, apps/api/app/runtime/control/checkpoint/artifacts.py, apps/api/app/runtime/control/checkpoint/recording.py, apps/api/app/runtime/control/dispatch/callbacks.py, apps/api/app/runtime/control/dispatch/control.py, apps/api/app/runtime/control/failures.py, apps/api/app/runtime/control/flow/listing.py, apps/api/app/runtime/control/flow/queries.py, apps/api/app/runtime/control/flow/resume.py, apps/api/app/runtime/control/flow/service.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/control/release/basis.py, apps/api/app/runtime/control/release/guards.py, apps/api/app/runtime/replan/adopt.py, apps/api/app/runtime/replan/defaults.py, apps/api/app/runtime/replan/edges.py, apps/api/app/runtime/replan/lineage.py, apps/api/app/runtime/replan/lookup.py, apps/api/app/runtime/replan/revision_state.py, apps/api/app/runtime/replan/service.py, apps/api/tests/e2e/phase3/normal_lane/flow.py, apps/api/tests/integration/phase3/contracts/test_callback_cases.py, apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py, apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py, apps/api/tests/integration/phase3/contracts/test_replan_cases.py, apps/api/tests/integration/phase3/contracts/test_replan_descendant_cases.py, apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py, apps/api/tests/integration/phase3/db/actions.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py
slice id: phase3-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/interfaces/api-surface-and-route-map.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
touched surfaces: docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/interfaces/api-surface-and-route-map.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md

## Slice identity

- selected phase: Phase 3
- work package or slice: merged Phase 3 controller-truth validation,
  failure-contract repair, boundary-legality cleanup, and authoritative closeout
  refresh
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
- describe the full merged Phase 3 wave: controller-truth validation, typed
  runtime failures, rollback-safe structural callback manifest timing,
  boundary-legality repair, runtime import-cycle cleanup for the scoped Phase
  2/3 proof lanes, split test-support cleanup, and current-doc / proof refresh
- point all Phase 3 proof routing at the current `phase3/**`,
  `runtime_schema_contract/**`, `phase3/normal_lane/**`, and stronger DB lanes
- keep the current Phase 3 closeout chain aligned to the final merged runtime,
  docs, and proof state

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
- `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
- `docs/current/interfaces/api-surface-and-route-map.md`
- `docs/current/interfaces/api-trust-lanes.md`
- `docs/current/operations/run-docker-postgres-verification.md`
- the current Phase 3 plan/evidence/review chain
- the live Phase 3 route and readback code under
  `apps/api/app/api/routes/{runtime,operator,callback,observability}.py`,
  `apps/api/app/runtime/control/flow/**`,
  `apps/api/app/runtime/control/dispatch/callbacks.py`,
  `apps/api/app/runtime/control/observability.py`, and
  `apps/api/app/runtime/effects/worker.py`

## Live package and proof layout

- runtime control and runtime-read proof now lands under:
  - `apps/api/app/runtime/control/**`
  - `apps/api/app/runtime/effects/**`
  - `apps/api/app/api/routes/**`
- split Phase 3 proof now lives under:
  - `apps/api/tests/integration/phase3/contracts/**`
  - `apps/api/tests/integration/phase3/control/**`
  - `apps/api/tests/integration/phase3/db/**`
  - `apps/api/tests/integration/phase3/routes/**`
  - `apps/api/tests/integration/runtime_schema_contract/**`
  - `apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`
- the stronger DB verification lane remains:
  - `make test-api-db`
- the current Docker/Postgres instructions remain truthful in:
  - `docs/current/operations/run-docker-postgres-verification.md`

## Validation checkpoints

- current-doc readback against the live split runtime and test tree
- Phase 3 route, read-model, runtime-schema, and normal-lane proof against the
  live `phase3/**` layout
- explicit check for the previously reported `ruff` import-order blocker
- repo-wide `docs_freeze` rerun to confirm any remaining failures are outside
  this slice

## Required validation for this chain

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate`
- `./.venv/bin/ruff check apps/api/tests/integration/phase3/db/actions.py`
- `./.venv/bin/ruff check apps/api/app/api/errors.py apps/api/app/runtime/control apps/api/app/runtime/effects/validation.py apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`
- `./.venv/bin/mypy apps/api/app/api/errors.py apps/api/app/runtime/control apps/api/app/runtime/effects/validation.py apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract`
- `make pyright-api`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/routes apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`

## Exit evidence

- evidence artifact:
  `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- review artifact:
  `../reviews/phase-3-closeout-runtime-lineage-and-budget.md`

## Stop conditions

- stop if truthful wording requires reopening production code outside the
  Phase 3 owned and allowed collateral surfaces
- stop if repairing the remaining `ruff` or `docs_freeze` blockers requires
  runtime code, `scripts/docs/**`, or non-Phase-3 current-doc edits
