# Phase 3 Local-Tool-First Runtime, Closure, And Replan Review

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2, P3-WP3
summary-only: no
delegated slices: listed
slice id: phase3-current-surface-and-launch-readability
slice type: edit
owned surfaces: apps/api/app/runtime/control/assignment/**, apps/api/app/runtime/control/boundary/**, apps/api/app/runtime/control/release/**, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/effects/validation.py, apps/api/app/runtime/launch/**, apps/api/app/runtime/task_root/**, apps/api/tests/integration/phase3/contracts/**, apps/api/tests/integration/phase3/db/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/phase3/normal_lane/**
touched surfaces: apps/api/app/runtime/control/assignment/staging.py, apps/api/app/runtime/control/boundary/release_descendant_refs.py, apps/api/app/runtime/control/boundary/transitions.py, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/control/release/basis.py, apps/api/app/runtime/control/release/preconditions.py, apps/api/app/runtime/effects/validation.py, apps/api/app/runtime/launch/service.py, apps/api/app/runtime/launch/persistence/runtime.py, apps/api/app/runtime/task_root/reads.py, apps/api/tests/integration/phase3/contracts/test_assignment_pending_materialization_cases.py, apps/api/tests/integration/phase3/contracts/test_release_pending_projection_cases.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py, apps/api/tests/integration/phase3/db/test_checkpoint_cases.py, apps/api/tests/integration/phase3/db/test_release_root_cases.py, apps/api/tests/e2e/phase3/normal_lane/flow.py
slice id: phase3-handoff-and-failure-family
slice type: edit
owned surfaces: apps/api/app/api/runtime_exception_mapping.py, apps/api/app/runtime/control/dispatch/opening.py, apps/api/app/runtime/projection/manifest/**, apps/api/app/runtime/projection/attempt_materialization.py, apps/api/app/runtime/projection/dispatch/materialization.py, apps/api/app/runtime/launch/bootstrap/projection.py, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/integration/phase3/contracts/**
touched surfaces: apps/api/app/api/runtime_exception_mapping.py, apps/api/app/runtime/control/dispatch/opening.py, apps/api/app/runtime/projection/manifest/checkpoint_handoff.py, apps/api/app/runtime/projection/manifest/context.py, apps/api/app/runtime/projection/manifest/current_context_queries.py, apps/api/app/runtime/projection/attempt_materialization.py, apps/api/app/runtime/projection/dispatch/materialization.py, apps/api/app/runtime/launch/bootstrap/projection.py, apps/api/tests/integration/phase2/bootstrap/test_manifest.py, apps/api/tests/integration/phase2/bootstrap/test_manifest_checkpoint_handoff.py, apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py, apps/api/tests/integration/phase3/contracts/test_failure_mapping_cases.py, apps/api/tests/integration/phase3/contracts/test_parent_checkpoint_handoff_cases.py
slice id: phase3-structural-manifest-and-thin-route
slice type: edit
owned surfaces: apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/effects/cases.py, apps/api/app/runtime/effects/worker.py, apps/api/app/runtime/projection/**init**.py, apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py
touched surfaces: apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/parent_tools.py, apps/api/app/runtime/effects/cases.py, apps/api/app/runtime/effects/worker.py, apps/api/app/runtime/projection/**init**.py, apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py, apps/api/tests/integration/phase3/routes/test_surface_contract.py
slice id: phase3-current-doc-and-closeout-refresh
slice type: edit
owned surfaces: docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/current/interfaces/api-surface-and-route-map.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
touched surfaces: docs/current/architecture/runtime-control-plane.md, docs/current/interfaces/api-trust-lanes.md, docs/current/interfaces/api-surface-and-route-map.md, docs/current/architecture/runtime-read-models-and-operator-surfaces.md, docs/current/architecture/manifest-projection-and-acknowledgement.md, docs/current/interfaces/prompt-layer-and-worker-delivery.md, docs/execution/plans/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/evidence/phase-3-closeout-runtime-lineage-and-budget.md, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md

## Slice identity

- selected phase: Phase 3
- reviewed plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- reviewed evidence: `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- date: 2026-05-13

## Phase-local contract

- current phase page:
  `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map:
  `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- reviewed evidence: `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
- reviewed current docs:
    - `../../current/architecture/runtime-control-plane.md`
    - `../../current/interfaces/api-trust-lanes.md`
    - `../../current/interfaces/api-surface-and-route-map.md`
    - `../../current/architecture/runtime-read-models-and-operator-surfaces.md`
    - `../../current/architecture/manifest-projection-and-acknowledgement.md`
    - `../../current/interfaces/prompt-layer-and-worker-delivery.md`
    - `../../current/operations/run-docker-postgres-verification.md`

## Verdict

- pass/fail: pass
- summary: the refreshed authoritative chain now matches the merged Phase 3
  runtime/current-doc work, the current docs no longer teach the stale
  checkpoint fallback, route-local structural manifest sync, or old launch
  timing, and the final docs_freeze, style_audit, private-symbol search,
  SQLite/reset, Postgres strong-lane, typing, and representative merged Phase
  3 pytest proof are all green.

## Findings

- the authoritative Phase 3 chain now describes the actual merged runtime work
  instead of the earlier stale draft:
    - current-surface validation now requires readable current evidence
    - bootstrap launch now refreshes the stable root reread path before return
    - checkpoint handoff stays controller-selected even without an open dispatch
    - structural manifest timing lives in the control-side commit/rollback path
- the refreshed current docs now remove the stale claims that were previously
  keeping Phase 3 current behavior misleading:
    - no route-local structural manifest sync story remains in the callback lane
      docs
    - no checkpoint-order fallback story remains in the stable-manifest or
      prompt-delivery docs
    - no old launch-after-return stable-manifest/attempt timing story remains in
      the runtime control-plane docs
- the plan now includes validator-compliant body briefs for all listed Phase 3
  delegated slices instead of relying only on the top-of-file header block
- the final proof rerun now confirms the refreshed chain and the updated
  current docs are closure-ready

## Delegated-slice compliance

- `phase3-current-surface-and-launch-readability`
    - slice type: `edit`
    - ownership result: stayed inside current-surface validation, launch, task-root,
      and Phase 3 proof-test surfaces
    - do-not-edit compliance: did not take callback-route or prompt-owner
      ownership
- `phase3-handoff-and-failure-family`
    - slice type: `edit`
    - ownership result: stayed inside checkpoint-handoff, failure-family, and
      supporting Phase 2/3 proof-test surfaces
    - do-not-edit compliance: did not widen into current docs or later-phase
      continuity ownership
- `phase3-structural-manifest-and-thin-route`
    - slice type: `edit`
    - ownership result: stayed inside callback-route, control-side structural
      sync, effect-worker, and structural-manifest proof surfaces
    - do-not-edit compliance: did not widen into prompt-owner docs or broader
      package/install work
- `phase3-current-doc-and-closeout-refresh`
    - slice type: `edit`
    - ownership result: stayed inside the owned current docs plus the selected
      Phase 3 triplet
    - do-not-edit compliance: did not reopen runtime code, scripts/docs, or
      prompt-layer owner docs

## Gate coverage

- the selected phase and current phase page remain correct for this chain
- the authoritative plan, evidence, and review each keep `summary-only: no`
- the refreshed plan now includes delegated-slice body briefs with
  do-not-edit, required reads, required tests/validators, expected outputs,
  dependencies, evidence to return, parent-owned decisions, and stop
  conditions for each listed slice
- the refreshed current docs stay inside the Phase 3 owned and allowed
  collateral surfaces
- the final gate result is now green:
    - `docs_freeze` passes
    - `style_audit` passes
    - the exact repo search for private symbol and underscore-private imports
      found no matches
    - SQLite init/upgrade/reset proof passes
    - `make test-api-db` passes
    - representative merged Phase 3 runtime, schema, and e2e proof passes

## Proof lanes relied on

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli validate` ->
  `Docs freeze validation passed.`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` ->
  `No findings.` The report also recorded zero cross-module private-helper
  imports, zero file-size threshold violations, and zero function-size
  threshold violations.
- exact repo search for cross-module underscore-private imports across the
  touched Phase 3 code paths ->
  no matches; `rg` exited with status `1`, which is the expected no-match
  result for this private-symbol and underscore-private import search
- `./.venv/bin/ruff check apps/api/app/api/runtime_exception_mapping.py apps/api/app/api/routes/callback.py apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract apps/api/tests/e2e/phase3/normal_lane` ->
  `All checks passed!`
- `./.venv/bin/mypy apps/api/app/api/runtime_exception_mapping.py apps/api/app/api/routes/callback.py apps/api/app/runtime/control apps/api/app/runtime/effects apps/api/app/runtime/launch apps/api/app/runtime/projection apps/api/app/runtime/task_root apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3 apps/api/tests/integration/runtime_schema_contract` ->
  `Success: no issues found in 125 source files`
- `make pyright-api` -> `0 errors, 0 warnings, 0 informations`
- shipped-path SQLite init/upgrade/reset proof subset ->
  `4 passed, 3 deselected in 8.52s`
- `make test-api-db` -> `262 passed in 666.45s (0:11:06)`
- representative merged Phase 3 pytest batch ->
  `105 passed in 729.09s (0:12:09)`

## Stale-logic search proof

- searched the refreshed current docs and authoritative Phase 3 chain for stale
  claims that:
    - structural manifest sync still lives in the callback route
    - stable-manifest handoff still falls back to surfaced checkpoint order when
      no dispatch is open
    - launch still returns before the stable root manifest and root attempt files
      are readable
- outcome:
    - those stale claims are removed from the refreshed current docs and the
      authoritative Phase 3 triplet

## Kill-list proof

- phase kill-list source:
    - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- terms checked in this refresh:
    - runtime truth split across both Phase 2 and Phase 3
    - review treated as an external gate
    - stale checkpoint-only closure language
    - structural replan or reread behavior inferred from filesystem order rather
      than controller truth
- outcome:
    - the refreshed chain keeps currentness, handoff, and reread timing under the
      Phase 3 controller-owned runtime surfaces and does not reintroduce the
      stale filesystem-order explanation

## Docs answer-sourcing proof

- execution canon read:
    - `AGENTS.md`
    - `STYLE.md`
    - `docs/execution/README.md`
    - `docs/execution/maps/file-priority-map.md`
    - `docs/execution/maps/redesign-code-landing-map.md`
    - `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
    - `docs/execution/gates/mandatory-review-gate.md`
    - `docs/execution/gates/reset-gate.md`
    - `docs/execution/gates/code-quality-gate.md`
- redesign/current truth read:
    - `docs/redesign/architecture/runtime-records-and-lifecycle.md`
    - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
    - `docs/redesign/architecture/checkpoint-contract.md`
    - `docs/redesign/architecture/runtime-database-and-object-contract.md`
    - `docs/redesign/architecture/worker-context-contract.md`
    - `docs/redesign/workflows/parent-review-and-replan.md`
    - `docs/redesign/workflows/parent-root-release-and-closure.md`
    - `docs/redesign/prompt-layer/source-and-sections.md`
    - `docs/redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md`
    - `docs/current/architecture/runtime-control-plane.md`
    - `docs/current/interfaces/api-trust-lanes.md`
    - `docs/current/interfaces/api-surface-and-route-map.md`
    - `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
    - `docs/current/architecture/manifest-projection-and-acknowledgement.md`
    - `docs/current/interfaces/prompt-layer-and-worker-delivery.md`
    - `docs/current/operations/run-docker-postgres-verification.md`
- code/tests inspected for current truth:
    - `apps/api/app/api/routes/callback.py`
    - `apps/api/app/api/runtime_exception_mapping.py`
    - `apps/api/app/runtime/control/dispatch/opening.py`
    - `apps/api/app/runtime/control/parent_tools.py`
    - `apps/api/app/runtime/effects/cases.py`
    - `apps/api/app/runtime/control/observability.py`
    - `apps/api/app/runtime/effects/worker.py`
    - `apps/api/app/runtime/effects/validation.py`
    - `apps/api/app/runtime/launch/service.py`
    - `apps/api/app/runtime/launch/persistence/runtime.py`
    - `apps/api/app/runtime/projection/manifest/checkpoint_handoff.py`
    - `apps/api/app/runtime/projection/manifest/context.py`
    - `apps/api/app/runtime/projection/manifest/current_context_queries.py`
    - `apps/api/app/runtime/task_root/reads.py`
    - `apps/api/tests/integration/phase2/bootstrap/test_manifest_checkpoint_handoff.py`
    - `apps/api/tests/integration/phase3/contracts/test_assignment_cases.py`
    - `apps/api/tests/integration/phase3/contracts/test_parent_checkpoint_handoff_cases.py`
    - `apps/api/tests/integration/phase3/contracts/test_structural_manifest_cases.py`
    - `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Phase-bounded STYLE exceptions

- none

## Remaining exact blockers

- none

## Cross-links

- authoritative plan: `../plans/phase-3-closeout-runtime-lineage-and-budget.md`
- authoritative evidence:
  `../evidence/phase-3-closeout-runtime-lineage-and-budget.md`
