# Phase 3 Controller-Truth and Failure Contract Repair Review

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
  cleanup, and authoritative closeout review
- date: 2026-05-12

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- reviewed evidence: `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- reviewed current docs:
  - `../../current/architecture/runtime-read-models-and-operator-surfaces.md`
  - `../../current/interfaces/api-surface-and-route-map.md`
  - `../../current/interfaces/api-trust-lanes.md`
  - `../../current/operations/run-docker-postgres-verification.md`

## Verdict

- pass/fail: pass
- summary: the authoritative Phase 3 chain now matches the final merged
  runtime/docs/test wave, the Phase 3 proof lanes are green, and the
  structural-tool rollback path is described without overclaiming the
  best-effort manifest restoration step.

## Findings

- the old authoritative Phase 3 triplet was stale against the live tree and
  the refresh now fixes the owned doc surfaces:
  - removed flat `test_phase3_runtime_*.py` and `test_runtime_schema_contract.py`
    references from the authoritative chain
  - removed deleted runtime file refs such as `runtime/post_commit.py` and
    `runtime/control/surfaces.py`
  - rewired the current Phase 3 docs to the live `runtime/control/flow/**`,
    `runtime/control/dispatch/callbacks.py`, `runtime/control/observability.py`,
    `runtime/effects/worker.py`, `phase3/routes/**`, and
    `runtime_schema_contract/**` layout
- the owned Phase 3 docs and closeout chain no longer appear in the remaining
  `docs_freeze` findings
- the remaining raw structural-replan `ValueError` producers were replaced with
  typed runtime failures, so the live mapper now relies on typed runtime
  failures plus only the narrow file-missing / internal-error fallbacks
- structural callback manifest success is now rollback-safe: structural tools
  rewrite the stable manifest before the final commit, and commit failure now
  makes a best-effort attempt to restore the prior stable manifest instead of
  returning failure after a committed graph change
- the runtime `control` barrel no longer forces the Phase 2/3 proof lanes
  through an import cycle, and the live Phase 3 paths no longer resolve
  `load_task_root_paths` through the heavier `projection` barrel
- the current live Phase 3 proof lanes are now green:
  - `ruff` passes on the touched Phase 3 runtime/test scope
  - `mypy` passes on the touched Phase 3 runtime/test scope
  - `pyright` passes
  - `docs_freeze` passes

## Gate coverage

- the selected phase and current phase page remain correct for this chain
- the authoritative plan, evidence, and review each keep `summary-only: no`
- the closeout chain now points at the current split Phase 3 proof tree rather
  than deleted flat tests
- the run-Docker/Postgres current doc stayed unchanged because its lane wording
  was already truthful
- the obsolete `phase-3-runtime-contract-and-control-repair*` history no longer
  remains as redundant routing noise

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate` -> passed
- `./.venv/bin/ruff check apps/api/tests/integration/phase3/db/actions.py` -> passed
- `./.venv/bin/ruff check apps/api/app/api/errors.py apps/api/app/runtime/control apps/api/app/runtime/effects/validation.py apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py` -> passed
- `./.venv/bin/mypy apps/api/app/api/errors.py apps/api/app/runtime/control apps/api/app/runtime/effects/validation.py apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract` -> passed
- `make pyright-api` -> passed
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py apps/api/tests/integration/phase3/contracts/test_assignment_cases.py apps/api/tests/integration/phase3/contracts/test_error_cases.py apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py` -> targeted contract proof passed in the final merged wave
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/contracts/test_replan_cases.py apps/api/tests/integration/phase3/contracts/test_replan_descendant_cases.py apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py` -> structural callback timing and full structural-CRUD manifest reread proof passed in the final merged wave
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py` -> current green proof rerun recorded in the parent integration loop

## Delegated-slice compliance

- this slice stayed inside the approved Phase 3 current-doc and closeout
  artifact surfaces
- no runtime code, `scripts/docs/**`, or non-Phase-3 current docs were edited
- the authoritative chain no longer attributes live ownership to deleted flat
  runtime files or flat Phase 3 test collectors

## Stale-logic search proof

- checked the authoritative Phase 3 chain for stale references to:
  - deleted flat Phase 3 test files
  - deleted `runtime/post_commit.py`
  - deleted `runtime/control/surfaces.py`
  - the obsolete `phase-3-runtime-contract-and-control-repair*` family
- outcome:
  - those stale references are removed from the authoritative plan/evidence/review
  - the split Phase 3 layout is now the only live routing surface in the
    authoritative chain

## Kill-list proof

- checked the current authoritative Phase 3 chain for wording that would:
  - claim deleted flat files are still the current Phase 3 proof surface
  - claim this docs slice cleared the known `ruff` blocker
  - overstate whole-program final acceptance from this phase-scoped review
- outcome:
  - no such stale or overreaching wording remains in the current chain

## Docs answer-sourcing proof

- execution canon relied on:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/overview.md`
  - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
- redesign/current truth relied on:
  - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs/redesign/architecture/checkpoint-contract.md`
  - `docs/redesign/architecture/runtime-database-and-object-contract.md`
  - `docs/redesign/workflows/parent-root-release-and-closure.md`
  - `docs/redesign/workflows/runtime-structural-replan.md`
  - `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
  - `docs/current/interfaces/api-surface-and-route-map.md`
  - `docs/current/interfaces/api-trust-lanes.md`
  - `docs/current/operations/run-docker-postgres-verification.md`
- code/tests inspected for current truth:
  - `apps/api/app/runtime/control/flow/listing.py`
  - `apps/api/app/runtime/control/flow/service.py`
  - `apps/api/app/runtime/control/dispatch/callbacks.py`
  - `apps/api/app/runtime/control/observability.py`
  - `apps/api/app/runtime/effects/worker.py`
  - `apps/api/app/api/router.py`
  - `apps/api/app/api/routes/runtime.py`
  - `apps/api/app/api/routes/operator.py`
  - `apps/api/app/api/routes/callback.py`
  - `apps/api/app/api/routes/observability.py`
  - `apps/api/tests/integration/phase3/routes/test_query_contract.py`
  - `apps/api/tests/integration/phase3/routes/test_surface_contract.py`
  - `apps/api/tests/integration/phase3/contracts/test_callback_cases.py`
  - `apps/api/tests/integration/runtime_schema_contract/test_database.py`
  - `apps/api/tests/integration/runtime_schema_contract/test_guard.py`
  - `apps/api/tests/integration/runtime_schema_contract/test_model.py`
  - `apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py`

## Phase-bounded STYLE exceptions

- none

## Remaining exact blockers

- none

## Cross-links

- authoritative plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- authoritative evidence: `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
